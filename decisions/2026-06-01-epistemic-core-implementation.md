---
id: 2026-06-01-epistemic-core-implementation
concept: epistemic-core
repo: agent-infra
decision_date: 2026-06-01
recorded_date: 2026-06-01
provenance: contemporaneous
status: accepted
initial_leaning: follow the v2 plan literally — relation in a content-addressed sidecar, migrate edges.stance_class to 5-class in Phase 1, run the citation-edge fill
relations:
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
  - type: cross_repo_of
    target: 2026-05-27-corpus-as-event-log-repos-as-hybrid
---

# 2026-06-01: Epistemic core — four implementation-time forks vs the plan

## Context
Building the greenlit epistemic-core layer (durable cross-repo claim_relation;
plan `.claude/plans/2026-05-31-epistemic-core-contradiction-refutation-layer.md`).
Reading the actual corpus_core / phenome / genomics code surfaced four forks the
plan under-specified or got wrong. Recorded because each forecloses an
alternative and would be costly to re-derive.

## Alternatives considered (per fork)

**Fork A — how the relation rides the ledger.**
1. Content-addressed SIDECAR (plan v1, pre-critique) — two writes, non-atomic.
2. Separate relation.jsonl record type + writer — parallel append log, atomic, but a second writer/file/projection surface.
3. **Inline on the annotation** (extended schema 1-0-1, optional `relation` body) — one writer, one file, one atomic O_APPEND, one projection. Substrate owns relation identity (content-addressed `relation_id`) + idempotency (output_hash = relation sha).

**Fork B — edges.stance_class 5-class migration timing.**
1. Migrate in Phase 1 (plan as written).
2. **Defer to Phase 6, with its consumer** — the only thing that writes 5-class edge values is the citation adjudication; migrating early breaks the corpus_mcp contradictions query for zero benefit and violates single-variable-commit discipline.

**Fork C — Phase 6 citation-edge fill.**
1. Run the 2055-edge LLM adjudication + edges migration (plan, gated).
2. **Probe first, then don't ship** — the gate needs operator labels AND the signal must exist.

**Fork D — support_balance directionality.**
1. All relations symmetric (both endpoints).
2. All relations directional (object only).
3. **Split: conflict (refute/qualify) symmetric, endorsement (support/extend) directional** — a mutual contradiction lowers both assertions; an endorsement raises only the endorsed object.

## Counterevidence sought
- Fork A: looked for a size case that breaks inlining — multi-party relations stay <1 KB (spans referenced by id, not text); the 4 KB ceiling that motivated sidecars was artificial (raised to 16 KB). No case found where inline overflows.
- Fork C: did NOT stop at "weak signal" intuition — probed the live 2055 snippets. Searched for genuine A-refutes-B citations: cue-word upper bound 7.8% (161/2055), and inspecting those, they are mixed-literature summaries ("several studies proved X but others failed to find it"), not citation-level refutations. Genuine refutations <2%, deduplicated. The opposite (a rich latent stance signal) was actively looked for and not found.
- Fork D: checked whether symmetric-refute mis-scores genomics (evidence refutes claim, directional) — it tallies the db_ source endpoint at -1, but db sources are not consumer claims, so the only consumer-visible effect (the refuted CLAIM at -1) is correct. Searched for a consumer that reads a db-source support_balance; none exists.

## Decision
A→3 (inline), B→2 (defer), C→2 (don't ship, measured), D→3 (split). Governing
principle held throughout: **deep in the substrate, simple in the inference.**
Phase 1 came out purely ADDITIVE (graph 1.2.0→1.3.0, outbox 1.4.0, min_reader
held back; live graph.duckdb migrated with 658 annotations / 2055 edges / 209
papers intact). Two cross-repo subtleties, both validated by tests:
- **Home repo owns participant liveness** — the corpus stays domain-agnostic; a
  repo emits a superseding relation when a participant is retracted/resolved.
- **Retraction needs a distinct output_uri** — annotation identity excludes
  status, so a same-content retraction collapses onto the active annotation_id;
  the retraction carries a `.../retraction` URI + supersedes pointer so
  rebuild_claim_relations drops the prior refute from the active surface.

## Evidence
67+ tests green (15 corpus-core + 6 phenome + 6 genomics + 40 atomicity/drain).
Phase-0 census: phenome 6 contradiction_pairs (100% source-null → virtual
sources mandatory), genomics 1 contradicted verdict (superseded). Phase-6 probe:
`.scratch/phase6-citation-signal-probe-2026-06-01.md`. Live read-loop smoke:
refute relation → `epistemic.conflict:true`, support_balance −1.0 on lookup.
Commits: agent-infra 42eca2d/ce73351/af86a3c, phenome 75061fd, genomics e7a9999b.

## Revisit if
- A marker-modal re-ingest of the 209 papers yields cleaner, segmented citation
  contexts → re-probe stance density before reconsidering Fork C.
- Cross-repo relations (phenome-claim vs genomics-claim, the deferred embedding
  retrieval) arrive → participant-liveness can no longer be fully home-owned;
  add a liveness check (reopens the Fork-A delegation).
- Relation volume grows enough that a relation↔home-table drift audit earns its
  maintenance (deferred now at N≈3).

## Supersedes
Supersedes the sidecar/paper-keyed/Phase-1-edges-migration choices in plan v1
(already superseded in the plan by /critique, hardened here by implementation).
