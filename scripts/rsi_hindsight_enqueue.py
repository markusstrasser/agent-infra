#!/usr/bin/env python3
"""rsi_hindsight_enqueue.py — CLOSE the RSI rediscovery loop.

Blindspot/supervision already SENSE "why didn't you find X" flags. This script
turns those flags into a durable file-bus artifact that maintain_tick / harvest
can drain — without expanding REDISCOVERY regexes (ablation-control hygiene).

Reads `.claude/blindspot-digest.md` (or --digest PATH), extracts rediscovery /
GROW_COVERAGE flags that look like RSI-hindsight steers, appends deduped rows to
`artifacts/rsi-hindsight/queue.jsonl`, and refreshes `LATEST.md` for /rsi close.

Does NOT edit hooks, does NOT expand prior-context patterns, does NOT auto-build
detectors — only enqueues evidence for the motor/human to convert.

Usage:
  uv run python3 scripts/rsi_hindsight_enqueue.py
  uv run python3 scripts/rsi_hindsight_enqueue.py --digest path --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DIGEST = REPO / ".claude" / "blindspot-digest.md"
OUT_DIR = REPO / "artifacts" / "rsi-hindsight"
QUEUE = OUT_DIR / "queue.jsonl"
LATEST = OUT_DIR / "LATEST.md"

# Flag lines look like:
# - `+1.00` [rediscovery/regex] **arc-agi/d8da85ee** (2026-07-07): RSI : why did you not find...
_FLAG = re.compile(
    r"^- `\+([0-9.]+)` \[(\w+)/(\w+)\] \*\*([^/]+)/([^*]+)\*\* \(([^)]+)\):\s*(.*)$"
)
# RSI-hindsight phrasing (already sensed by blindspot; we only CLOSE)
_RSI = re.compile(
    r"(?i)\b("
    r"RSI\s*:|"
    r"why did you not (find|figure)|"
    r"why didn't you (find|figure|check)|"
    r"ask yourself|"
    r"every ?time I mention|"
    r"why is our system not figur|"
    r"metaimprove|metaiprove|meta[- ]improve"
    r")\b"
)


def _load_queue(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _flag_id(project: str, session: str, text: str) -> str:
    h = hashlib.sha1(f"{project}|{session}|{text.strip()[:200]}".encode()).hexdigest()[:12]
    return f"rsi-{project}-{session[:8]}-{h}"


def parse_digest(text: str) -> list[dict]:
    out: list[dict] = []
    for line in text.splitlines():
        m = _FLAG.match(line.strip())
        if not m:
            continue
        conf, direction, method, project, session, date, preview = m.groups()
        if direction not in ("rediscovery",) and "grow_coverage" not in direction.lower():
            # blindspot uses rediscovery= under GROW_COVERAGE; type_id is rediscovery
            if direction != "rediscovery":
                continue
        if not _RSI.search(preview):
            continue
        out.append(
            {
                "id": _flag_id(project, session, preview),
                "confidence": float(conf),
                "direction": "grow_coverage",
                "type_id": direction,
                "method": method,
                "project": project,
                "session_prefix": session.strip(),
                "date": date.strip(),
                "text_preview": preview.strip()[:400],
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
                "status": "queued",
                "proposed_convert": (
                    "Convert this RSI-hindsight flag into a durable detector or "
                    "maintain_tick BUILD draft — do not chat-apologize. Cite this "
                    "queue row from /rsi close."
                ),
            }
        )
    return out


def enqueue(digest_path: Path, *, dry_run: bool = False) -> dict:
    if not digest_path.is_file():
        return {"ok": False, "error": f"missing digest: {digest_path}", "new": 0, "total": 0}
    flags = parse_digest(digest_path.read_text())
    existing = _load_queue(QUEUE)
    seen = {r["id"] for r in existing if "id" in r}
    new_rows = []
    for r in flags:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        new_rows.append(r)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "parsed": len(flags),
            "new": len(new_rows),
            "total": len(existing),
            "sample": [r["id"] for r in new_rows[:5]],
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if new_rows:
        with QUEUE.open("a") as f:
            for r in new_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    all_rows = existing + new_rows
    queued = [r for r in all_rows if r.get("status") == "queued"]
    by_proj: dict[str, int] = {}
    for r in queued:
        by_proj[r.get("project", "?")] = by_proj.get(r.get("project", "?"), 0) + 1
    latest = f"""# RSI hindsight queue — {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

**Source:** `{digest_path.relative_to(REPO) if digest_path.is_relative_to(REPO) else digest_path}`
**Queued (unacked):** {len(queued)} · **New this run:** {len(new_rows)} · **All-time rows:** {len(all_rows)}

By project: {", ".join(f"{k}={v}" for k, v in sorted(by_proj.items(), key=lambda kv: -kv[1])) or "(none)"}

## CLOSE contract
Each row is a labeled loop-miss. `/rsi close` and `/improve maintain` must cite a
file artifact (this queue or a maintain draft), not a chat apology.
Do **not** expand REDISCOVERY regexes while over_caution ablation is measuring
(see `decisions-pending/2026-07-10-ablate-over-caution-enforce.md`).

## Top queued
"""
    for r in queued[-15:][::-1]:
        latest += (
            f"- `{r['id']}` **{r['project']}/{r['session_prefix']}** ({r['date']}): "
            f"{r['text_preview'][:160]}\n"
        )
    if not queued:
        latest += "_empty — no RSI-phrasing rediscovery flags in digest_\n"
    LATEST.write_text(latest)
    return {
        "ok": True,
        "parsed": len(flags),
        "new": len(new_rows),
        "queued": len(queued),
        "total": len(all_rows),
        "latest": str(LATEST.relative_to(REPO)),
        "queue": str(QUEUE.relative_to(REPO)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digest", type=Path, default=DEFAULT_DIGEST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = enqueue(args.digest, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if not res.get("ok"):
            print(f"FAIL: {res.get('error')}")
            return 1
        print(
            f"rsi-hindsight: parsed={res['parsed']} new={res['new']} "
            f"queued={res.get('queued', res.get('total'))} "
            f"→ {res.get('latest', '(dry-run)')}"
        )
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
