"""JSONL file helpers."""

import json
from pathlib import Path


def load_jsonl(path: Path, *, since: str | None = None) -> list[dict]:
    """Load JSONL file. Returns [] if file missing."""
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since and row.get("ts", "") < since:
                continue
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write list of dicts to JSONL file."""
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
