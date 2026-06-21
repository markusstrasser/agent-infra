# The Substrate Knowledge Graph — Evolution Across Repos (2023 → 2026)

> **One system, six names, four eras, ~a dozen implementations (several retired).**
> Traced 2026-06-21 from git history + on-disk schema across the full lineage:
> `savant → synth → synthoric` (web) → `selve/phenome` (Python trunk) →
> `genomics / intel / personal` (forks) → `substrate / corpus` (unification).
>
> Provenance: synthesized from 4 context-isolated sub-traces + parent-gathered git backbone.
> Backing memos: `.scratch/substrate-trace/{A-web-ancestry, B-selve-phenome, C-genomics-intel-personal, D-unification}.md`.
> Builds on (does not duplicate) phenome's `.claude/research/2026-06-17-substrate-unification/` and
> agent-infra `decisions/2026-0{3,5,6}-*` cross-attestation series.

---

## TL;DR — the two through-lines

The same **machinery** has persisted since 2024 while its **subject** changed
edtech → genomics, and the system was rebuilt repeatedly until two laws were learned:

1. **Verifier-conditioned shape.** Each repo's substrate is exactly as heavy as its
   domain is checkable. genomics (measured pipeline output, *has* a verifier) → a deep
   bitemporal event-log behind a write-lock gateway. intel (human conjectures, *falsifiable*)
   → a rebuildable graph with first-class contradictions. personal (*unverifiable* context)
   → **no database at all**. This is the constitution's verifier-conditioned-autonomy
   principle, discovered empirically in the data layer.

2. **The contract must live in the code path, not in agent ritual.** Every attempt to make
   agents *remember* to record/attest knowledge got ~0 adoption and was retired (the shared-
   substrate MCP, the 2-call `record_verdict→corpus_attest` ritual, the `corpus_attest` tool).
   Only when attestation moved *inside the mutation-gateway transaction* (a transactional
   outbox) did it stick. This is why the substrate was "implemented a bunch of times."

The constant machinery: **typed-node knowledge graph · evidence-weighted beliefs
(value + confidence) · dereferenceable weighted provenance · append-only events with
derived projections · LLM-driven inference · generation gated on the maintained graph.**

---

## Master lineage (ASCII)

```
 SUBSTRATE KNOWLEDGE GRAPH — LINEAGE 2023→2026               (single author: Markus Strasser / "Synthoria")

 ERA 0 · WEB LEARNING-KG          ERA 1 · PY TRUNK            ERA 2 · FORK & DIVERGE          ERA 3 · UNIFY
 TypeScript · Convex              "selve" → phenome           per-repo, verifier-conditioned  shared L2 packages
 ───────────────────────         ─────────────────────       ────────────────────────────   ──────────────────

 savant      2023-06 ─┐  Next13                                ┌── genomics 2026-02 ───────┐
 Chrome-ext AI chat   │  Zustand+graphlib                      │  bitemporal DuckDB log     │
 inferKnowledge()     │  "idea before schema"                  │  MutationGateway+lock      │
                      ▼                                         │  +2-phase commit  ★REF     │
 synth       2024-05 ─┐  Next.js+Convex                        │                            │   ┌──────────────────┐
 "KG tracking         │  zod Inference{                        ├── intel    2026-02 ───────┤   │  substrate/ repo │
  components +        │   mastery, confidence,    selve→       │  markdown-canonical,       │   │  2026-05-11      │
  user mastery"       │   sources[weight]}        phenome      │  DB-rebuildable graph,     │──▶│  corpus-core ▒   │
                      ▼  "interactions are        FORK ──────▶ │  contradiction_pairs       │pkg│  claimcore   ▒   │
 synthoric   2024-06 ─┐  permanent; only          (late Feb)   │  attests CONTRADICTIONS    │up │  claim-reasoning │
 Svelte5 rewrite      │  knowledge updates"                    │                            │   │  genomics-read   │
 knowledgeComponents  │         │                              ├── personal 2026-06-10 ────┤   │  clinical-profile│
 + userInsights       │         │ 2026-04-12 pkg rename        │  NO DB. markdown dossiers  │   │  evalcore        │
                      ▼         │ 2026-04-16 ★CLAIM STORE      │  + embedding caches.       │   │  plan-core       │
   ~17-month                    │   = the KG is BORN           │  NO gateway/attestation    │   └────────┬─────────┘
   DORMANCY                     ▼   (search → graph)           └─────────────┬──────────────┘            │
   2024-08→2026-01         ┌─────────┐                                       │ corpus_core.outbox        │
        ┊                  │ phenome │◀── migrates onto claimcore ───────────┤ (the ONE shared           ▼
   [concept revived        │ = trunk │    2026-06-07 "atomic flip"           │  extraction)         ┌──────────┐
    in Python, new         │  + KG   │                                       └─────────────────────│  corpus/ │
    subject = genome]      └─────────┘    genomics + intel emit ↑ ;  personal abstains              │ 2026-06  │
                                                                                                    │ event-   │
                                                                                                    │ log/data │
                                                                                                    └──────────┘

 ════ RETIRED / NEVER-BUILT (the "implemented many times" tax) ═══════════════════════════════════════════════
   v0  shared-substrate MCP            2026-03-17 → RETIRED 03-24   (0 organic adoption in 7 days)
   v1  2-call ritual record_verdict    2026-05-11 → SUPERSEDED 05-26 (0 invocations / 260+ writes bypassed it)
       └ record_verdict stubs ×5 deleted 05-26 · corpus_attest MCP tool deleted 05-31 (last dual-write door)
   --  cross-repo contradiction layer  2026-06-01  NOT BUILT (the live bridge already owns cross-repo flow)
   --  decay-weighted RSI salience     2026-06-20  NOT BUILT (write-once data; co-access doesn't exist)
   ▒ = current home of the claim/source floor (extracted from phenome 2026-06-10; "Seam B")
```

---

## Naming & rename reference (every alias, dated)

| Name | Era | What it actually was | Born | Note |
|------|-----|----------------------|------|------|
| **savant** | 0 | Chrome-extension AI chat; Zustand + `graphlib` directed graph + LLM `inferKnowledge/Skills/Interests` stubs | 2023-06-08 | "the idea before the schema" |
| **synth** | 0 | Next.js STEM-learning platform, Convex; **brand "Synthoria" already in `layout.tsx`** | 2024-05-01 | first real KG schema (zod) |
| **synthoric** | 0 | Svelte 5 rewrite of synth (literal `copy files from NextJS project`) | 2024-06-24 | KG promoted to first-class tables |
| **Synthoria** | all | the **brand/company** (synthoria.bio), not a repo | 2024 (name) / 2026-04-06 (site) | edtech → genomics pivot |
| **"refs knowledge manifold"** | 1 | the repo's *first commit message*; a personal-knowledge **search** tool (bookmarks CSV + embeddings + FTS5) | 2026-01-10 | NOT yet a claim graph |
| **selve** | 1 | the Python **package** name inside that repo | 2026-02-27 | search-first |
| **phenome** | 1+ | the repo + package after rename; the **KG trunk** | pkg 2026-04-12 / repo-dir ~2026-06-17 | two distinct renames |
| **genomics** | 2 | fork — genomic mutation/verdict substrate | ~2026-02-28 | extracted from selve |
| **intel** | 2 | fork — investing/entity thesis & contradiction graph | ~2026-02 | |
| **personal** | 2 | fork — personal context dossiers (no DB) | split 2026-06-10 | history dates inherited to 02-26 |
| **substrate** | 3 | repo of shared L2 packages (corpus-core, claimcore, …) | 2026-05-11 | "owns reusable packages" |
| **corpus** | 3 | the cross-repo **event-log / data store** | 2026-06-01 | `annotations.jsonl` = the moat |
| **claimcore** | 3 | the extracted claim **floor**; phenome's `store.py` is now a thin profile over it | 2026-06-07 | "one substrate, two projections" |
| **_synthoria-donor** | — | **parked** product fork of phenome (donor data-room MCP); NOT an ancestor | extracted 2026-06-10 | matured Python form |

Two renames people conflate — keep them apart:
- **claimcore package migration** (2026-06-07 → 12): phenome's claim logic moves to the shared `claimcore` floor.
- **selve → phenome rename**, itself in two steps: **package** `src/selve/`→`src/phenome/` (2026-04-12, `0f2f0009`, 96 import sites) and **repo-directory** `~/Projects/selve`→`~/Projects/phenome` (~2026-06-17, the June `*-repoint` cleanup commits).

---

## Era 0 — Web learning-KG (2023 → 2024)

The original problem was **adaptive STEM learning**: model a learner's knowledge as a
graph and generate content against it. The KG was reinvented three times in TypeScript,
each more first-class than the last:

```
savant (2023)        synth (2024)                       synthoric (2024)
─────────────        ────────────                       ────────────────
client Zustand:      Convex tables:                     Convex tables (KG = first-class):
 interactions         interactions  (permanent history)   knowledgeComponents   ← "knowledge atoms"
 inferences           inferences                           userInsights          ← renamed inferences,
 contents             history                                                       w/ resolved source edges
+ graphlib graph                                           sequences → interactions
+ LLM infer stubs    zod Inference schema:
                      { type ∈ knowledge|skill|misconception,
                        assumedMasteryLevel : 0..1,        ← the BELIEF VALUE
                        systemConfidence    : 0..1,        ← the CONFIDENCE
                        sources : [{id, whyRelevant, weight:0..1}] }   ← WEIGHTED PROVENANCE
                     README: "Knowledge graph tracking individual components and user mastery"
                     invariant: "interactions are permanent history! Only knowledge is updated"
```

Everything that matters about the modern substrate is already here in 2024, just pointed
at learners instead of genomes: a **typed knowledge-node graph maintained by LLM inference**,
**belief = (value, confidence)** with **weighted dereferenceable provenance**, and
**append-only events vs. mutable/derived knowledge**.

---

## Era 1 — Python trunk: search manifold → claim graph (2026-01 → 04)

The Python repo did **not** start as a knowledge graph. Its first incarnation
("refs knowledge manifold", 2026-01-10) was a **personal-knowledge search tool** — a flat
`bookmarks.csv` (5,560 rows of ChatGPT/Twitter/Logseq/Git/Raycast/podcast refs), a unified
embedding space (the "manifold"), and FTS5. "refs" = bookmarks; provenance was a ranking field.

```
 2026-01  refs manifold      bookmarks.csv(5560) + embeddings + FTS5          [search, no claims]
 2026-02  selve package      cli/scripts → pkg: FTS5 + entity-elevation + provenance   [still search]
 2026-04-12  pkg rename       src/selve/ → src/phenome/  (96 import sites)
 2026-04-16  ★ PROSE-FIRST CLAIM STORE   first CREATE TABLE assertions/evidence;
             = the KG is BORN            2,326 claims ingested; 7 claim MCP tools
 2026-04-17  v3 event-kernel  → 2026-04-18 v4 cut-direct-state
 2026-06-09  verify-not-synthesize doctrine (ADR 0002): identity flips search-tool → VERIFICATION substrate
```

The pivot on **2026-04-16** is the true birth of the Substrate Knowledge Graph as a *graph*:
the search index became a **claim ledger**. Current floor (now the shared `claimcore`,
DuckDB, ~63 tables / 1815 lines) keeps the belief/evidence/provenance shape from Era 0 and
adds verification and admissibility:

```
claimcore spine (DuckDB):
  claim_events            ← append-only kernel; assertions is a PROJECTION of this  (Era-0 invariant!)
  assertions              ← the belief node      (identity v4 = uuid5(predicate + slots))
  assertion_entities · assertion_slot_logic                       (n-ary subject binding)
  assertion_identities · corroboration_key · contradiction_key
  assertion_evidence · evidence_spans                             (quote-containment provenance)
  grounding_input_manifest · grounding_verdict                    (status-envelope CHECK)
  evidence_verification · upstream_checks
  clinical_grade · framework_contracts                            (CPIC/ClinVar/GenCC grades)
  assertion_admissibility (the MEET) · admissibility_gate_requirements
  extraction_runs · assertion_provenance                          (model, prompt-hash, source-hash)
```

phenome's write path is **function-based** (`mutate.py`: `record_action`,
`resolve_contradiction`, `record_upstream_check`; `attest.py: attest_addition`) — *not* the
class-based `MutationGateway` (that pattern is genomics'). It stores biomedical +
pharmacogenomic claims (ClinVar/GenCC/CPIC) ⊕ literature-extracted prose ⊕ PHI-tiered
personal-genome observations + 198K+ phenotype entries.

---

## Era 2 — Fork & diverge (2026-02 → present): verifier-conditioned substrates

Three repos forked the trunk and built **deliberately different** substrates. The axis of
divergence is **how checkable the domain is** — not accident:

```
                  genomics                    intel                       personal
                  (measured output)           (human conjecture)          (unverifiable context)
                  HAS a verifier              FALSIFIABLE                  NO verifier
 ───────────────  ─────────────────────────  ──────────────────────────  ─────────────────────────
 store            bitemporal DuckDB           markdown-canonical,         NONE
                  event-log (INSERT-only)     DuckDB rebuildable          (markdown dossiers +
                  asserted_at (txn-time) +    from markdown               JSON embedding caches)
                  valid_from (world-time)
 tables           assertions, claim_verdicts, assertions(UUID5),         — (zero CREATE TABLE)
                  source_observations,        assertion_relation_edges,
                  evidence_bindings           contradiction_pairs,
                  (2026-05-09 migration)      prediction/portfolio_events
 write path       MutationGateway +           rebuild → validate →        direct file write
                  writer.lock + 2-phase       atomic-swap (NO lock)
                  DB+FS commit
 attests          VERDICTS                    CONTRADICTIONS              nothing
                  in-process self-drain       pre-resolved crosswalk,     (corpus_core not even a dep)
                  after lock release          async drain only
 role             ★ substrate-v2 REF IMPL     thesis/contradiction graph  personal memory
```

**Shared kernel they re-converge on:** `corpus_core` 0.2.0 — a domain-agnostic graph store
with a **closed** relation enum (`support / extend / qualify / refute / background`),
round-trip home pointers (`home_verdict_id`→genomics, `home_pair_id`→phenome), and a
transparent linear `support_balance` that is **explicitly not P(true)**. genomics and intel
both emit into it; personal abstains by design.

> **By-design vs accidental duplication:** the `corpus_core` outbox is the one *genuinely
> shared* extraction. The predicate-registry shape was independently reimplemented **3×** and
> left duplicated — correctly, because it is not a correctness invariant (cf. the
> "shared invariant has ONE definition" rule: this isn't one).

---

## Era 3 — Unify (2026-05 → present): shared packages + corpus event-log

The recurring extractions finally landed in two repos:

**`substrate/`** (uv workspace, consumed by editable path; 8 packages on disk):

| Package | Owns | Key model |
|---------|------|-----------|
| `corpus-core` | canonical source store + **sole annotation writer** | `papers` / `edges` / `annotations`; ids `doi_/pmid_/sha_` |
| `claimcore` | the biomedical claim **floor / spine** ("evidence over an *injected* corpus") | `assertions` + `evidence_spans` + `documents` + `extraction_runs` + `entities` + `predicates` |
| `claim-reasoning` | defeasible reasoning over claimcore, **firewalled** in its own schema | `defeasible_rule` / `generated_defeater` / `challenge` |
| `genomics-read` | read-only genomic resolver | `NeutralGenomicsFact(extra="forbid")`, directive-redacted |
| `clinical-profile` | clinical axis over claimcore | injected subject |
| `corpus-testing` | pytest fixtures | — |
| `evalcore` | shared eval primitives | stats / blind-judge / leak-guard |
| `plan-core` | generic plan-doc engine | ex-genomics `planctl` |

**`corpus/`** (own git, 2026-06-01) — the **event-log**, not a service:
```
 annotations.jsonl  (per source)   = the moat — "every correction is a commit"
 graph.duckdb                       = rederivable PROJECTION
 ledger.duckdb                      = full materialized claimcore schema
 _science_kg/                       = scratch/staging for an overnight lit-ingest loop (63/15,630 = 0.4%),
                                      NOT a separate KG store
```
Repos are **hybrid**, not pure CQRS: each holds materialized slices + local-authoritative
state; **no repo rebuilds from corpus alone**.

**Identity boundary (decision 2026-06-14):** the 2026-06-10 extraction moved only reusable
*package code* to `substrate`; phenome keeps the claim-graph **data** + verifier +
enrichment. Two co-core identities, split on the **verify-vs-synthesize** axis (not
personal-vs-general).

---

## The cross-attestation arc — the same thing built ~5 times

This is the clearest illustration of "implemented a bunch of times." The *goal* never
changed (a repo records a verdict → it shows up as an attested annotation in the shared
corpus). Only the *layer* changed, until it worked:

```
v0  shared-substrate MCP        2026-03-17  RETIRED 03-24   agents won't call a separate store
                                                            (4 reads / 60 writes / 7 days)
v1  2-call agent RITUAL         2026-05-11  SUPERSEDED      record_verdict() then corpus_attest():
                                            05-26           0 invocations in 9mo, 260+ writes bypassed
                                                            → the ritual was at the WRONG LAYER
    record_verdict stubs ×5     deleted 05-26
    corpus_attest MCP tool      deleted 05-31              (the last dual-write backdoor closed)
v2  TRANSACTIONAL OUTBOX        2026-05-26  CURRENT         attestation INSIDE the gateway txn:
                                                            pending_corpus_attestations → drains to
                                                            sole corpus_core.annotate writer.
                                                            0 agent discipline. audit_corpus_sync.py = net
```

**Lesson (the project's spine):** *agent-orchestrated rituals over a database get ~0 adoption
— the contract must live in the code path.* This is the local instance of the global
"architecture over instructions" principle, paid for in five build-then-retire cycles.

---

## What carried forward — continuity proof (independently corroborated by 2 traces)

| 2024 (synth/synthoric, TS/Convex) | 2026 (phenome/claimcore, Py/DuckDB) |
|---|---|
| zod `Inference{assumedMasteryLevel, systemConfidence, sources[{weight}]}` | `assertions{confidence}` + `assertion_evidence` + `evidence_spans` |
| "interactions are permanent history! Only knowledge is updated" | `claim_events` append-only; `assertions` = projection |
| `knowledgeComponents` (knowledge atoms) | `assertions` / `entities` (claim nodes) |
| `sources:[{id, whyRelevant, weight}]` | `assertion_provenance{created_by, model_name, prompt_hash, source_file_hash}` |
| LLM `inferKnowledge/Skills/Interests` | LLM extraction_runs → claim ingest |
| adaptive content generation gated on the KG | answers gated on the verification substrate |

The continuity link (web → Python) is corroborated structurally: the parked
`_synthoria-donor` (a Python phenome fork) carries the *same* `assertions` /
`assertion_evidence` / `evidence_spans` tables that claimcore defines — the schema is the
fingerprint.

---

## Data-model evolution at a glance

```
 ERA 0  MASTERY GRAPH (TS/Convex)   nodes = knowledgeComponents · belief = (mastery, confidence)
                                    edges = weighted sources · events = permanent interactions
        ────────────────────────── subject: the LEARNER ──────────────────────────────────────
 ERA 1  SEARCH MANIFOLD (Py)        bookmarks.csv + embeddings + FTS5         [NOT a graph]
            │ 2026-04-16 pivot
            ▼
        CLAIM LEDGER (Py/DuckDB)    claim_events(append-only) → assertions(projection)
                                    + evidence_spans + grounding_verdict + admissibility
        ────────────────────────── subject: GENOME / PHENOTYPE / LITERATURE ──────────────────
 ERA 2  PER-REPO (verifier-cond.)   genomics: bitemporal verdict log | intel: contradiction graph
                                    personal: no DB | shared: corpus_core.claim_relations
 ERA 3  SHARED FLOOR                claimcore (the ledger, extracted) + corpus (the event-log)
                                    repos = hybrid materialized slices, attest via gateway outbox
```

---

## Source evidence / where to look

| Claim | Evidence |
|-------|----------|
| Web-era schemas | `_ancestry/{savant,synth,synthoric}`; `synth/src/zodSchemas/index.js`, `synthoric` Convex tables |
| trunk origin = search tool | phenome `9f14be3e` (2026-01-10); bookmarks CSV |
| KG born 2026-04-16 | phenome prose-first claim-store plan + first `CREATE TABLE assertions` |
| claimcore floor | `substrate/packages/claimcore/schema.sql` (~63 tables); phenome `store.py` (thin profile) |
| genomics gateway | `genomics/scripts/knowledge/mutation_gateway.py:210`, `:482`; `migrations/2026-05-09-knowledge-tables.sql` |
| intel rebuild path | `intel/tools/theses/schema.sql`, `rebuild.py:477`, `corpus_attestation.py:55` |
| personal = no DB | `personal/` (markdown dossiers + `indexed/*.json`; no CREATE TABLE) |
| corpus event-log | `corpus/` `annotations.jsonl`, `graph.duckdb`, `ledger.duckdb` |
| attestation v1→v2 | agent-infra `decisions/2026-05-11-…`, `2026-05-26-cross-attestation-substrate-v2.md` |
| identity boundary | agent-infra `decisions/2026-06-14-phenome-substrate-identity-boundary.md` |
| retired attempts | agent-infra `decisions/2026-03-17-shared-knowledge-substrate.md`; `.claude/rules/vetoed-decisions.md` |

Full per-repo detail: `.scratch/substrate-trace/{A,B,C,D}-*.md` + `00-backbone-timeline.md`.
```
```
