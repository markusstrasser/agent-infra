# Worktree GC Sweep — 2026-07-06

PROBE IN PROGRESS

## Scope reconciliation

Control-plane `--check` now reports **6 LAND / 2 INSPECT / 1 REAP**, but 4 of those
are **live arc-agi peer sessions** committing seconds/minutes ago — EXCLUDED (task:
never touch live peer work). The task's intended stale set (3 LAND / 1 INSPECT "pub" /
1 REAP) maps to:

| Disp | Repo/branch | ahead | age | status |
|------|-------------|-------|-----|--------|
| LAND | substrate/worktree-agent-a1a05d9f236aac59a | 2 | 8d | pending |
| LAND | substrate/worktree-agent-a9d90b0c2c159a0f9 | 2 | 8d | pending |
| LAND | substrate/worktree-agent-ade0fd3e6f3d2b12e | 2 | 8d | pending |
| INSPECT | publishing/worktree-agent-a50704d3c6939405b | 13 | 7wk | pending |
| REAP | genomics/worktree-agent-aab883543a1e2fd6b | 1 (DUP) | 2h | pending |

EXCLUDED (live arc-agi peers): a36c381 (INSPECT, 9min, dirty), a770d7fe (82s),
ab45524 (2min), ad8f0c25 (2min).

## Per-branch findings (appended as confirmed)

### substrate/a1a05d9f (synonyms) — LANDED f9c51eb
- 2 unmerged commits (both `+` in cherry), additive: synonyms.py (445) + tests (168) + research memo (147). No file modifications.
- Target `bio-reference/ontology/` is LIVE on main (last commit ed17219, ADR 0022); kill commit f61c9b6 did NOT touch bio-reference.
- Imports only `bio_reference.ontology.sources` + `reference_root` — no coupling to removed corpus-extract/claim-KG stack.
- No pre-existing synonym work on main (not a dup). merge-tree clean.
- Merged --no-ff → f9c51eb. Post-merge `pytest test_ontology_synonyms.py` = **6 passed**.

### substrate/a9d90b0c (faithfulness gate) — NOT LANDED (superseded → report)
- Targets `packages/corpus-extract/` which main **deleted 6h ago** in f61c9b6 "Remove claim-KG stack — no capability edge (kill-switch 2026-06-29)".
- merge-tree reports "clean" only because git resolves (main deletes package) + (branch adds new files) with no textual conflict — result would RESURRECT a partial orphaned package into a deliberately-killed stack.
- Commit itself says "deferred wire-in" — never integrated. Recommend REAP (branch), or cherry-pick just the research memo if the operator wants the measurement retained.

### substrate/ade0fd3e (drug→RxNorm xref) — NOT LANDED (superseded → report)
- Same as above: targets deleted `corpus-extract`. Superseded by kill-switch f61c9b6. Recommend REAP (branch); memo `2026-06-28-drug-rxnorm-recall-fork.md` is the only salvageable artifact.

### genomics/aab883543 — REAPED
- Single commit 66fb68a63; `git cherry` = `-`; **patch-id identical** (5c2e2c26...) to main's f1867d205 "[payload] Gate 3 cohort absent-input silent-zeros" — byte-for-byte already on main.
- Worktree clean. Removed dir + `git branch -D` (recoverable via reflog 90d). Native `--include-unmerged --prune-branches` avoided: it would collaterally drop live arc-agi/substrate unmerged worktree dirs + the genomics-e2e-sim SAFE branch.

### publishing/a50704d3c ("pub" INSPECT) — LEFT (reap-recommended, blocked on uncommitted files)
- 13 commits (enhanced:img migration Phases A-G). `git cherry`: 12 = `-` (on main); 1 = `+` (Phase A 6bfe882).
- Phase A's `+` is representational only: range-diff vs main's equivalent `ef98973` shows the sole diff is rename-vs-new-file for a few images. Net effect IS on main — `src/lib/images/essays` present, `static/media/essays` deleted. Whole migration superseded.
- Worktree is DIRTY: 3 modified tracked files (`.claude/settings.local.json`, `src/lib/data/essays.ts`, `src/lib/favicon-map.json`) + 1 untracked favicon — an unrelated in-progress edit. NOT TOUCHED.
- Cannot reap: branch is checked out; removing the dir would discard the uncommitted files. **Recommend operator: rescue/discard the 3 dirty files, then `git branch -D worktree-agent-a50704d3c6939405b`** — the 13 commits add nothing over main.

## Summary

| Disposition | Branch | Result |
|-------------|--------|--------|
| LANDED | substrate/…a1a05d9f | merge f9c51eb (tests 6/6 pass) |
| REAPED | genomics/…aab883543 | dir removed + branch -D (patch-id identical to main f1867d205) |
| LEFT (reap-rec) | publishing/…a50704d3c | superseded but blocked on 3 uncommitted files |
| LEFT (reap-rec) | substrate/…a9d90b0c | targets deleted corpus-extract (kill f61c9b6) |
| LEFT (reap-rec) | substrate/…ade0fd3e | targets deleted corpus-extract (kill f61c9b6) |
| EXCLUDED | arc-agi ×4 (a36c381, a770d7fe, ab45524, ad8f0c25) | live peer sessions, committing seconds/minutes ago |



