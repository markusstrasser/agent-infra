#!/usr/bin/env python3
"""Researcher postmortem — classify silent subagent failures.

Reads subagent-log.jsonl, finds unpaired researcher starts (no stop event),
checks for transcripts, and classifies: turn-exhausted, error-crashed,
context-overflow, or truly-silent.

Usage: uv run python3 scripts/researcher-postmortem.py [--days N]
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

from common.paths import CLAUDE_DIR, PROJECTS_DIR
LOGFILE = CLAUDE_DIR / "subagent-log.jsonl"


def parse_args():
    days = 7
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--days" and i < len(sys.argv) - 1:
            days = int(sys.argv[i + 1])
    return days


def load_events(days: int) -> list[dict]:
    if not LOGFILE.exists():
        print(f"No log file at {LOGFILE}")
        sys.exit(1)

    cutoff = datetime.now() - timedelta(days=days)
    events = []
    for line in LOGFILE.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = entry.get("ts", "")
        try:
            ts = datetime.fromisoformat(
                ts_str.replace("+0000", "+00:00").replace("Z", "+00:00")
            )
            ts = ts.replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue
        if ts >= cutoff:
            entry["_ts"] = ts
            events.append(entry)
    return events


def find_transcript(start_event: dict) -> Path | None:
    """Try to locate transcript for an unpaired subagent start."""
    agent_id = start_event.get("agent_id", "")
    session_id = start_event.get("session_id", "")
    cwd = start_event.get("cwd", "")

    if not agent_id or not session_id:
        return None

    if not cwd:
        return None

    # Construct project path: /Users/alien/Projects/agent-infra -> -Users-alien-Projects-agent-infra
    project_path = cwd.replace("/", "-").lstrip("-")
    project_dir = PROJECTS_DIR / f"-{project_path}"

    # Try candidate paths (most specific first)
    candidates = [
        project_dir / session_id / "subagents" / f"agent-{agent_id}.jsonl",
        project_dir / session_id / f"agent-{agent_id}.jsonl",
        project_dir / f"{session_id}.jsonl",
    ]

    for path in candidates:
        if path.exists() and path.stat().st_size > 0:
            return path

    return None


def classify_transcript(path: Path, agent_id: str) -> tuple[str, dict]:
    """Classify the failure mode from a transcript file."""
    try:
        size = path.stat().st_size
        text = path.read_text()
        lines = text.splitlines()
    except Exception:
        return "read-error", {"error": "Could not read transcript"}

    messages = []
    for line in lines:
        try:
            msg = json.loads(line)
            messages.append(msg)
        except json.JSONDecodeError:
            continue

    if not messages:
        return "empty-transcript", {"size": size}

    # Count tool_use entries
    tool_uses = 0
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                tool_uses += sum(
                    1
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "tool_use"
                )

    # Check last message
    last_msg = messages[-1]
    last_role = last_msg.get("role", "")
    last_content = last_msg.get("content", "")
    if isinstance(last_content, list):
        last_content = json.dumps(last_content)

    has_error = False
    if isinstance(last_content, str):
        has_error = any(
            kw in last_content.lower()
            for kw in ["error", "exception", "traceback", "failed", "timeout"]
        )

    info = {
        "size": size,
        "messages": len(messages),
        "tool_uses": tool_uses,
        "last_role": last_role,
    }

    # Classification
    if size > 500_000:
        return "context-overflow", info
    elif has_error and last_role != "assistant":
        return "error-crashed", info
    elif tool_uses > 10:
        return "turn-exhausted", info
    elif tool_uses > 0:
        return "partial-activity", info
    else:
        return "unclear", info


def main():
    days = parse_args()
    events = load_events(days)

    starts = [
        e
        for e in events
        if e.get("event") == "subagent_start" and e.get("agent_type") == "researcher"
    ]
    stops = [
        e
        for e in events
        if e.get("event") == "subagent_stop" and e.get("agent_type") == "researcher"
    ]

    start_ids = {e.get("agent_id"): e for e in starts if e.get("agent_id")}
    stop_ids = {e.get("agent_id") for e in stops if e.get("agent_id")}

    unpaired = {aid: ev for aid, ev in start_ids.items() if aid not in stop_ids}

    print(f"# Researcher Postmortem — last {days} days\n")
    print(f"- Total researcher starts: {len(starts)}")
    print(f"- Completed (paired): {len(start_ids) - len(unpaired)}")
    print(f"- Unpaired (silent failures): {len(unpaired)}")
    if start_ids:
        rate = len(unpaired) / len(start_ids) * 100
        print(f"- Silent failure rate: {rate:.1f}%")
    print()

    if not unpaired:
        print("No unpaired researcher starts found.")
        return

    # Classify each unpaired start
    classifications = Counter()
    details = []

    for agent_id, start_event in unpaired.items():
        transcript = find_transcript(start_event)
        if transcript is None:
            category = "truly-silent"
            info = {"transcript": "not found"}
        else:
            category, info = classify_transcript(transcript, agent_id)
            info["transcript"] = str(transcript)

        classifications[category] += 1
        details.append(
            {
                "agent_id": agent_id[:12],
                "ts": start_event.get("ts", ""),
                "project": start_event.get("project", ""),
                "category": category,
                **info,
            }
        )

    print("## Classification Breakdown\n")
    print("| Category | Count | Share |")
    print("|----------|-------|-------|")
    for cat, count in classifications.most_common():
        pct = count / len(unpaired) * 100
        print(f"| {cat} | {count} | {pct:.1f}% |")
    print()

    print("## Category Definitions\n")
    print("- **turn-exhausted**: Many tool calls (>10), no final synthesis returned")
    print("- **error-crashed**: Last message indicates error/exception/timeout")
    print("- **context-overflow**: Transcript >500KB, likely hit context limit")
    print("- **truly-silent**: No transcript file found at expected path")
    print("- **partial-activity**: Some tool calls (1-10) but incomplete")
    print("- **empty-transcript**: File exists but no parseable messages")
    print("- **unclear**: Activity doesn't fit other categories")
    print()

    print("## Details\n")
    print("| Agent ID | Time | Project | Category | Tool Uses | Size |")
    print("|----------|------|---------|----------|-----------|------|")
    for d in sorted(details, key=lambda x: x.get("ts", "")):
        ts = d.get("ts", "")[:16]
        tool_uses = d.get("tool_uses", "—")
        size = d.get("size", 0)
        size_str = f"{size / 1024:.0f}KB" if size else "—"
        print(
            f"| {d['agent_id']} | {ts} | {d['project']} | {d['category']} | {tool_uses} | {size_str} |"
        )
    print()

    cost_per_run = 2.0
    waste = len(unpaired) * cost_per_run
    print("## Cost Estimate\n")
    print(f"- Unpaired researcher runs: {len(unpaired)}")
    print(f"- Estimated cost per run: ${cost_per_run:.2f}")
    print(f"- Estimated waste: ${waste:.2f}")
    if days > 0:
        print(f"- Monthly projection: ${waste / days * 30:.0f}")


if __name__ == "__main__":
    main()
