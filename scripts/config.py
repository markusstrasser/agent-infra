"""Shared config for epistemic measurement scripts."""

from pathlib import Path

METRICS_FILE = Path.home() / ".claude" / "epistemic-metrics.jsonl"

PROJECT_ROOTS = {
    "intel": Path.home() / "Projects" / "intel",
    "genomics": Path.home() / "Projects" / "genomics",
    "selve": Path.home() / "Projects" / "selve",
    "meta": Path.home() / "Projects" / "meta",
}

RESEARCH_DIRS = ["docs", "analysis", "research", "entities", "briefs"]

PROSE_EXTENSIONS = {".md", ".txt", ".rst"}
