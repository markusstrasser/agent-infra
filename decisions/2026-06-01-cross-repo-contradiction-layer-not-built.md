---
id: 2026-06-01-cross-repo-contradiction-layer-not-built
concept: cross-repo-epistemics
repo: agent-infra
decision_date: 2026-06-01
recorded_date: 2026-06-01
provenance: contemporaneous
status: accepted
initial_leaning: extend the corpus with a cross-repo contradiction layer (shared embeddings → retrieval → adjudication → phenome read-loop) — the "attestation moat"
relations:
  - type: branches_from
    target: 2026-06-01-epistemic-core-implementation
---

# 2026-06-01: Do NOT build a corpus-mediated cross-repo contradiction layer

## Context
The epistemic core (within-repo durable claim_relations + read-loop) shipped this
session. The stated next "extend this" — and the long-running framing of the whole
substrate's moat — was a **cross-repo** contradiction layer: detect when a genomics
finding refutes a phenome assertion (or vice versa) about the same entity, and surface
it. The roadmap (`.claude/plans/2026-06-01-science-graph-remaining-roadmap.md`) scoped
this as Group B: shared Gemini-Embedding-2 space → candidate retrieval → LLM adjudication
→ cross-repo `claim_relations` → phenome-side read-loop. Cross-model critique sharpened
the gate from "entity overlap" to "demand first." A demand probe was then run over
agentlogs.db (last 60d, 1752 sessions) **before building anything**.

## Alternatives considered
1. **Build Group B as specified** (embeddings → retrieval → adjudication). The "flagship."
   Pro: cross-repo contradictions are the one thing the corpus adds over each repo's local
   view. Con: large standing infrastructure (embedding-sync service) for N=1 low throughput.
2. **Build a lighter on-demand lexical/FTS adjudication tool** (no embedding pipeline),
   gated on a demand+overlap probe. The critique's preferred shape.
3. **Do not build any cross-repo contradiction layer.** Keep the corpus as a within-repo +
   per-repo attestation/relation ledger; let cross-repo concerns live where they already do.

## Counterevidence sought
The probe was explicitly designed to *falsify option 3* — to find demand that would
justify building. What it found instead **confirmed option 3**:
- **An active phenome↔genomics bridge already serves cross-repo data flow, and it is not
  the corpus.** `genomics/scripts/bridge_artifact.py` emits a hash-verified, content-
  addressed artifact set (`case_bundle`, `pgx_card`, `clinician_summary`, `review_packets`);
  `phenome/src/phenome/bridge/` consumes it with staleness detection; `phenome/mcp/
  genomics-consumer/` exposes `kg_*` graph tools with per-edge source attestation. 326
  file-touches across 23 sessions in 60 days; last built 2026-05-31. → the embedding/
  retrieval stack to "discover overlap" is **redundant, not speculative**.
- **0 cross-repo contradictions on record, ever** (corpus relation layer: 2 relations,
  both intra-phenome). No demand for the contradiction layer ever materialized.
- **The atomic-claim surface is shrinking.** Genomics *retired* `variant_phenotype_overlay`
  (commit 26b7e93c) — the one artifact that mapped variant→phenotype, the natural
  contradiction surface. The producer moved toward bundled clinical summaries.
- **Epistemically thin at this boundary.** Genomic predisposition (PRS/risk) vs phenotype
  realization are different claim types; penetrance < 1 means high risk does not *contradict*
  an absent phenotype. The apt relation is weak "support," already carried by the bridge.

Searched for the opposite (real cross-repo contradiction demand) and found none.

## Decision
**Do not build the cross-repo contradiction layer (Group B deleted from the roadmap, not
deferred).** The corpus's role is a **within-repo + per-repo durable attestation/relation
ledger with a deterministic read-loop** — not a cross-repo contradiction moat. Cross-repo
data flow is owned by the existing bridge.

This also falsifies the long-standing "moat = cross-repo attestation" framing
(see `memory/science-graph-positioning-2026-05.md`, corrected alongside this decision).

**Resurrection trigger (narrow, cheap):** only if a *real* cross-repo contradiction is ever
observed in practice. Even then the path is a hook at the **bridge sync boundary** (which
already holds the genomics-finding→phenome-entity mapping) that emits a single cross-repo
`claim_relation` — the substrate already supports multi-party namespaced endpoints, so no
schema work is pre-needed. NOT the embedding/retrieval/adjudication stack.

## Rejected
- Continuous Gemini-Embedding-2 shared-space sync service — redundant with the bridge;
  standing maintenance liability for N=1.
- Retrieval/adjudication apparatus to discover cross-repo overlap — the bridge curates the
  exact overlap surface already.
