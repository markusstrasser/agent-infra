"""Shared config for epistemic measurement scripts."""

import json
from datetime import datetime
from pathlib import Path

METRICS_FILE = Path.home() / ".claude" / "epistemic-metrics.jsonl"

PROJECT_ROOTS = {
    "intel": Path.home() / "Projects" / "intel",
    "genomics": Path.home() / "Projects" / "genomics",
    "selve": Path.home() / "Projects" / "selve",
    "meta": Path.home() / "Projects" / "meta",
    "anki": Path.home() / "Projects" / "anki",
}

RESEARCH_DIRS = ["docs", "analysis", "research", "entities", "briefs"]

PROSE_EXTENSIONS = {".md", ".txt", ".rst"}


def log_metric(metric_name: str, **fields) -> None:
    """Append a metric entry to epistemic-metrics.jsonl."""
    entry = {"ts": datetime.now().isoformat(), "metric": metric_name, **fields}
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_hook_event(
    hook_name: str,
    *,
    triggered: bool = True,
    bypassed: bool = False,
    execution_time_ms: int | None = None,
) -> None:
    """Log a hook trigger/bypass event for observability (Phase 1.5).

    All new hooks should call this. Enables hook ROI measurement
    (constitution: "measure before enforcing").
    """
    entry = {
        "ts": datetime.now().isoformat(),
        "metric": "hook_event",
        "hook_name": hook_name,
        "triggered": triggered,
        "bypassed": bypassed,
    }
    if execution_time_ms is not None:
        entry["execution_time_ms"] = execution_time_ms
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
