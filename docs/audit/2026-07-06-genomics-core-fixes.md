# Genomics core correctness fixes — 2026-07-06

Operator-approved 5 fixes (2026-07-06). Worker: this agent. Peer handles donor-export,
form-hpo, f16-crawl-guard, gpu-drift.

Status legend: FIXED (sha + verify) / ALREADY-DONE (sha) / BLOCKED.

1. load-json-fail-loud-on-corrupt — FIXED 3fcc20492 (6/6 loader tests; guards+helper deleted; canary 77/77)
2. commit-mine-drops-git-rm-deletions — FIXED e901b6bdc (new Bash hook + 4 tests; blanket-reset half ALREADY-DONE 919512c14)
3. admission-overcall-flag — IN PROGRESS
4. pytest-collection-error-gate — PENDING
5. stale-mock-test-class — PENDING
