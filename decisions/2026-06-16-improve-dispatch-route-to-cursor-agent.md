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

## The change (one line, in `improve/SKILL.md` "Rate Limit Check" + "Tier 2: Dispatched Work")

**Route repo-coupled Tier-2 dispatch to `cursor-agent -p -f --mode ask --model
claude-opus-4-8-thinking-high`.** That lane runs on Cursor's quota and is gated by the loop's
existing Max-1-per-tick cap, so the broken claude-proc count no longer gates it.

Everything else is status quo, not part of this change: search fan-out stays on claude `Explore`,
non-repo synthesis stays on claude `Agent`/`llmx`. For those residual claude lanes the surviving
piece of the superseded proposal applies — fix `pgrep -lf claude` → `pgrep -x claude` (account-wide
count is the rate-limit-relevant signal). That's a one-line cleanup, not a new architecture.

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

---

## P12 cross-lab critique verdict — 2026-06-19

Cross-model critique run (`.model-review/2026-06-19-critique-…-2fd78d/`): 54 claims →
16 confirmed, 5 hallucinated, 32 inconclusive. The premise-scout (cursor-agent, repo-coupled)
**timed out at 90s**, so the dispatch fell back to repo-blind external models — which produced
the one hallucination that matters:

- **REFUTED (hallucination):** "`pgrep -x claude` returns zero because Claude Code is Node.js."
  Principal check on this machine: `pgrep -x claude` = **5** real processes; the executable is
  literally named `claude` (`/Users/alien/.local/bin/claude`), not `node`. The `-x` fix is
  correct here. (Classic context-blind-model environment hallucination — `feedback-cursor-agent-for-codebase-review`.)

**The confirmed findings all converge on ONE thing:** routing Tier-2 to cursor-agent — even the
narrow option (a) — is **NOT a one-line change**. Replacing a lane in the shared `improve/SKILL.md`
with an external-CLI dependency requires an operational safety wrapper, or a cursor-agent
auth-expiry / missing-binary / quota-stall **silently breaks the maintain loop across every repo**:
- output contract undefined (read-only `--mode ask` vs "persists to repo" — contradictory) [#2,#8,#21,#30]
- no install/auth preflight, no exit-code/timeout handling, no fallback to the claude lane [#3,#11,#17,#20,#49]
- immediate cutover, no canary, high blast radius on shared infra [#18,#19]
- high-latency model / quota may starve the per-tick loop; worktree-escape risk [#44,#48,#46]

## Disposition — DECOUPLE (the decision conflated two changes)

The original framing made the **urgent cheap fix hostage to the larger architectural change**.
The critique vindicates splitting them.

## RESOLVED 2026-06-19 — both SHIPPED (operator approved "do both")

- **Fix A — SHIPPED** (`skills@ca6ea0f`). `pgrep -lf claude` → `pgrep -x claude` at
  `improve/SKILL.md:457`. Un-breaks the dead Tier-2 gate (verified `-x`=5 vs `-lf`=105).
- **Fix B — SHIPPED** as a hardened wrapper, not prose (`skills@d3cc9d7` +
  `scripts/cursor_dispatch.sh`). Preflight (binary + `isAuthenticated`) → shell-`timeout`-bounded
  run → ANSI-stripped capture → FALLBACK exit codes 10–14 → caller re-dispatches to the claude
  Agent lane. Smoke-tested live (real Composer dispatch happy-path + fallback branches).
- **Operator directive 2026-06-19:** cursor lane **defaults to Composer** (best price/perf,
  encouraged), not opus; opus is an opt-in `--model` override for rare high-stakes. Memory:
  `feedback-cursor-default-composer`.
- **CLI ground-truth corrections** (verify-before-documenting paid off): cursor-agent has **no
  native `--timeout`** (wrapped with shell `timeout`); `--mode` accepts only `plan|ask`;
  `-f`=`--force`; the model string `claude-opus-4-8-thinking-high` IS valid (confirmed via
  `--list-models`, refuting critique finding #38). The critique's load-bearing hallucination
  (`pgrep -x`=0 "because Node.js") was refuted by the principal check (binary is named `claude`).
