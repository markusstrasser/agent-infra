# Route `/improve maintain` Tier-2 dispatch to cursor-agent — dissolves the rate-gate, not just patches it

**Supersedes:** `2026-06-15-improve-rate-gate-pgrep-overcount.md` (the pgrep `-x` fix survives
here as the residual-claude-lane cleanup, but it is no longer the primary fix).

**Boundary:** shared — edits `skills/improve/SKILL.md` (the maintain loop's dispatch model),
consumed by all projects (3+ blast radius). User-directed (operator: "use agent (cursor
subagents)", 2026-06-16) + reversible, but it changes how the loop dispatches across every repo,
so it goes through sign-off + cross-lab critique per constitution P12 rather than a silent edit.

## The reframe

The original finding was "the rate-gate's `pgrep -lf claude` substring-matches every
`~/.claude/...` path (1130 vs true 21), so the gate is stuck closed and the loop never dispatches
Tier-2 subagents." That's true, but the **gate is measuring the wrong process class.** It counts
`claude` processes to decide whether to add load — but the dispatch it throttles draws on the
claude subscription only because it uses the claude Agent tool. Route Tier-2 dispatch to
`cursor-agent` (separate process, Cursor's quota) and the claude-proc count is no longer the
relevant pressure signal for that lane.

This converges with two independent signals:
- **`/model-guide` codebase-coupled row** (operator `#f` 2026-06-16): repo-coupled critique should
  run with real repo access via `cursor-agent -p -f --mode ask --model
  claude-opus-4-8-thinking-high` — it flags "already-handled at file:line" vs "genuinely-open,"
  which a cold API model can't. Memory: `feedback-cursor-agent-for-codebase-review`.
- **Subagent zero-output bug** (`anthropics/claude-code#47936`, verified OPEN 2026-06-16, local
  rate 0.17%→4.2% rising): a claude-Agent-tool failure mode. cursor-agent persists output to the
  repo directly and has no silent-completed-with-zero-output mode, so the write-first gate friction
  (`pretool-subagent-gate.sh` checks 7+10, fired 3× in one dispatch this session) doesn't apply to
  the cursor lane.

## Proposed lane split (in `improve/SKILL.md` "Rate Limit Check" + "Tier 2: Dispatched Work")

| Lane | Tool | Rate signal | Notes |
|---|---|---|---|
| Repo-coupled execution / critique (common case) | `cursor-agent -p -f --mode ask --model claude-opus-4-8-thinking-high` | Cursor quota; loop already caps Max-1/tick | model-guide-endorsed; repo-grounded |
| Read-only search fan-out | claude `Explore` agent | claude subscription | residual claude lane — keep `pgrep -x claude` gate (the surviving piece of the superseded proposal) |
| Non-repo synthesis | claude `Agent` / `llmx --subscription` | claude subscription | write-first gate (`#47936`) keeps earning its keep here |

So the `pgrep` fix is **not deleted** — it's demoted to gating only the residual claude lanes,
where `pgrep -x claude` (total claude procs, the account-wide rate-limit-relevant count) is correct.
The cursor lane is gated by the existing Max-1-per-tick cap, not a proc count.

## Open question for sign-off

cursor-agent `--mode ask` is read-only (critique/analysis — the bulk of the loop's Tier-2 work).
For the rare **write/execute** dispatch the loop does (multi-file fixes), the lane is cursor-agent
*agent-mode* (not ask) or stay on claude Agent + worktree isolation. Do we (a) route only
read/critique dispatch to cursor and keep write-dispatch on claude+worktree, or (b) move write
dispatch to cursor agent-mode too? Recommend **(a)** — narrowest change, keeps the proven
worktree-isolation path for mutations; revisit (b) only if a measured win appears.

## Reversible?

Yes — `improve/SKILL.md` text only, no state. One-section revert. Cost if wrong: dispatch lane
mis-routed, same severity as today (today the gate is stuck closed, so any working lane is strictly
better).

## Before implementing

- [ ] Cross-lab critique (`/critique model`) on this lane split — P12, shared infra.
- [ ] Confirm cursor-agent ask-mode output convention matches the loop's file-output/manifest gate
      (it writes to repo; verify the coordinator can read the result deterministically).
- [ ] Separate, smaller follow-up: auto-INJECT the write-stub instruction in
      `pretool-subagent-gate.sh` instead of BLOCKING (keeps the #47936 guard, kills the
      re-author-the-prompt friction) — gated on whether PreToolUse can mutate `Agent` input on this
      CC version. File its own proposal if feasible.

**Evidence:**
- `/model-guide` Dispatch Economics + codebase-coupled row; operator `#f` 2026-06-16
- `#47936` OPEN (verified 2026-06-16 via claude-code-guide); `subagent-zero-output-gate-stays`
- cursor-agent live: `2026.06.15` build, authed (`cursor-agent status` ✓)
- `feedback-cursor-agent-for-codebase-review` (memory)
