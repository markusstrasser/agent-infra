"""Shared config for epistemic measurement scripts."""

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from common.paths import CLAUDE_DIR

METRICS_FILE = CLAUDE_DIR / "epistemic-metrics.jsonl"

PROJECT_ROOTS = {
    "intel": Path.home() / "Projects" / "intel",
    "genomics": Path.home() / "Projects" / "genomics",
    "phenome": Path.home() / "Projects" / "phenome",
    "agent-infra": Path.home() / "Projects" / "agent-infra",
    "anki": Path.home() / "Projects" / "anki",
}

RESEARCH_DIRS = ["docs", "analysis", "research", "entities", "briefs"]

PROSE_EXTENSIONS = {".md", ".txt", ".rst"}


def extract_project_name(dir_name: str) -> str:
    """Convert dir name like '-Users-alien-Projects-intel' to 'intel'."""
    parts = dir_name.split("-")
    for i, p in enumerate(parts):
        if p == "Projects" and i + 1 < len(parts):
            return "-".join(parts[i + 1:])
    return dir_name


def log_metric(metric_name: str, **fields) -> None:
    """Append a metric entry to epistemic-metrics.jsonl."""
    entry = {"ts": datetime.now().isoformat(), "metric": metric_name, **fields}
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def jsonl_log(name: str, entry: dict) -> None:
    """Append a JSONL entry to ~/.claude/{name}.jsonl.

    Adds 'ts' if not present. Used by measurement scripts to avoid
    duplicating the open/write/newline pattern.
    """
    if "ts" not in entry:
        entry = {"ts": datetime.now().isoformat(), **entry}
    path = CLAUDE_DIR / f"{name}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def extract_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns parsed dict or None if no frontmatter found.
    Shared by ingestion scripts, hooks, and balance checks.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = _FM_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None


# Knowledge-eligible path patterns (per project)
KNOWLEDGE_ELIGIBLE_PATTERNS = {
    "intel": ["analysis/entities/*.md"],
    "phenome": ["docs/research/*.md", "docs/entities/*.md"],
    "genomics": ["docs/research/*.md"],  # was empty (A6) but hook already indexes 22 files here
    "agent-infra": ["research/*.md", "decisions/*.md"],
}


def is_knowledge_eligible(file_path: Path) -> bool:
    """Check if a file path matches knowledge-eligible patterns."""
    path_str = str(file_path)
    for patterns in KNOWLEDGE_ELIGIBLE_PATTERNS.values():
        for pattern in patterns:
            # Convert glob pattern to a path check
            parts = pattern.split("/")
            # Check if path contains the directory structure
            if all(p == "*" or p.rstrip("*.md") in path_str for p in parts if p != "*.md"):
                # More precise: check actual path segments
                if any(d in path_str for d in [p for p in parts if p != "*.md" and p != "*"]):
                    if path_str.endswith(".md"):
                        return True
    return False

