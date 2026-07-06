# Shared Hooks Batch — 2026-07-06

Operator-approved (2026-07-06, explicit "ship all 8") shared/global hook changes.
Every hook kept fail-open/warn posture; no NEW blocking behavior. Commits are granular,
specific-path staged (never `-A`), each with an `Evidence:` trailer. The unrelated
`model` setting change in `~/.claude/settings.json` was left untouched (excluded via `git add -p`).

| # | Item | Status |
|---|------|--------|
| 1 | userprompt-clock | SHIPPED — skills `57d72e2`, reg `.claude c3cfa1a` |
| 2 | askuserquestion-autonomous-warn | SHIPPED — skills `4ad1cc7`, manifest `ai 5fc2cbd`, reg `.claude 9166800` |
| 3 | unstarted-goal-detection | SHIPPED — skills `3a2fd5b`, goal-night `ai c61684a` |
| 4 | codex-exec-stdin + bg-relative-path (merged) | SHIPPED — skills `bc6f557`, manifest `ai 1fac276`, reg `.claude ccd6610` |
| 5 | live-peer-work-visibility | SHIPPED — skills `1d52f5d` |
| 6 | researcher-pathological-empty-stop-gate | SHIPPED as SHADOW — skills `da792bc` |
| 7 | stop-hook-suppress-resurfaced-unattributable | ALREADY-DONE — `_fresh_unattributable` (`d1907d3`/`52db803`) |
| 8 | deletion-guard-attribution-verify-first | SHIPPED — skills `d5b13f7` |
| + | shared-checkout-reset-wipes-peer-work | PARTIAL/BLOCKED — see below |

## Notes on the judgment calls

**#6 (researcher pathological-empty)** — proposal was flagged "do NOT ship blind." The naive
"research calls + no provenance-tagged write" predicate fired on **76/486** real transcripts
(coding subagents Read+Write). Revised to "≥6 research calls AND total write content < 400 chars,
no tag" → **9/486**, ALL `write_calls==0` (genuinely wrote nothing). Shipped as SHADOW (never
blocks, logs would-fire to `~/.claude/subagent-empty-research-shadow.jsonl`), researcher-Stop only.
Promotion to advisory/block needs a precision review of the shadow log — do NOT auto-promote.

**#3 (unstarted-goal)** — needed a goal↔deliverable binding that did not exist. Added an opt-in
`.claude/goal-deliverable` marker (a progress-check command); the goal controller reads it and, on
zero progress while continuing, prepends a loud one-time UNSTARTED warning. No marker → no firing.
goal-night clears the warn-marker on re-arm.

**+ (shared-checkout-reset)** — the hookable core (peer uncommitted work swept into the `[wip]`
auto-checkpoint) is ALREADY-DONE since the proposal was filed: `stop-uncommitted-warn.sh` never
auto-commits contested or contested-by-content files (`52db803` + `ce59d36`). The remaining danger
(session-end `git reset --hard` DISCARDING peer uncommitted work) is a **harness-internal action,
not a hook we control** — there is no safe reset-path change to ship, so per the operator's gate
("report BLOCKED rather than ship a risky reset-path change") it is BLOCKED as a hook change. Guards
#2 (verify worktree isolation at dispatch) and #3 (resolve committing session from the Session-ID
trailer, not shared `current-session-id`) are separate features each needing a dedicated
no-work-loss test — out of scope for this batch.

## Gate
`just harness-eval` GREEN after every edit. Final: **hooks smoke pass=291** (baseline 287 → +4 new
registered hooks: clock, bg-dispatch-footgun, askuserquestion-warn; +peer-work/shadow/goal helpers
not separately smoke-counted), 52 hooks / 41 global pretools covered, 26 approval-tier + all suites pass.
