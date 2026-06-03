---
id: 2026-06-03-corpus-test-pollution
concept: corpus-integrity
repo: agent-infra
decision_date: 2026-06-03
recorded_date: 2026-06-03
provenance: contemporaneous
status: accepted
initial_leaning: "fail-closed: raise when CORPUS_ROOT unset under pytest"
relations:
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-06-03: Corpus test-fixture pollution — redirect at the sole writer, not fail-closed-raise

## Context

`audit_corpus_sync.py` reported `DRIFT: 30 verdict` (genomics orphan annotations) — a
signal that had been firing daily (exit 1) and going unconsumed. Read-only investigation
(`.scratch/orphan-annotations-investigation-2026-06-03.md`) found the cause.

## Finding (fact, not churn or data loss)

**30 test-fixture verdict annotations leaked into the PRODUCTION corpus** (`~/Projects/corpus`)
during genomics pytest runs on 2026-06-02:
- All 30 are hard-absent from `claim_verdicts` under any `review_status` (459 current + 493
  superseded checked) — they were never real verdicts.
- Fixture fingerprints: `recorded_at` in 4 clusters on 2026-06-02 (suite ran ~4×); `source_id`
  ∈ {pubmed_1, p1, p_ok, src_c0…}; `actor_id` ∈ {m1, model-1…}; ids match
  `test_bitemporal_invariants.py`, `test_mutation_gateway_atomicity.py`,
  `test_contradiction_relation_promotion.py` verbatim.
- **Mechanism:** `MutationGateway.write_verdict` drains attestations on `__exit__` via
  `corpus_core.annotate`, which resolves `CORPUS_ROOT` — defaulting to prod when unset. Only
  **2 of 17** gateway-using test files pin `CORPUS_ROOT` to tmp; the conftest leak-guard checks
  env/module leaks, not filesystem writes.
- **Blast radius > 30 graph rows:** also created git-tracked `annotations.jsonl` ledgers in 5
  prod source dirs, now in corpus git history (corpus `.gitignore` tracks JSONL, ignores
  `*.duckdb`).

This is the diagnosis pattern in the wild: a verifier (the audit) caught it; the signal was
never consumed.

## Decision (proposed — awaiting approval)

Three parts, by blast radius:

1. **Defense-in-depth at the sole writer (`corpus_core`, agent-infra).** Under pytest
   (`PYTEST_CURRENT_TEST` set) with `CORPUS_ROOT` unset, `store_root()` resolves to a throwaway
   tmp dir — **redirect, NOT raise.** *Initial leaning was fail-closed-raise; rejected* because
   15 of 17 unpinned suites would break **fleet-wide across ~26 active sessions** — detonating
   mass test failures into others' in-flight work. Redirect prevents pollution with zero
   breakage (writes+reads share `store_root`, so round-trips stay self-consistent). Shared infra
   (3+ repos) → human-approved; apply when the genomics suite is runnable to verify (post
   quota-reset / fleet quiet).
2. **Genomics test boundary** — autouse conftest pinning `CORPUS_ROOT`/`PROJECTS_ROOT` to tmp +
   a filesystem leak-guard. Must land coordinated with #1. (Also check phenome/intel gateway
   tests for the same gap.)
3. **Cleanup — purge the 5 fixture source dirs + rebuild `graph.duckdb`.** Destructive, touches
   prod corpus + git history → **explicit human approval required**; do deliberately after #1/#2
   stop the bleeding. NOT a reconcile-via-retract (these aren't real verdicts).

## Counterevidence sought

Checked whether the 30 could be legitimate superseded/retracted verdicts (expected churn) or
hard-deleted real verdicts (data loss): neither — absent under all `review_status`, and the
fixture fingerprints are conclusive. Checked a migration cause via genomics git log: none; the
`recorded_at`/fingerprints date it to test runs, not a migration.

## Revisit if

- The redirect masks a test that legitimately asserts on corpus output (it should pin
  `CORPUS_ROOT` itself; #2 does this for genomics).
- audit_corpus_sync's daily exit-1-on-drift remains unconsumed — the deeper fix is routing that
  signal to a consumed surface (the report-into-void layer above this incident).

## Supersedes
None. Instance of the failure class in `research/closed-loop-boundary-and-system-awareness.md`
(§5.1 self-referential/unconsumed verifiers) and `decisions/2026-06-03-verifier-bound-autonomy.md`.

## Revisions

**2026-06-04 — Implemented as dependency injection, NOT redirect (supersedes the Decision above).**
The shipped fix is deeper than this record's proposed "redirect" *and* the rejected "raise":
the ambient `CORPUS_ROOT`-with-prod-default was **deleted by construction.**
- `8a0a790` — extract a `CorpusStore` handle, remove the root singleton (22 corpus_core modules).
- `3f0c81c` — entrypoints (CLI/MCP/ingest/audit) **require an explicit `--corpus-root`**, fail closed.
- `9e7434a` — 17 test files migrated to isolated temp stores.
Validated 2026-06-04 (reality-anchored, not commit-message trust): no residual env-default /
`store_root` singleton / prod fallback in corpus_core; `audit_corpus_sync` *errors* without
`--corpus-root` (fail-closed confirmed live); corpus-core suite **182 passed, 1 skipped**. The
leak path is closed by construction — neither redirect nor raise was needed. `status → accepted`
for the §1 architecture.

**Still pending: cleanup (was §3).** The 30 already-leaked fixture annotations remain in prod
corpus (`audit_corpus_sync --corpus-root ~/Projects/corpus` → `DRIFT: 30 verdict`) plus the 5
git-tracked `annotations.jsonl` ledgers. Destructive (prod-data delete + git history) → needs
deliberate, snapshot-first execution; not yet done.

**2026-06-04 (later) — cleanup DONE.** Removed the 5 pure-fixture ledgers
(`p1`/`p_ok`/`src_c0`/`src_c1`/`pubmed_1` — 0 real data; verdict ids `01J0…`/`vrd-…`, all
2026-06-02), reprojected annotations + claim_relations from remaining ledgers, verify-replay
clean (661 rows, 0 missing/extra/mismatched), drift **30 → 0**. `corpus@3b4cff56`; pre-cleanup
snapshot at `/tmp/corpus-graph-snapshot-20260604.duckdb`. **Incident fully closed** — the DI
migration prevents recurrence, the historical pollution is purged.
