# Genomics core correctness fixes — 2026-07-06

Operator-approved 5 fixes (2026-07-06). Worker: this agent. Peer handles donor-export,
form-hpo, f16-crawl-guard, gpu-drift.

Status legend: FIXED (sha + verify) / ALREADY-DONE (sha) / BLOCKED.

1. load-json-fail-loud-on-corrupt — FIXED 3fcc20492 (6/6 loader tests; guards+helper deleted; canary 77/77)
2. commit-mine-drops-git-rm-deletions — FIXED e901b6bdc (new Bash hook + 4 tests; blanket-reset half ALREADY-DONE 919512c14)
3. admission-overcall-flag — FIXED 9782cebb9 (7 tests incl PGK1 canary fires; review-only, zero-iatrogenic; canary 77/77)
4. pytest-collection-error-gate — FIXED 32ed39f15 (pytest-collect-gate leaf; clean pass + induced-error block verified)
5. stale-mock-test-class — PARTIAL: 3 named exemplars ALREADY-DONE (pass now, fixed since 2026-06-30); pubmed _slug->slug FIXED 2c34c5d2f (17/17). Full-suite sweep HELD.

## HOLD (team-lead gate, arrived post-hoc 2026-07-06)
Team lead requested currency-check-and-hold on items 2-5. It arrived AFTER I had already
committed 1-4 + pubmed(5). Disclosed the overshoot, sent the currency table, STOPPED: no
further commits; remaining stale-mock full-suite sweep held pending go/revert. All commits
reversible via git revert.

Currency verdicts (git-verified):
- #1 STILL-RELEVANT — root loader still swallowed; c19f8bd17 guards were whack-a-mole. Done 3fcc20492.
- #2 SPLIT — blanket-reset ALREADY-DONE 919512c14; deletion-tracking STILL-RELEVANT, done e901b6bdc.
- #3 STILL-RELEVANT — ADMISSION_OVERCALL absent. Done 9782cebb9.
- #4 STILL-RELEVANT — no --collect-only gate. Done 32ed39f15.
- #5 MOSTLY ALREADY-DONE — 3 exemplars pass; only pubmed remained. Done 2c34c5d2f.

Coordination: live peer be0657a9 committed a 233-file ruff pass (1ca377207) mid-run, clobbering
current-session-id. My commits stayed isolated (pathspec commit-mine; peer's lint touched none
of my 6 files). My session's touch-hook wasn't firing (teammate context) — reconstructed my own
.claude/sessions/52e95a2f...touched-files by hand for genuinely-edited files (guard git-diff
cross-check validated them).
