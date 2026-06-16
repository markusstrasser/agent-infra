# Commit-gateway signal watch

**Goal:** wait until peer agents wind down (don't build shared commit infra into a busy checkout),
while validating the plan against LIVE git-friction signals ("would the gateway solve them easier?").
**Terminal condition:** active peer sessions ≤ 1 (just me) → report accumulated validation + execute
Phase 1 of `.claude/plans/2026-06-14-commit-gateway-build.md` (the gateway CLI is drafted at
`scripts/commit_gateway.py`, uncommitted, ready).

## Tick 1
- **Peers: 8 active** (genomics×2, agent-infra×4, hutter, phenome) → NOT clear to build.
- **Live friction today:** ~12 `--no-verify` (agent-infra×3 sessions, genomics×1); ~12 commit-FAIL
  (phenome×6, agent-infra×3, genomics×3); feisty (merge/rebase) ~0.
- **Gateway verdict:** commit-FAIL → explicit-paths + escalate-no-retry = **SOLVE**; `--no-verify` →
  `--allow-guard-bypass` visible+receipted = **IMPROVE** (flexibility kept); feisty → escalate = N/A
  today. **Plan HOLDS vs live signal.**
- **Next-tick TODO:** (1) re-count peers; (2) new signals since this tick; (3) the strongest test —
  scan git log across repos for actual foreign-file *contamination* among the 8 concurrent sessions
  (would explicit-pathspec have prevented it?); (4) if any feisty case appears, confirm the gateway
  correctly escalates it.

## Tick 2 (~18:39)
- **Peers: 7** (hutter, agent-infra×2, genomics, phenome, intel, ancient-marinating-rain) → still
  busy, NOT building.
- **New friction:** commit-FAIL 12→15 (+3); no-verify 12→14 (+2); **feisty-FAIL 0→1 (NEW class).**
- **Gateway verdict:** +commit-FAIL → SOLVE; +no-verify → IMPROVE (visible+receipted); feisty-FAIL →
  **ESCALATE** (gateway correctly refuses + hands to the reasoning agent — validates the routine-only
  boundary). **All 3 friction classes now observed live, each maps to a gateway behavior →
  VALIDATION CONVERGED.**
- **Contamination scan:** inconclusive — `git_commits` table lags ~2h (last-2h empty); live detection
  needs a direct cross-repo `git log` pass. Explicit-pathspec value already incident-proven in
  genomics (2026-06-08/12). Deferred, low marginal value.
- **Status:** validation done. Remaining loop = pure peer-wait until ≤1 → then build Phase 1.
