#!/usr/bin/env python3
"""PreCompact hook: goal-run ordering guard + compaction quality instructions.

Only active when `.claude/goal-run` exists (overnight /goal opt-in marker).

Ordering guard: an AUTO compaction attempt before the wrap-up ritual has been
prompted (no `.claude/goal-wrapup-fired`) is blocked — the binary continues
uncompacted and re-triggers next turn (willRetriggerNextTurn), by which time
the Stop hook has injected the ritual. Blocks are capped (5) so a pathological
session can't ride uncompacted into the hard context limit; set the goal-run
window (settings autoCompactWindow, floor 80K) well under the model window so
blocked attempts have real headroom.

Quality injection: on allowed compactions, stdout becomes the summarizer's
customInstructions (binary-verified: PreCompact hook output -> newCustomInstructions).
"""
import json
import sys
from pathlib import Path

MAX_BLOCKS = 5

CUSTOM_INSTRUCTIONS = (
    "Preserve verbatim in the summary: the original goal statement (/goal text), "
    "the path .claude/checkpoint.md and instruction to re-read it, the current "
    "state of each work front (done / in-flight / blocked), any pending "
    "verification commands, and any hard constraints the operator stated."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    claude_dir = cwd / ".claude"
    if not (claude_dir / "goal-run").is_file():
        return 0
    trigger = payload.get("trigger") or payload.get("compaction_trigger") or ""
    fired = claude_dir / "goal-wrapup-fired"
    blocks = claude_dir / "goal-compact-blocks"
    if trigger == "auto" and not fired.exists():
        n = 0
        try:
            n = int(blocks.read_text().strip() or "0")
        except Exception:
            pass
        if n < MAX_BLOCKS:
            try:
                blocks.write_text(str(n + 1))
            except Exception:
                pass
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": "goal-run wrap-up ritual not yet done; compact retries next turn",
                    }
                )
            )
            return 0
    # allowed: reset block counter, inject summarizer instructions
    try:
        blocks.unlink(missing_ok=True)
    except Exception:
        pass
    print(CUSTOM_INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
