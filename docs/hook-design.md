# Hook design

Read when implementing or evaluating hooks. Current fail-open/fail-closed boundaries remain in CLAUDE.md. Inventory and vendor details below are historical context; use just orient and current vendor docs for current state.

- **Four hook types:** `command` (bash), `prompt` (Haiku LLM call ~$0.001), `agent` (multi-turn subagent), `http` (POST). Use deterministic command hooks for concrete invariants; use prompt hooks for semantic judgment calls (unsourced claims, unverified completion).
- Fail open unless blocking is clearly worth it. All prompt hooks wrapped with 3-10s timeout.
- `trap 'exit 0' ERR` swallows `exit 2` from Python — disable trap before critical Python calls.
- Stop hooks must check `stop_hook_active` to prevent infinite loops.
- **Deployed prompt hooks:** Agent dispatch turn-budget validation (PreToolUse), Stop verification of claimed work (Stop), unsourced claim detection (PostToolUse Write|Edit).
- **Hook fleets become dispatchers (2026-07-13).** N same-matcher command hooks = N process spawns + N stdin re-parses per event (measured: intel's 42 Write|Edit gates = 7.5s/edit, 38× cut; the 2 universal hooks' jq storm = 264ms/tool-call, 2.6× cut). At ~5+ hooks on one matcher, consolidate into ONE parse-once dispatcher that importlib-loads each gate's unmodified `main()` (stdin swapped, SystemExit caught) — zero edits to gate files keeps standalone contracts and is a behavioral mirror by construction. Ship with a frozen pre-migration snapshot fixture + parity pytest, fail-open wrapper, fail-fast on first exit-2. Reference impls: intel `.claude/hooks/pretool_writeedit_dispatch.py` · skills `hooks/pretool-universal-dispatch.py`.
- Hook inventory and event types are **derived, never hand-listed**: `just orient` prints live fire count, unique scripts, and the per-event breakdown; `just hooks-smoke` catches silently-dead hooks; `just hook-roi` / `just hook-decay` flag advisory noise to cull and over-aggressive gates to demote.
