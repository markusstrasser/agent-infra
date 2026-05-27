---
id: 2026-05-27-corpus-as-event-log-repos-as-hybrid
concept: substrate-architecture
repo: agent-infra
decision_date: 2026-05-27
recorded_date: 2026-05-27
provenance: contemporaneous
status: accepted
initial_leaning: "corpus as 'attestation log' with per-repo DBs as projections (CQRS-pure)"
relations:
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-05-27: Corpus is the event log; per-repo DBs are hybrid

## Context

Substrate v2 ships cross-attestation via per-repo outboxes + a shared
corpus drainer. With Phases G0+F+A+B+I+G2 now landed (this plan), the
substrate has the abstractions of an event-sourced system — append-only
JSONL annotations, projection table, supersession chain, bitemporal
valid_from. The natural question: what IS the corpus, and what ARE the
per-repo DBs in this architecture?

Vocabulary matters here because cross-model review and operators
reading the code need a shared mental model. Wrong framing leads to
wrong recommendations (CDC! Kafka! Triple store! Full replay!) that
the substrate is explicitly NOT trying to be.

## Alternatives considered

1. **Corpus = event log; repo DBs = pure projections (CQRS-pure).**
   Repo DBs are 100% rederivable from corpus annotations.jsonl. Any
   repo can be blown away and rebuilt from the event log. This is the
   textbook event-sourcing shape.

2. **Corpus = event log; repo DBs = hybrid (chosen).** Corpus holds the
   cross-repo scientific assertions. Per-repo DBs are a mix of (a)
   materialized slices over corpus events AND (b) repo-local
   authoritative state that does NOT round-trip through corpus.

3. **Corpus = passive cache; repos own everything.** Reverts substrate
   v2's intent. Each repo writes its own truth; corpus is decorative.

## Counterevidence sought

Searched for: a per-repo DB that we could fully rebuild from
annotations.jsonl alone. Specifically checked phenome's claim_certificate_
events (would need ALL cert state in JSONL — it isn't there; cert
identity_key, cert_hash, hard_closure_state are repo-local). Checked
genomics's claim_verdicts (same — verdict_projection_hash + evidence_
projection_hash are local computation derivatives, not corpus-side).

Found: no repo can be rebuilt from corpus annotations alone. Per-repo
backups are REQUIRED. This is the strongest argument against alternative
(1) — it would over-promise on rederivability.

## Decision

**Corpus annotations.jsonl IS the cross-repo event log of substantive
scientific assertions.** Per-repo DBs are HYBRID:

- **(a) Materialized slices over corpus events.** Things like "which
  verdicts has phenome attested" are projectable from
  annotations_current. The audit_corpus_sync drift check is exactly
  this kind of projection comparison.

- **(b) Repo-local authoritative state.** Cert projection hashes,
  verdict_projection_hash, evidence_projection_hash, identity_key,
  per-repo materialized views — these don't round-trip through corpus
  because they're local-computation derivatives that need DETERMINISTIC
  reproducibility, not event-source replay.

**Practical implications:**

- Substantive scientific assertions → corpus annotation (cross-repo
  visible).
- Queryable materialized slices + locally-authoritative computational
  state → repo DBs (backed up per-repo).
- Corpus annotations.jsonl is the load-bearing truth for the assertion
  event log. graph.duckdb is its projection (rederivable via
  `corpus maintain --rebuild-annotations-index`).
- Per-repo DBs are NOT rederivable from corpus alone. Repo backups
  required.

**What this is NOT:**

- NOT code changes, NOT an event-bus, NOT Kafka, NOT a rewrite.
  Substrate v2 stands as-is.
- NOT a commitment that every repo write must go through corpus
  attestation. Local repo state (e.g. genomics `assertions`,
  phenome `todos`) stays local.

## Cross-references

- Substrate v2 decision: `decisions/2026-05-26-cross-attestation-substrate-v2.md`
- Plan that landed this phase: `.claude/plans/2026-05-27-knowledge-infra-next-foundations.md`
- v3 critique that surfaced the framing question: `.model-review/2026-05-27-knowledge-infra-foundations-v3-7865d7/`
- 8-primitive kernel dossier: `research/2026-05-15-cross-project-knowledge-infra-dossier.md`
