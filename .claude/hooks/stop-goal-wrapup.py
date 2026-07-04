#!/usr/bin/env python3
"""Stop hook: overnight /goal wrap-up trigger at a context threshold.

Opt-in per run: create `.claude/goal-run` in the project (file content = context
threshold in tokens; empty file = 100000, i.e. ~50% of a 200K window; Fable 1M
runs want e.g. 500000). When the session's live context crosses the threshold,
this hook blocks the Stop ONCE with the wrap-up ritual as the reason — the agent
does the session-end work while full context still exists, then self-queues
/compact via `just session-live-compact` (tmux) and ends its turn.

Re-arm: PostCompact removes `.claude/goal-wrapup-fired`, so the next fill cycle
fires again. Fail-open everywhere (P10).

Context measurement: last assistant message's usage in the transcript —
input_tokens + cache_read_input_tokens + cache_creation_input_tokens.
"""
import json
import sys
from pathlib import Path

WRAPUP_PROMPT = """CONTEXT THRESHOLD REACHED ({ctx:,} tokens >= {thr:,}) — run the goal-run wrap-up ritual NOW, while full context exists:

1. Anything to improve/eradicate/rethink with smart tooling, hooks, skills, MCPs, or goal rethinking? Wasted effort or bad infrastructure? What could a future agent leverage? Only long-term, deep, strictly better changes — no noise, no iatrogenic harm; "nothing strictly better" / no-op is a fine answer. No backward compatibility or cruft.
2. Run /rsi.
3. Update docs touched by this session; tie off loose ends that need full context.
4. Write .claude/checkpoint.md (Last Request / Pending Tasks / git state).
5. LAST tool call: `just -f ~/Projects/agent-infra/justfile session-live-compact` (queues /compact + a continue-the-goal message into this session's own tmux pane), then end your turn. If $TMUX_PANE is unset (not in tmux), skip step 5 — auto-compact is the fallback.

Then stop talking. Compaction and continuation happen via the queued messages."""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("stop_hook_active"):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    marker = cwd / ".claude" / "goal-run"
    if not marker.is_file():
        return 0
    fired = cwd / ".claude" / "goal-wrapup-fired"
    if fired.exists():
        return 0
    try:
        threshold = int(marker.read_text().strip() or "100000")
    except Exception:
        threshold = 100000

    transcript = payload.get("transcript_path", "")
    ctx = 0
    try:
        with open(transcript, "rb") as f:
            # usage lives on assistant messages; scan the tail for the latest one
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
                ctx = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                )
                break
    except Exception:
        return 0

    if ctx < threshold:
        return 0
    try:
        fired.write_text(f"ctx={ctx}\n")
    except Exception:
        pass
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": WRAPUP_PROMPT.format(ctx=ctx, thr=threshold),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
