# Fix `/improve maintain` rate-limit gate — `pgrep -lf claude` over-counts, gate is permanently closed

**Boundary:** shared — edits `skills/improve/SKILL.md`, consumed by all projects (3+ blast radius)
**Recommendation:** Change `SKILL.md:456` from
`CLAUDE_PROCS=$(pgrep -lf claude 2>/dev/null | wc -l | tr -d ' ')`
to an exact-name count, e.g.
`CLAUDE_PROCS=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')`
(or `pgrep -fc 'claude --dangerously'` if the intent is "headless agent dispatches" specifically).

**The bug:** `pgrep -lf claude` matches the string `claude` anywhere in any process's *full
command line*, not just claude processes. Because nearly every tool references `~/.claude/...`
paths and many `python3 -c` scripts carry "claude" in args, the count is wildly inflated.
Measured live 2026-06-15 from this research-repo tick:
- `pgrep -lf claude | wc -l` → **1130**
- `pgrep -x claude | wc -l` (exact process name) → **21** (the true count)

The gate is `if CLAUDE_PROCS >= 5: skip Tier-2 subagent dispatch`. With the `-f` count
effectively always ≥ 5 (the `~/.claude/` paths alone guarantee it), **the gate is stuck
closed: the loop never dispatches Tier-2 subagent work even when the fleet is idle.** This is a
silent-proxy defect (constitution P8 — proxy substituted for the principal check) and an
instance of the documented `remote-ssh-ops.md` gotcha #2 (`pgrep -f` self/substring match).

**Dissent / risk:** `pgrep -x claude` counts ALL interactive `claude` REPLs too (every open
window), not just dispatched agents — so on a multi-window day it could over-gate in the other
direction (skip dispatch when you have 6 windows open but zero agents running). If the intent is
specifically "headless agent load," `pgrep -fc 'claude --dangerously-skip-permissions'` is the
sharper proxy. Pick based on what the gate is protecting (total claude API load → `-x`; agent
spawns only → the `--dangerously` filter). Either is strictly better than the current substring
count.

**Open question for you:** which semantic does the gate want — total claude processes (`-x`) or
headless-dispatch load only (`--dangerously` filter)? That's the only judgment call; the fix is
otherwise mechanical and one line in two locations (canonical + symlink, though the symlink
should track canonical automatically).

**Reversible?** Yes, trivially — one-line revert, no state. Cost if wrong: the gate mis-counts in
a known direction, same failure class as today but less severe.

**Evidence:**
- `skills/improve/SKILL.md:456` (canonical) + `~/.claude/skills/improve/SKILL.md:456` (symlink)
- Live measurement this session: `pgrep -lf claude`=1130 vs `pgrep -x claude`=21
- `~/.claude/rules/remote-ssh-ops.md` gotcha #2 (same bug class, already documented)
- Surfaced by: `/improve maintain` cron tick, research repo, 2026-06-15
