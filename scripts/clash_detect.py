#!/usr/bin/env python3
"""clash_detect.py — OFFLINE governance clash-detection over captured user messages.

Phase 2 (SHADOW) of ADR 2026-06-16-governance-clash-detection. Reads the directive-class
messages captured by .claude/hooks/userprompt-clash-capture.py, checks each against the
compact governance-index (the single-source substrate, .claude/governance-index.md), and
writes verdicts to ~/.claude/clash-shadow.jsonl. SHADOW = log what it WOULD flag; surface
nothing. Promotion to the human-facing back-queue is gated on measured precision on REAL
messages (the probe showed 5/5 on synthetic — this measures the real rate).

No turn latency: the capture hook is in-band + cheap; THIS runs offline (just clash-detect
or a launchd cadence). Cursor-tracked over the append-only capture log → no rewrite race.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CAPTURE_LOG = Path.home() / ".claude" / "clash-capture.jsonl"
CURSOR = Path.home() / ".claude" / "clash-capture.cursor"
SHADOW_LOG = Path.home() / ".claude" / "clash-shadow.jsonl"
MAX_BATCH = 20

SYSTEM = (
    "You are a GOVERNANCE CLASH DETECTOR. Given a compact index of a project's goals, "
    "principles, and vetoed decisions, and user DIRECTIVES, decide whether each directive "
    "CLASHES with any indexed item (proposes something a principle forbids, re-proposes a "
    "vetoed thing, or contradicts a goal). Be CONSERVATIVE: only flag CLASH when the "
    "contradiction is clear and consequential — alignment or orthogonality is CLEAN, and "
    "false positives are costly. For each directive output exactly one line:\n"
    "  <n>. VERDICT=CLASH item=<ID> why=<≤12 words>   OR   <n>. VERDICT=CLEAN"
)

# item= may be a MULTI-WORD name (gemini cites the full veto/principle title), so capture
# non-greedily up to ` why=` rather than a single token.
_LINE = re.compile(
    r"^\s*(\d+)\.\s*VERDICT=(CLASH|CLEAN)(?:\s+item=(.+?))?(?:\s+why=(.*))?\s*$", re.I
)


def _effective_cursor(n_lines: int) -> int:
    """The line offset to resume from, self-healing against log rotation/truncation.

    The capture log is append-only WITHIN a rotation epoch, but log rotation (or a
    manual reset) can truncate/delete it. A raw line-offset cursor would then point PAST
    the (now shorter) log → `lines[cursor:]` is empty → every future capture is silently
    dropped forever. Detect that (cursor > current line count = log shrank) and reset to 0
    so the new epoch reprocesses from the start. Reprocessing is shadow-safe (idempotent
    append to clash-shadow.jsonl; precision is measured, not mutated)."""
    cur = int(CURSOR.read_text().strip()) if CURSOR.is_file() else 0
    return 0 if cur > n_lines else cur


def _read_new() -> list[dict]:
    if not CAPTURE_LOG.is_file():
        return []
    lines = CAPTURE_LOG.read_text(errors="ignore").splitlines()
    cursor = _effective_cursor(len(lines))
    new = []
    for ln in lines[cursor:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            new.append(json.loads(ln))
        except ValueError:
            continue
    return new


def _dispatch(index: str, messages: list[str]) -> str:
    numbered = "\n".join(f"{i+1}. {m}" for i, m in enumerate(messages))
    prompt = (
        f"## GOVERNANCE INDEX\n{index}\n\n## DIRECTIVES\n{numbered}\n\n"
        f"Output {len(messages)} lines, nothing else."
    )
    tmp = Path("/tmp/clash-detect-prompt.md")
    tmp.write_text(prompt)
    proc = subprocess.run(
        ["llmx", "chat", "--subscription", "-m", "gemini-3-flash-preview",
         "-s", SYSTEM, "-f", str(tmp), "Classify every directive now."],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:200] or "llmx failed")
    return proc.stdout


def _parse(out: str) -> dict[int, dict]:
    verdicts: dict[int, dict] = {}
    for line in out.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        idx = int(m.group(1))
        verdicts[idx] = {
            "verdict": m.group(2).upper(),
            "item": (m.group(3) or "").strip("[]") or None,
            "why": (m.group(4) or "").strip() or None,
        }
    return verdicts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--summary", action="store_true", help="print the shadow tally and exit")
    args = ap.parse_args()

    if args.summary:
        if not SHADOW_LOG.is_file():
            print("no shadow data yet")
            return 0
        rows = [json.loads(l) for l in SHADOW_LOG.read_text().splitlines() if l.strip()]
        clash = [r for r in rows if r.get("verdict") == "CLASH"]
        print(f"shadow: {len(rows)} judged · {len(clash)} CLASH "
              f"({100*len(clash)//max(len(rows),1)}%) · review precision in {SHADOW_LOG}")
        for r in clash[-8:]:
            print(f"  CLASH {r.get('item')}: {(r.get('message') or '')[:70]}")
        return 0

    index_path = args.repo / ".claude" / "governance-index.md"
    if not index_path.is_file():
        print(f"no governance-index at {index_path} — run `just governance-index`", file=sys.stderr)
        return 2

    new = _read_new()
    if not new:
        print("no new captured messages")
        return 0

    index = index_path.read_text()
    batch = new[:MAX_BATCH]
    try:
        out = _dispatch(index, [r["message"] for r in batch])
    except Exception as e:
        print(f"detector dispatch failed (cursor NOT advanced, will retry): {e}", file=sys.stderr)
        return 1
    verdicts = _parse(out)

    with SHADOW_LOG.open("a") as fh:
        for i, row in enumerate(batch):
            v = verdicts.get(i + 1, {"verdict": "PARSE_FAIL", "item": None, "why": None})
            fh.write(json.dumps({
                "ts": row.get("ts"), "session_id": row.get("session_id"),
                "message": row.get("message"), "model": "gemini-3-flash-preview",
                **v,
            }) + "\n")

    # advance cursor only by what we actually processed (the batch). Base off the SAME
    # effective cursor as the read (resets to 0 on rotation) so the two never desync.
    n_lines = len(CAPTURE_LOG.read_text(errors="ignore").splitlines()) if CAPTURE_LOG.is_file() else 0
    CURSOR.write_text(str(_effective_cursor(n_lines) + len(batch)))
    n_clash = sum(1 for v in verdicts.values() if v["verdict"] == "CLASH")
    print(f"judged {len(batch)} messages → {n_clash} CLASH (shadow → {SHADOW_LOG})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
