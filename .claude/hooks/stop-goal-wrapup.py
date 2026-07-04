#!/usr/bin/env python3
"""Stop hook: overnight /goal run controller (wrap-up ritual + goal continuation).

Opt-in per run via `just goal-night` (or manually: `.claude/goal-run` file whose
content = ritual threshold in tokens; launch with CLAUDE_CODE_AUTO_COMPACT_WINDOW
~10% above it). Stop = the "agent finished a meaningful unit of work" event, so
one hook drives the whole night:

  Stop fires
    ├─ context >= ritual threshold and ritual not yet prompted
    │    → block ONCE with the wrap-up ritual (do it with full context;
    │      native auto-compact fires next turn; precompact-goal-guard.py
    │      enforces ordering + injects summarizer instructions)
    ├─ goal not done, not human-blocked, continuation budget left
    │    → block with the continuation prompt (goal keeps going after compaction)
    └─ .claude/goal-done / .claude/goal-blocked / budget exhausted → allow stop

Escapes the agent controls: touch .claude/goal-done (goal complete + verified),
touch .claude/goal-blocked (write HUMAN.md first). Operator disarm: rm .claude/goal-run.
Continuation budget (MAX_CONTINUES) bounds a pathological spin; PostCompact re-arms
the ritual for the next fill cycle. Fail-open everywhere (P10).

Context measurement: last assistant usage in the transcript =
input_tokens + cache_read + cache_creation.
"""
import json
import sys
from pathlib import Path

MAX_CONTINUES = 100

WRAPUP_PROMPT = """CONTEXT THRESHOLD REACHED ({ctx:,} >= {thr:,} tokens) — run the wrap-up ritual NOW, while full context exists. Order matters:

1. COMMIT everything finished (granular, semantic). Post-compaction verification trusts git, not memory — uncommitted work risks being hallucinated-as-done after the summary.
2. Session sweep: anything to improve, eradicate, or rethink with smart tooling, hooks, skills, MCPs, or goal rethinking? Wasted effort? Bad infrastructure? What could a future agent leverage? Only long-term, deep, STRICTLY better changes — no noise, no iatrogenic harm, no backward-compat cruft. "Nothing strictly better" is a fine answer.
3. Run /rsi.
4. Spend remaining full-context leverage: loose ends only this context can tie off; update docs/indexes for files this session touched; record path-dependent decisions in decisions/.
5. Rewrite .claude/checkpoint.md as the post-compact re-entry brief:
   GOAL — the /goal verbatim.
   FRONTS — per-front status (done / in-flight / blocked) with evidence (commit SHAs, paths).
   NEXT — the 2-3 highest-value next actions, with exact commands.
   VERIFY — commands the post-compact agent must run before trusting state (git log --oneline -10, test/gate commands). Never carry bare numbers across the boundary — carry the command that produces them.
   ASKS — anything for the human (also append to HUMAN.md).
6. End your turn normally. Native auto-compact fires on a subsequent turn (the PreCompact guard passes once this ritual has been prompted); the goal continues after."""

CONTINUE_PROMPT = """GOAL-RUN ACTIVE (continuation {n}/{cap}) — the goal is not marked done; keep going.
- If you just compacted: re-orient from .claude/checkpoint.md and VERIFY claimed work against git log / the checkpoint's VERIFY commands before building on it — compaction summaries hallucinate completions.
- Advance the highest-value front. Run the portfolio (grind subagents / heretic on what just landed / scout / meta) rather than a single serial thread; don't idle, don't re-derive settled state.
- Goal fully done AND verified → touch .claude/goal-done, write the final summary, stop.
- Genuinely blocked on the human with no other front progressable → append the ask to HUMAN.md, touch .claude/goal-blocked, stop."""


def _context_tokens(transcript: str) -> int:
    try:
        with open(transcript, "rb") as f:
            tail = f.read()[-200_000:].decode("utf-8", "replace").splitlines()
        for line in reversed(tail):
            if '"usage"' not in line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            usage = (entry.get("message") or {}).get("usage") or {}
            if "input_tokens" in usage:
                return (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                )
    except Exception:
        pass
    return 0


def _block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    claude_dir = cwd / ".claude"
    marker = claude_dir / "goal-run"
    if not marker.is_file():
        return 0
    if (claude_dir / "goal-done").exists() or (claude_dir / "goal-blocked").exists():
        return 0
    try:
        threshold = int(marker.read_text().strip() or "100000")
    except Exception:
        threshold = 100000

    # Ritual outranks continuation: it must land before the native compact.
    fired = claude_dir / "goal-wrapup-fired"
    ctx = _context_tokens(payload.get("transcript_path", ""))
    if ctx >= threshold and not fired.exists():
        try:
            fired.write_text(f"ctx={ctx}\n")
        except Exception:
            pass
        return _block(WRAPUP_PROMPT.format(ctx=ctx, thr=threshold))

    # Continuation: Stop = "finished a meaningful unit" — re-kick until done/blocked.
    # Deliberately ignores stop_hook_active (the re-kick loop is the point);
    # MAX_CONTINUES + the done/blocked escapes bound it.
    counter = claude_dir / "goal-continues"
    n = 0
    try:
        n = int(counter.read_text().strip() or "0")
    except Exception:
        pass
    if n >= MAX_CONTINUES:
        return 0
    try:
        counter.write_text(str(n + 1))
    except Exception:
        pass
    return _block(CONTINUE_PROMPT.format(n=n + 1, cap=MAX_CONTINUES))


if __name__ == "__main__":
    sys.exit(main())
