#!/usr/bin/env python3
"""loop_funnel.py — per-stage queue depths for the RSI learning loop.

Honest denominator: separates capture → classify → quarantine → human disposition.
Zero-LLM, read-only. Consumed by act_drain.py and `just loop-funnel`.

Usage:
  uv run python3 scripts/loop_funnel.py
  uv run python3 scripts/loop_funnel.py --json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from session_automation_telemetry import summarize, fetch_sessions, DB as AGENTLOGS_DB

REPO = Path(__file__).resolve().parent.parent
CAPTURE_LOG = Path.home() / ".claude" / "reflect-capture.jsonl"
PROCESSED = Path.home() / ".claude" / "reflect-processed.json"
QUARANTINE_DIR = Path.home() / ".claude" / "reflect-quarantine"
STEWARD_DIR = Path.home() / ".claude" / "steward-proposals"
DIGEST_LOG = Path.home() / ".claude" / "reflect-close-digest.jsonl"
CLOSE_QUEUE = Path.home() / ".claude" / "close-queue"
FM_EVIDENCE = Path.home() / ".claude" / "fm-evidence.jsonl"


def _count_jsonl(path: Path, pred=None) -> int:
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if pred is None or pred(row):
            n += 1
    return n


def _closed_sessions() -> set[str]:
    closed: set[str] = set()
    if not DIGEST_LOG.exists():
        return closed
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if row.get("rsi_closed") and row.get("session_id"):
            closed.add(str(row["session_id"]))
    return closed


def rsi_pending() -> list[dict]:
    closed = _closed_sessions()
    pending: list[dict] = []
    if not DIGEST_LOG.exists():
        return pending
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        sid = row.get("session_id")
        if row.get("invoke_skill") and sid and sid not in closed:
            pending.append(row)
    return pending


def quarantine_pending() -> list[dict]:
    out: list[dict] = []
    if not QUARANTINE_DIR.exists():
        return out
    for f in sorted(QUARANTINE_DIR.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if row.get("status") == "pending":
                out.append(row)
    return out


def steward_count() -> int:
    if not STEWARD_DIR.exists():
        return 0
    return len(list(STEWARD_DIR.glob("*.md")))


def close_queue_open() -> int:
    if not CLOSE_QUEUE.exists():
        return 0
    n = 0
    for p in CLOSE_QUEUE.glob("*.json"):
        try:
            row = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        if not row.get("processed"):
            n += 1
    return n


def metrics() -> dict:
    captured = _count_jsonl(CAPTURE_LOG)
    processed = 0
    if PROCESSED.exists():
        try:
            processed = len(json.loads(PROCESSED.read_text(encoding="utf-8")).get("hashes", []))
        except (json.JSONDecodeError, ValueError, OSError):
            processed = 0
    quarantine = quarantine_pending()
    rsi = rsi_pending()
    steward = steward_count()
    fm_evidence = _count_jsonl(FM_EVIDENCE) if FM_EVIDENCE.exists() else 0
    unclassified = max(0, captured - processed)
    disposition = len(quarantine) + steward + len(rsi)
    session_rows = fetch_sessions(AGENTLOGS_DB, 7, None) if AGENTLOGS_DB.is_file() else []
    session_split = summarize(session_rows) if session_rows else {}
    return {
        "captured": captured,
        "classified": processed,
        "unclassified": unclassified,
        "quarantine_pending": len(quarantine),
        "steward_proposals": steward,
        "rsi_close_pending": len(rsi),
        "close_queue_open": close_queue_open(),
        "fm_evidence_rows": fm_evidence,
        "disposition_queue": disposition,
        "rsi_pending": rsi,
        "quarantine": quarantine,
        "session_split_7d": session_split,
    }


def render(m: dict) -> str:
    lines = [
        "## Loop funnel",
        f"- captured: **{m['captured']}** → classified: **{m['classified']}** "
        f"(unclassified: **{m['unclassified']}**)",
        f"- quarantine pending: **{m['quarantine_pending']}** · "
        f"steward proposals: **{m['steward_proposals']}** · "
        f"RSI close pending: **{m['rsi_close_pending']}**",
        f"- disposition queue (human): **{m['disposition_queue']}** · "
        f"FM evidence rows: **{m['fm_evidence_rows']}**",
    ]
    ss = m.get("session_split_7d") or {}
    if ss.get("total"):
        lines.append(
            f"- sessions (7d): **{ss['total']}** · automation **{ss.get('automation_pct', 0)}%** · "
            f"operator **{ss.get('operator', 0)}**"
        )
    if m["rsi_pending"]:
        lines.append("\n### RSI close (run `/rsi close`)")
        for row in m["rsi_pending"][:3]:
            sid = str(row.get("session_id", ""))[:8]
            lines.append(f"- `{row.get('project','?')}/{sid}` — {row.get('tier1_reason','?')}")
    if m["quarantine"]:
        lines.append("\n### Reflect quarantine (approve/reject in jsonl)")
        for row in sorted(m["quarantine"], key=lambda r: r.get("confidence", 0), reverse=True)[:5]:
            head = row.get("action", "enforcer")
            if head not in ("mint", "needs-review"):
                head = f"enforcer→{row.get('fm_id','?')}"
            lines.append(f"- [{head}] {row.get('cluster_summary','?')} (conf={row.get('confidence')})")
    if m["steward_proposals"]:
        lines.append(f"\n### Steward proposals ({m['steward_proposals']} files)")
        lines.append("- Review `~/.claude/steward-proposals/` — cross-repo items need human gate.")
    return "\n".join(lines) + "\n"


def needs_attention(m: dict) -> bool:
    return (
        m["unclassified"] > 0
        or m["quarantine_pending"] > 0
        or m["rsi_close_pending"] > 0
        or m["steward_proposals"] > 0
        or m["close_queue_open"] > 0
    )


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="RSI loop funnel metrics")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    m = metrics()
    if args.json:
        # strip heavy nested lists for json export
        slim = {k: v for k, v in m.items() if k not in ("rsi_pending", "quarantine")}
        slim["rsi_pending_count"] = len(m["rsi_pending"])
        slim["quarantine_summaries"] = [r.get("cluster_summary") for r in m["quarantine"][:10]]
        print(json.dumps(slim, indent=2))
        return 0
    print(render(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
