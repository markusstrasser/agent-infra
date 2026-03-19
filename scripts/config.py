"""Shared config for epistemic measurement scripts."""

import json
from datetime import datetime
from pathlib import Path

from common.paths import CLAUDE_DIR

METRICS_FILE = CLAUDE_DIR / "epistemic-metrics.jsonl"

PROJECT_ROOTS = {
    "intel": Path.home() / "Projects" / "intel",
    "genomics": Path.home() / "Projects" / "genomics",
    "selve": Path.home() / "Projects" / "selve",
    "meta": Path.home() / "Projects" / "meta",
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


