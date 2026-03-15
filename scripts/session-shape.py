#!/usr/bin/env python3
"""Session shape detector — zero-LLM-cost structural anomaly detection.

Analyzes session topology (tool patterns, message ratios, structural signals)
to flag anomalous sessions worth deep analysis. Pre-filter for session-analyst:
most sessions are fine — don't waste Gemini on them.

Usage:
    session-shape.py [--days N] [--project P] [--threshold T] [--json]
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev

from config import log_metric

DB_PATH = Path.home() / ".claude" / "sessions.db"

# Structural features extracted per session
FEATURE_NAMES = [
    "tool_diversity",       # unique tools / total tool calls
    "read_write_ratio",     # reads / (writes + edits + 1)
    "bash_fraction",        # bash calls / total tool calls
    "agent_fraction",       # agent calls / total tool calls
    "search_density",       # (grep + glob + web) / total
    "transcript_density",   # transcript lines / duration minutes
    "tool_intensity",       # total tool calls / duration minutes
    "mcp_fraction",         # mcp tool calls / total
    "commit_ratio",         # commits / edits
    "read_only_flag",       # 1 if zero writes/edits, else 0
]


@dataclass
class SessionShape:
    uuid: str
    project: str
    start_ts: str
    first_message: str
    duration_min: float
    cost_usd: float
    features: dict = field(default_factory=dict)
    anomaly_score: float = 0.0
    anomaly_reasons: list = field(default_factory=list)


def extract_features(row: sqlite3.Row) -> dict:
    """Extract structural features from a session row."""
    tools_raw = row["tools_used"]
    tools = json.loads(tools_raw) if tools_raw else []
    total_tools = len(tools)

    # Count tool categories
    reads = sum(1 for t in tools if t in ("Read", "Glob", "Grep"))
    writes = sum(1 for t in tools if t in ("Write", "Edit", "NotebookEdit"))
    bashes = sum(1 for t in tools if t == "Bash")
    agents = sum(1 for t in tools if t == "Agent")
    searches = sum(1 for t in tools if t in ("Grep", "Glob", "WebSearch", "WebFetch"))
    mcps = sum(1 for t in tools if t.startswith("mcp__"))

    unique_tools = len(set(tools))
    duration = max(row["duration_min"] or 1.0, 0.1)
    transcript_lines = row["transcript_lines"] or 0

    commits_raw = row["commits"]
    commits = json.loads(commits_raw) if commits_raw else []

    return {
        "tool_diversity": unique_tools / max(total_tools, 1),
        "read_write_ratio": reads / max(writes + 1, 1),
        "bash_fraction": bashes / max(total_tools, 1),
        "agent_fraction": agents / max(total_tools, 1),
        "search_density": searches / max(total_tools, 1),
        "transcript_density": transcript_lines / duration,
        "tool_intensity": total_tools / duration,
        "mcp_fraction": mcps / max(total_tools, 1),
        "commit_ratio": len(commits) / max(writes + 1, 1),
        "read_only_flag": 1.0 if writes == 0 and total_tools > 5 else 0.0,
    }


def compute_anomalies(
    shapes: list[SessionShape], threshold: float = 2.0
) -> list[SessionShape]:
    """Flag sessions where features are > threshold stddevs from mean."""
    if len(shapes) < 5:
        return shapes  # Not enough data for statistics

    # Compute mean/stdev per feature
    stats = {}
    for feat in FEATURE_NAMES:
        values = [s.features.get(feat, 0.0) for s in shapes]
        m = mean(values)
        s = stdev(values) if len(values) > 1 else 1.0
        stats[feat] = (m, max(s, 0.001))

    for shape in shapes:
        score = 0.0
        reasons = []
        for feat in FEATURE_NAMES:
            val = shape.features.get(feat, 0.0)
            m, s = stats[feat]
            z = abs(val - m) / s
            if z > threshold:
                score += z
                direction = "high" if val > m else "low"
                reasons.append(f"{feat}={val:.2f} ({direction}, z={z:.1f})")
        shape.anomaly_score = score
        shape.anomaly_reasons = reasons

    return shapes


def main():
    parser = argparse.ArgumentParser(description="Session shape anomaly detector")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--project", "-p", help="Filter by project")
    parser.add_argument(
        "--threshold", "-t", type=float, default=2.0, help="Z-score threshold (default: 2.0)"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--all", action="store_true", help="Show all sessions, not just anomalies")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Session DB not found. Run: uv run python3 scripts/sessions.py index", file=sys.stderr)
        sys.exit(1)

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    query = """
        SELECT uuid, project, start_ts, first_message, duration_min, cost_usd,
               tools_used, commits, transcript_lines
        FROM sessions
        WHERE start_ts >= ? AND duration_min IS NOT NULL AND duration_min > 0.5
    """
    params = [since]
    if args.project:
        query += " AND project = ?"
        params.append(args.project)
    query += " ORDER BY start_ts DESC"

    rows = db.execute(query, params).fetchall()
    if not rows:
        print("No sessions found in the given period.", file=sys.stderr)
        sys.exit(0)

    # Extract features
    shapes = []
    for row in rows:
        shape = SessionShape(
            uuid=row["uuid"],
            project=row["project"] or "unknown",
            start_ts=row["start_ts"] or "",
            first_message=(row["first_message"] or "")[:80],
            duration_min=row["duration_min"] or 0,
            cost_usd=row["cost_usd"] or 0,
            features=extract_features(row),
        )
        shapes.append(shape)

    # Compute anomalies
    shapes = compute_anomalies(shapes, threshold=args.threshold)

    # Filter to anomalies unless --all
    if not args.all:
        shapes = [s for s in shapes if s.anomaly_score > 0]

    # Sort by anomaly score descending
    shapes.sort(key=lambda s: s.anomaly_score, reverse=True)

    if args.json:
        output = []
        for s in shapes:
            output.append({
                "uuid": s.uuid[:8],
                "project": s.project,
                "date": s.start_ts[:10],
                "anomaly_score": round(s.anomaly_score, 2),
                "reasons": s.anomaly_reasons,
                "first_message": s.first_message,
                "features": {k: round(v, 3) for k, v in s.features.items()},
            })
        print(json.dumps(output, indent=2))
    else:
        total = len(rows)
        anomalous = len([s for s in shapes if s.anomaly_score > 0]) if args.all else len(shapes)
        print(f"Sessions: {total} total, {anomalous} anomalous (threshold z>{args.threshold})")
        print()

        if not shapes:
            print("No anomalous sessions found.")
            return

        for s in shapes[:20]:
            score_bar = "█" * min(int(s.anomaly_score), 20)
            print(f"{s.uuid[:8]}  {s.start_ts[:10]}  {s.project:<12}  "
                  f"${s.cost_usd:>5.2f}  {s.duration_min:>5.1f}m  "
                  f"score={s.anomaly_score:>5.1f}  {score_bar}")
            for reason in s.anomaly_reasons[:3]:
                print(f"  ↳ {reason}")
            print(f"  {s.first_message}")
            print()

    # Log metric
    log_metric("session_shape",
               sessions_scanned=len(rows),
               anomalies_found=anomalous if not args.all else len([s for s in shapes if s.anomaly_score > 0]),
               threshold=args.threshold,
               days=args.days)

    db.close()


if __name__ == "__main__":
    main()
