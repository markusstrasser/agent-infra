---
title: Knowledge Infrastructure — Next Abstractions (Frontier Delta, May 2026)
date: 2026-05-27
tags: knowledge-substrate, cross-project, outbox, entity-resolution, provenance, frontier-delta
status: active
---

# Knowledge Infrastructure — Next Abstractions

Frontier-delta sweep on top of `2026-05-15-cross-project-knowledge-infra-dossier.md`, `epistemic-architecture-v3.md`, `knowledge-accrual-architecture.md`, `knowledge-representation-paradigms.md`, `scientific-substrate-target-architecture.md`, and the substrate-v2 decision (2026-05-26). Goal: find what's NEW since the prior sweep, what we MISSED, and where the 3-repo (intel × phenome × genomics + corpus) stack should grow next — without re-deriving what those memos already say.

## Executive Summary (200 words)

We're well within the mainstream on the architecture we just shipped: transactional outbox + per-repo natural emission + filesystem-as-federation is the boring-correct pattern in 2026, validated by the Zapier-class production write-ups and the May-2026 Debezium-vs-polling tradeoff posts. **Nothing in the frontier suggests we should rip out substrate-v2.** The four genuine deltas worth acting on are: (1) the intel UUID-vs-corpus-slug problem maps cleanly onto the well-studied **sameAs / identity-link** problem — answer is a dedicated bidirectional **crosswalk table inside corpus**, owned by corpus, not a sameAs RDF assertion (sameAs survey N=swj2430 confirms RDF semantics overpromise here); (2) **PROV-AGENT** (ORNL, arXiv:2508.02866) is the first credible AI-agent extension of W3C PROV — our annotation shape (source_id + scope + agent + output_uri + hash + idempotency_key) is already isomorphic to PROV-Activity, we should adopt the vocabulary names; (3) **bitemporal columns inside the corpus annotations table** are cheap to add now and expensive to retrofit (XTDB/Datomic confirmation); (4) outbox-at-scale post-mortems say the failure modes start at 5K events/sec — we are 4 orders of magnitude below that, so polling-drain stays optimal. **Don't** adopt CDC, CRDTs, RO-Crate, full PROV-O graphs, or a federated query layer at our scale.

---

## Axis 1 — Cross-Repo Knowledge Graph Patterns (2025-2026)

### What's NEW since prior sweep

**Frontier convergence on "event sourcing + materialized projections, NOT distributed graph DB".** Three independent signals:

- **ESAA — Event Sourcing for Autonomous Agents in LLM-Based SWE** (arXiv:2602.23193, Feb 2026). Treats agent steps as immutable events, derives current state via projection. Same shape as our intel `replay.py` — confirms intel got it right structurally, doesn't suggest a different pattern.
- **PROV-AGENT** (arXiv:2508.02866, ORNL/Flowcept). Cross-system agent provenance unified in a *single* PROV graph via instrumentation hooks. They explicitly punt on cross-system identity resolution (rely on orchestrator-side identity). This is the SAME punt we've been making — and it's industry-standard.
- **Springdrift / ElephantBroker / Graph-Native Cognitive Memory** (arXiv:2604.04660, 2603.25097, 2603.17244 — all Apr-May 2026). All converge on: append-only event log + projection + belief-revision overlay. None propose a distributed graph DB. None propose CRDTs for the knowledge layer (CRDTs appear only in the *memory* / conversational layer — see HackerNoon 2026-05-24 on MCP+CRDT, scoped to chat memory).

### What we MISSED

**Materialized projections are first-class in the new wave; we conflate "DuckDB tables" with "projections".** Genomics's `claim_verdicts`, phenome's `cert_event` derivation, intel's theses materialization are all PROJECTIONS over event streams in the CQRS sense. Calling them that out loud unlocks two things: (a) blowing one away and rebuilding from events is a debugging tool, not a migration; (b) adding new projection shapes (e.g., a "verdicts per agent" view across all three repos) is cheap if we treat corpus annotations.jsonl as the event log of record.

### For our 3-repo scope

- **WORTH:** Document explicitly that corpus `annotations.jsonl` is the cross-repo event log, and per-repo DBs are projections. Add a `decisions/` entry naming this — it's a vocabulary shift that costs ~50 lines and pays off the next time we hit a "should this live in corpus or in repo X" debate.
- **NOT WORTH:** Building a federated query layer, distributed graph DB, or shared materialized-view service. Below the scale threshold by 3-4 orders of magnitude (see Axis 3).

---

## Axis 2 — Source-Identity Alignment (the intel UUID problem)

### What's NEW

The **sameAs Problem survey** (Raad et al., Semantic Web Journal, swj2430) classifies the practical universe of cross-system identity into four buckets:

1. **Same real-world referent** (a person, a paper) — true `owl:sameAs`
2. **Same context-dependent referent** ("Paris" the city vs. "Paris" the metaphor)
3. **Related but not identical** (an FRBR Work vs. its Manifestation — a DOI usually identifies a Manifestation, intel's UUID usually identifies an item-level Filing)
4. **Crosswalk record** (this row in system A corresponds to this row in system B, no philosophical claim)

**The empirical finding from the linked-data literature**: misuse of `owl:sameAs` (using it for buckets 2-4) is the single biggest data-quality problem in cross-dataset linking. The frontier moved from "use sameAs" to **"use a typed identity link with named provenance"** (Schema.org now has `sameAs`, `subjectOf`, `mainEntityOfPage`, `isPartOf`, `isBasedOn` — pick the one that actually matches).

**PROV-AGENT's punt is informative**: they don't solve cross-system identity. They make the activity provenance graph queryable per-system and rely on the orchestrator to pass identity. For our scale, this is the right tradeoff.

### What we MISSED

We were one inch from inventing a "synthesize a fake corpus slug" workaround in intel — Phase 4 plan called it out. The sameAs literature says **synthetic IDs are the worst option**: they create a third identity that propagates everywhere and is impossible to retract. We correctly STOPPED. Bank that as a confirmed-correct decision.

**The actual answer is bucket 4 (crosswalk record):** a `source_identity_crosswalk` table inside corpus with columns `(repo, repo_local_id, corpus_source_id, link_type, confidence, asserted_by, asserted_at)`. Intel UUIDs that DO map to a DOI get a row; UUIDs that don't, just don't emit to corpus (they stay intel-local). This is exactly what OntoDup (MDPI 2026-03-26) recommends for scholarly KG dedup at small-to-medium scale.

### Three concrete options ranked by maintenance burden

| Option | Where it lives | Maintenance | Who does this |
|---|---|---|---|
| **A. Crosswalk table in corpus** (`source_identity_crosswalk`) | corpus, populated by repos via opt-in INSERT | LOW — append-only, no semantics, drop and rebuild any time | OntoDup, ORCID's external-id table, CrossRef's relationship API |
| **B. Repo-local identity-overlay** (intel adds `corpus_source_id` nullable column to `filings_and_datasets`) | intel | MEDIUM — schema change in each repo that wants to participate; harder to do "who else has this DOI?" queries | Datomic-style attribute extension; modern data-vault pattern |
| **C. owl:sameAs / RDF graph** | new service | HIGH — needs reasoning, canonicalization (W3C RDF Dataset Canonicalization, REC May 2024), and proper sameAs semantics most teams misuse | Wikidata, DBpedia — and they pay a full-time team |

**Recommended for our scale: Option A.** A `source_identity_crosswalk` table inside `~/Projects/corpus/` graph.duckdb. Intel's `MutationGateway` (when we build one) consults the crosswalk: if the UUID resolves to a corpus slug, enqueue annotation with the slug; if not, skip emission. The crosswalk itself is populated by a periodic intel script that promotes `filings_and_datasets.doi` → crosswalk row when present.

This unblocks Phase 4 of substrate-v2-deferred without forcing a schema-of-truth change in intel. Estimated work: ~150 lines + one migration.

---

## Axis 3 — Outbox Pattern Variants & Scale Ceilings

### What's NEW

The **scale ceilings are now well-documented** (May 2026 wave of post-mortems). Concrete numbers from production write-ups:

| Pattern | Latency | Throughput ceiling | When to switch |
|---|---|---|---|
| **Polling outbox** (us) | ~500ms p50 at 1s tick | ~5K events/sec single worker, ~10K with care | Below 5K/sec — stay here |
| **CDC (Debezium/WAL)** | 50-200ms | 20K+/sec, needs Kafka Connect | Above 20K/sec OR multi-region |
| **Sharded polling** | ~500ms | ~50K/sec total | The awkward middle (5-20K/sec) |
| **Direct CDC → agent** (no Kafka, "Event-Driven Agents", dev.to 2026-04-19) | 50ms | 5K/sec | Brand new pattern, immature |

We process **~10-100 annotations/day**. We are 4-5 orders of magnitude below where polling breaks. **The Zapier post (2026-03-30) explicitly says: "if you don't have an existing Kafka cluster, the 6-month setup detour is bigger than your event-volume problem."**

### Failure modes other teams hit (worth a peek)

1. **Cross-transaction ordering broken in CDC** — WAL ordering ≠ commit ordering. Consumers must key off aggregate ID, not log position. (We sidestep by being single-writer per repo.)
2. **WAL slot bloat when consumer lags** — disk-fills-up incident class. We don't have this (no replication slots).
3. **Schema drift between producer and consumer** — Kafka Schema Registry exists for this. We have it solved by JSONL with stable_tuple-derived idempotency keys.
4. **"Why We Replaced Debezium+Kafka"** (dev.to 2026-02-26) — the team replaced with... a polling outbox. Inverse migration is common at <10K/sec.
5. **Lock contention on the outbox table** — our 3-phase RO-fetch / unlocked-FS-emit / RW-DELETE pattern is exactly the recommended mitigation. Already shipped.

### For our 3-repo scope

- **WORTH:** Add lag/drain-time telemetry to `audit_corpus_sync.py` (already does abandoned-count; add p50/p95 drain latency, currently uninstrumented). When it crosses some threshold (define: drain latency > 10s, or abandoned > 100 in 24h), that's the trigger to revisit.
- **NOT WORTH:** Debezium, Kafka, CDC, fire-and-forget async drain, sharded outbox. All overkill until we're 4+ orders of magnitude bigger.

---

## Axis 4 — Provenance Graph Standards

### What's NEW

**PROV-AGENT** (arXiv:2508.02866, ORNL, Flowcept-based) — *the* 2025-2026 attempt to extend W3C PROV-O specifically for AI agents. Key vocabulary additions:

- `AIAgent` ⊑ `prov:Agent`
- `AIModelInvocation` ⊑ `prov:Activity`
- `Prompt`, `ResponseData`, `AIModel` as `prov:Entity`
- Integrates **MCP** (Model Context Protocol) tool definitions as first-class

**Adoption status: early.** ORNL HPC demo, no production claims. But it's the only standards-coupled vocabulary that names what we're already doing.

**W3C RDF Dataset Canonicalization** became a REC in May 2024. This is the cryptographic canonicalization standard for RDF graphs. Not relevant at our scale, but worth knowing exists if we ever publish corpus snapshots externally.

**RO-Crate** (Provenance Run Crate profile, PLOS One Sep 2024 + community update FDO 2024). Adoption real in: bioinformatics workflows (Galaxy, Nextflow, CWL), ELIXIR ecosystem, life-sci data deposits. Not adopted in: agent systems, LLM provenance, anything outside the WfMS world. **Wrong abstraction for us** — it's about packaging a workflow run as a sharable artifact, not annotating sources continuously.

### Our annotation shape mapped to PROV-AGENT

Our `annotations.jsonl` row:
```
{source_id, scope, agent, output_uri, output_hash, idempotency_key, asserted_at}
```

Maps cleanly to:
```
prov:Activity(id=ann_<hash>) {
  prov:used = source_id              // Entity
  prov:wasAssociatedWith = agent      // Agent (could be AIAgent subclass)
  prov:generated = output_uri         // Entity, content-addressed via output_hash
  prov:atTime = asserted_at
  scope, idempotency_key as custom properties
}
```

**One-for-one isomorphism, zero data migration required to start using the PROV vocabulary in documentation.** That's the right level of adoption: borrow names, don't import the stack.

### What we already have right

- Content-addressed identity (output_hash) — matches PROV `prov:Entity` with hash invariants
- Append-only — matches PROV's "facts about the past" semantics
- Idempotency keys — matches the bag-of-relations semantics (multiple equivalent assertions merge)
- Per-source file (annotations.jsonl) — matches PROV's notion of "provenance bundle"

### For our 3-repo scope

- **WORTH:** Rename annotation fields in documentation to match PROV vocab where lossless (`agent` already matches; consider `output_uri` → `generated_uri`, but not blocking). Add a comment in `corpus_core/outbox.py` linking to PROV-O Activity model. Cost: 0 to 50 lines of doc.
- **NOT WORTH:** Full PROV-O graph in DuckDB. RO-Crate export. Triple store. Any RDF serialization. We have JSONL with the right shape — RDF buys us nothing at our scale.

---

## Axis 5 — Next Abstractions Beyond Gateway + Outbox + Drain

Where does this stack typically grow next? Two genuinely new ideas worth considering, several rejected.

### WORTH considering

**(1) Bitemporal columns on annotations.** Add `valid_from` / `valid_to` alongside `asserted_at`. Cost: 2 columns, 1 migration. Value: when corpus is later asked "what did genomics believe about source X *as of the 2026-04-01 ClinVar update*?", we have the answer without a snapshot DB. Genomics already does this on verdicts (`asserted_at`, `valid_from`). Corpus doesn't. The XTDB / Datomic / Minigraf community is unanimous that bitemporal is cheap to add early and expensive to retrofit. **Recommend adding now.**

**(2) Projection re-derivation script.** A `corpus_core.replay` that drops `graph.duckdb` and rebuilds it from all `annotations.jsonl` files. Cost: ~100 lines. Value: corruption recovery, schema migrations, debugging "why does graph.duckdb show X when annotations don't?". Intel already has the pattern (`replay.py`). Genomics doesn't have it on the corpus side. **Recommend building when needed, not preemptively.**

### NOT worth adding

- **Subscriptions / agent-side push notifications** — no consumer demand. Zero invocations of cross-repo `corpus_lookup` MCP per the forensics memo. Build the subscription when there's a subscriber.
- **Materialized views on corpus** — current `graph.duckdb` index IS the materialized view. Don't add a second.
- **Trigger-driven re-derivation** — at our throughput, manual replay is fine.
- **Cross-repo locking** — premature. Single-writer-per-repo plus per-source append-only file naturally serializes; no actual concurrent-write conflict has been observed.
- **Conflict resolution protocol** — two repos asserting different things about the same source IS the interesting signal we want to preserve, not resolve. The current design (both annotations land, both readable) is correct.
- **Federation server / GraphQL gateway** — see Axis 3 throughput numbers.

---

## Axis 6 — Operational Pain Points From the Wild

From May-2026 outbox post-mortems and Debezium-in-production write-ups:

| Pain point | Their cause | Are we exposed? |
|---|---|---|
| **Outbox table grows unboundedly** | Forgot to DELETE on drain success | NO — our 3-phase drain DELETEs on success |
| **Drain worker dies silently** | No deadletter, no alerting | PARTIAL — abandoned-count surfaced in audit; no alerting yet |
| **Idempotency key collision** | Hash of mutable fields | NO — we use stable_tuple; lint forbids content-derivation |
| **Schema migration on outbox table during in-flight rows** | Forgot to drain before migrating | LOW — `ensure_lifecycle_columns` is idempotent ALTER, designed for live data |
| **Duplicate emission after crash mid-drain** | Drained but didn't DELETE before crash | NO — idempotency key + UPSERT downstream makes duplicates harmless |
| **Cross-transaction ordering breaks consumers** | WAL ≠ commit order in CDC | N/A — we're polling, not CDC |
| **Lock contention spikes** | Long drain held the writer lock | NO — 3-phase RO-fetch / unlocked-FS-emit / RW-DELETE explicitly fixes this |
| **"Drain works in dev, breaks in prod under concurrent writers"** | Producer & drainer racing on row visibility | PARTIAL — single-writer-per-repo plus shared-connection-across-threads in phenome regression-tested under 4-worker race; gateway pattern correct |
| **Annotation drift between domain DB and corpus** | Drain succeeded, DB write failed (or vice versa) | NO post-2026-05-26 backfill — but the *class* of drift can recur if gateway is bypassed; lint forbids the bypass |

**The one we should pre-empt:** *Alerting on abandoned-row count*. Currently audit reports it; nothing alerts. Pattern from Zapier post: "we found out about a drain outage 5 days later when a downstream system complained." Cheap fix: stop-hook checks `audit_corpus_sync` abandoned-count post-session and surfaces if >threshold.

---

## What We ALREADY Have Right (Don't Churn)

1. **Filesystem-as-federation** (per-source `annotations.jsonl`). Mainstream-correct. Don't rebuild as a service.
2. **Content-addressed source identity** (`doi_*`, `pmid_*`, `db_*`, `sha_*` slug namespace). Matches PROV `prov:Entity` semantics and is the only sensible cross-repo lookup key.
3. **Transactional outbox + post-commit drain.** Standard pattern. 5K/sec ceiling — we are at 100/day. No reason to switch.
4. **Per-repo natural emission** (verdict in genomics, cert_event in phenome). Not forcing a fake common ontology was the right call (2026-05-26 decision).
5. **Single sole writer per scope** (`corpus_core.outbox.drain`). Audit + drain unified.
6. **Lint enforcement** (`lint_no_direct_corpus_writes.py`) preventing gateway bypass.
7. **Bitemporal in domain DBs** (genomics verdicts have asserted_at + valid_from). Wasn't in corpus annotations — that's the only retrofit recommendation in this memo.
8. **Three-value logic** on verdicts (VALID/INVALID/UNKNOWN). Industry-converged shape, also adopted independently by PROV-AGENT's prelim experiments.
9. **Append-only as the substrate principle.** All three repos converged here independently — confirms by the rule of independent rediscovery this is structural, not an artifact of taste.
10. **Per-repo MCP read surface, no cross-repo MCP-to-MCP federation.** Avoids the trap that broke the `record_verdict` ritual.

---

## Concrete Recommendation Stack (ranked by ROI)

| # | Item | Effort | Maintenance | Trigger |
|---|---|---|---|---|
| 1 | Add `valid_from` / `valid_to` columns to corpus annotations table | 1 migration, ~20 lines | LOW — backfill `valid_from = asserted_at` | Adopt now (cheap to add, expensive to retrofit) |
| 2 | Build `source_identity_crosswalk` table in corpus | 1 migration + intel-side promoter script, ~150 lines | LOW — append-only crosswalk | Unblocks intel Phase 4 |
| 3 | Add drain-latency + abandoned-count alerting to stop hook | ~30 lines | LOW | One real "drain hung" surprise away from being load-bearing |
| 4 | Rename `decisions/` framing: "corpus annotations are the event log, repo DBs are projections (CQRS sense)" | 1 short decision file | NONE | Vocabulary unlock; do once |
| 5 | Document PROV-AGENT vocabulary mapping in `corpus_core/outbox.py` | ~10 lines of docstring | NONE | Future-self orientation |
| 6 | Build `corpus_core.replay` script | ~100 lines | LOW | Build when first corruption / migration forces it |
| 7 | Anything from Axes 1-6 in the "NOT WORTH" lists | — | — | Defer indefinitely |

---

## Source Grade Footnotes

- D2 grade: dev.to / Medium production write-ups (May 2026 outbox-at-scale wave) — multiple independent sources converging on the same scale numbers
- C2 grade: arXiv preprints PROV-AGENT (2508.02866), ESAA (2602.23193), ElephantBroker (2603.25097), Springdrift (2604.04660) — recent, not yet peer-reviewed at the time of writing
- A1 grade: W3C PROV-O recommendation (stable since 2013); W3C RDF Dataset Canonicalization REC (May 2024)
- C3 grade: Raad et al. sameAs survey (Semantic Web Journal swj2430) — full PDF couldn't be parsed; conclusions cross-checked against OntoDup (MDPI 2026-03-26) and Schema.org documentation
- B2 grade: Zapier outbox-at-scale post (2026-03-30) — engineering blog, named author, concrete numbers
- Internal: dossier 2026-05-15, substrate-v2 decision 2026-05-26, substrate-v2-deferred update 2026-05-27, substrate-usage-forensics 2026-05-26

## Tools used

- Exa advanced search (5 queries, ~10 hits each)
- WebFetch on Zapier (503 — couldn't read; numbers from dev.to crosspost), dev.to outbox-vs-CDC piece, arXiv 2508.02866 PROV-AGENT
- Perplexity API: quota exhausted mid-session (known failure mode); fell back to Exa
- sameAs survey PDF: WebFetch failed to parse PDF binary; backed by OntoDup confirmation

<!-- knowledge-index
generated: 2026-05-27T09:20:44Z
hash: 60252e70d0d6

index:title: Knowledge Infrastructure — Next Abstractions (Frontier Delta, May 2026)
index:status: active
index:tags: knowledge-substrate, cross-project, outbox, entity-resolution, provenance, frontier-delta

end-knowledge-index -->
