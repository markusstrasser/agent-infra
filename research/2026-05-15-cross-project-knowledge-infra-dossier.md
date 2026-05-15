---
title: Cross-Project Knowledge Infrastructure Dossier — intel × phenome × genomics × agent-infra (+ evals)
date: 2026-05-15
tags: knowledge-substrate, cross-project, kernel-synthesis, corpus, attestation
status: active
---

# Cross-Project Knowledge Infrastructure — The Dossier

Scope: inventory of every knowledge-infra surface across `intel`, `phenome`, `genomics`, and `agent-infra`, plus an explicit verdict on whether `evals` belongs in the same world. Goal: identify the **stable kernel** that recurred independently in three domains, locate the **load-bearing differences**, and surface what's already shipped vs. in-flight.

Source dossiers (per-project, exhaustive — read for verbatim schemas):
- `/tmp/intel-knowledge-dossier.md` (~500 lines)
- `/tmp/phenome-knowledge-dossier.md` (~700 lines)
- `/tmp/genomics-knowledge-dossier.md` (~870 lines)
- `/tmp/agent-infra-knowledge-dossier.md` (~785 lines)
- `/tmp/evals-knowledge-dossier.md` (~300 lines)

Anchor decisions:
- `decisions/2026-03-17-shared-knowledge-substrate.md` — precursor (domain profiles over unified stack)
- `decisions/2026-05-11-cross-attestation-substrate.md` — current substrate v1 (multi-phase, mostly shipped)
- `~/Projects/genomics/decisions/2026-05-09-scientific-claim-governance-as-general-substrate.md` — substrate kernel recognized as domain-agnostic, but **not yet extracted**
- `~/Projects/agent-infra/research/scientific-substrate-target-architecture.md` — Layer 1–4 model

---

## TL;DR — The kernel exists. It was discovered three times independently. It is not yet a library.

Three production systems (intel, phenome, genomics) converged on the **same eight primitives** without sharing code. Agent-infra now hosts the **fourth primitive** (the canonical source store) that lets the three federate via filesystem semantics rather than a federation server. Evals is in the same MCP ecosystem but **does not participate** in the knowledge substrate — it's a benchmark harness whose only knowledge-infra hook (`corpus_attest`) is declared in CLAUDE.md and explicitly deferred as non-blocking. Three repos use the substrate; evals lives next to it.

### The eight-primitive kernel (independently rediscovered)

| # | Primitive | intel | phenome | genomics | Notes |
|---|-----------|-------|---------|----------|-------|
| 1 | **Assertion / Claim** — predicate + slots + identity | `assertions(predicate, slots JSON, content_hash UUID5)` | `assertions(predicate_family, predicate, slots, identity_version)` | `assertions(predicate_id, slot_schema_hash)` + `claim_id` (curator-stable) | Different identity rule (UUID5 vs content-hash vs curator-stable name), same shape |
| 2 | **Evidence / Span** — verbatim quote bound to source | `evidence_spans(text, span_hash, line_start/end)` byte-equal enforced | `evidence_spans(text, span_hash, span_text_sha256)` | `EvidenceBinding` (verdict↔observation hyperedge) | All three enforce byte-equality / drift detection |
| 3 | **Source** — bibliographic + identity (DOI/PMID/SHA) | `filings_and_datasets(doi, pmid, pmcid, ...)` | `primary_sources(doi, pmid, pmcid, retraction_status_observed_at)` | `source_observations(source_id, canonical_source_id, status, content_hash)` | Phase 5 unified on canonical `source_id` form across all three |
| 4 | **Verdict / Certificate** — model-attributed review | `FSMCertificate(fsm_kind, axes, state)` from closure-FSM | `ClaimClosureCertificate(hard_closure, risk_axes, proof_hash, refusal_codes)` | `ClaimVerdict(support_state, review_status, verdict_projection_hash)` | All three use **three-value logic** (VALID/INVALID/UNKNOWN), not boolean |
| 5 | **Supersession** — append-only updates via replacement chain | `assertions.replacement_assertion_id` | `assertion_identities` clusters + replacement chains | `verdict_supersedings(prior_verdict_id, new_verdict_id, reason)` | All three forbid UPDATE on the core fact rows |
| 6 | **Bitemporal time** — transaction time + world time | `assertions.valid_time_start/end` | `assertions.valid_time_start/end` | `(asserted_at, valid_from)` columns | Same pair: when recorded vs when true |
| 7 | **Single locked writer** — sole atomic mutation surface | `replay.py` idempotent rebuild + atomic rename | claim-store mutation harness + cert-stack producer-side proof | `MutationGateway` (fcntl writer.lock + 2-phase commit + crash-injected tests) | Genomics is most rigorous; pattern is shared |
| 8 | **Pattern B (facade module)** — read-side import surface | `tools/theses/__init__.py` re-exports | `src/phenome/__init__.py` re-exports | `scripts/knowledge/__init__.py` re-exports | No project subscribes to events; all read via thin module import |

These eight primitives form what the genomics 2026-05-09 decision calls "scientific claim governance as general substrate." They are not yet extracted into a library — the decision explicitly defers extraction.

### The fourth primitive — added 2026-05-11 by agent-infra

**The canonical source store IS the federation layer.**  
`~/Projects/corpus/<source_id>/annotations.jsonl` is an append-only JSONL of "who processed this source, with what model, when." To answer "has any repo verified source X?" you read **one file**. No federation server, no shared library, no MCP-to-MCP calls.

This is the central architectural insight from the 2026-05-11 cross-attestation decision: **filesystem semantics + content-addressed identity = federation**.

---

## Section 1 — Side-by-side comparison

### 1.1 Storage substrate

| | intel | phenome | genomics | agent-infra |
|---|-------|---------|----------|-------------|
| **Primary DB** | `intel/indexed/theses.duckdb` (32.5 MB) | `indexed/claims.duckdb` (64 MB) | `data/knowledge/knowledge.duckdb` (25 MB) | `~/Projects/corpus/graph.duckdb` |
| **Audit / history** | append-only journals `analysis/_logs/*.jsonl` + `theses.prev.duckdb` snapshot | `claim_closure_certificates` table + `claims.prev.duckdb` | `audit_history.duckdb` (6.4 GB append-only NDJSON ingest) | per-source `annotations.jsonl` |
| **Domain context DBs** | `intel.duckdb` (entity crosswalk), `state.duckdb` | `umls_reference.duckdb` (5.2 GB), `pgx.duckdb`, `onsides.db` (939 MB), `medical_data.duckdb` | `cost_calibration.duckdb` (455 MB), `source_summaries.duckdb` | n/a (substrate-only) |
| **Lock mechanism** | atomic rename (build new, rename old → `prev`, new → current) | producer-side proof; no explicit writer lock documented | `fcntl writer.lock` + 2-phase commit (DB → staged FS renames) | POSIX `O_APPEND` (≤4 KB lines fit `PIPE_BUF`) |
| **Schema versioning** | layered (Layers 0–4) + view materialization | v4 (breaking refactor from v3, no compat) | migration DDL files + auto-detect schema_version per release | SchemaVer `1-0-0` (MODEL-REVISION-ADDITION) |
| **Table count (core)** | 20 tables + 10+ views | 40+ tables + 17 views | 13 tables + 1 audit view | 3 tables (`papers`, `edges`, `annotations`) |

### 1.2 Domain language (vocabulary)

| Concept | intel | phenome | genomics |
|---|---|---|---|
| Atomic claim | **Assertion** (`predicate_family='claim'`) | **Assertion** (`predicate_family`) | **ClaimRecord** + **Assertion** |
| Strategic claim | **Thesis** (`predicate_family='thesis'`) | (cert-stack closure level) | (no explicit) |
| Verbatim quote | **EvidenceSpan** | **EvidenceSpan** | (paper_evidence + content_hash) |
| Source artifact | **Filing/Dataset** | **PrimarySource** | **SourceObservation** + **KnowledgeRelease** |
| Reviewed conclusion | **FSMCertificate** (entry + monitoring) | **ClaimClosureCertificate** (cert-stack) | **ClaimVerdict** (typed `support_state`) |
| Supersession event | `replacement_assertion_id` | `assertion_identities` clusters | **VerdictSupersedingEvent** (9 reason enum) |
| Refusal | `RefusalCode` in FSMCertificate.axes | typed `refusal_codes` (first-class) | `unevaluable` in `SupportState` |
| Outside-world freshness check | `upstream_observations.jsonl` | **UpstreamCheckArtifact** (Crossref, PubMed, ClinVar, …) | **SourceAdapter** (10+ providers) |

### 1.3 Identity rule

| | intel | phenome | genomics | agent-infra (corpus) |
|---|---|---|---|---|
| **Assertion/Claim ID** | UUID5 namespace + content_hash | UUID + `identity_version` overlay (plan 01) | `claim_id` curator-stable (lint-enforced no content-derivation) | n/a (claims live in repos) |
| **Source ID** | DOI/PMID/PMCID columns | DOI/PMID/PMCID + `external_url` | `source_id` + Phase-5 `canonical_source_id` | **canonical:** `doi_<slug>`, `pmid_<n>`, `pmcid_<id>`, `db_<slug>`, `tool_<slug>`, `sha_<hash16>` (precedence DOI > PMID > SHA) |
| **Verdict ID** | n/a (FSM axes are derived, not persisted as IDs) | `certificate_id = sha256(canonical_json(...))` | `verdict_id = ULID` |
| **Annotation ID** | n/a | n/a | n/a | `ann_ + sha256(stable_tuple)[:16]` — idempotent on retries |

Notice the divergence: **genomics insists `claim_id` is curator-stable** (lint hook forbids content-derivation). Intel and phenome both derive IDs from content. This is a real semantic divergence — it reflects whether claim text is allowed to evolve while the claim persists. Genomics says yes (claim is the "named question"); intel/phenome say no (claim is its content).

### 1.4 MCP surface

| MCP | Project | Role | Tools |
|---|---|---|---|
| `intel-theses` | intel | Read-only query + FSM eval | 18 (incl. `entry_readiness`, `monitoring_state`, substrate trio: `claims_for_source`, `verdicts_for_claim`, `record_verdict` ← **disabled** until write gateway lands) |
| `intelligence` | intel | Entity resolution + gov crosswalk | 4 (`resolve_entity`, `screen_entity`, `get_dossier`, `search_entities`) |
| `phenome` (claims_tools) | phenome | Claim store query | 9 (`claim_query`, `belief_history`, `entity_density`, `uncited_claims`, `stale_claims`, `path_neighbors`, `intervention_outcomes`, `claim_store_status`, `entity_facts`) |
| `phenome` (cert_stack_tools) | phenome | Cert-stack ops | 8 (`claim_closure_certify`, `bridge_snapshot_certify`, `answerability_certificate`, `answer_with_certificate`, `diagnostic_*`, `cert_stack_status`) |
| `phenome` (substrate_tools) | phenome | Substrate trio | 3 (`claims_for_source`, `verdicts_for_claim`, `record_verdict` ← signature only, returns `not_implemented_yet`) |
| `genomics` | genomics | Pipeline orchestration (NOT knowledge governance) | pipeline + orchestrator views, Modal volume I/O |
| `corpus-mcp` | agent-infra | Layer-1 canonical store ops | 6 (`corpus_lookup`, `corpus_graph_query`, `corpus_attest` ← **SOLE writer**, `corpus_annotations_query`, `corpus_ingest`, `corpus_dashboard`) |
| `agent-infra-mcp` | agent-infra | Markdown research search (returned to narrow scope after Phase 3) | 1 (`search`) |
| `research-mcp` | agent-infra (separate repo) | Discovery, fetch, citation graph; writes to `~/Projects/corpus/` | `fetch_paper`, `search_papers`, `prepare_evidence`, `ask_papers`, `traverse_citations`, … |

**Substrate Phase 4 contract** — every per-repo MCP MUST expose: `claims_for_source(source_id)`, `verdicts_for_claim(claim_id)`, `record_verdict(...)`. Intel and phenome have signatures; both currently return `not_implemented_yet` for `record_verdict`. Genomics doesn't expose its knowledge layer via MCP yet — consumed via CLI + Python imports (Pattern B).

### 1.5 Verifier / ingestion paths

| | intel | phenome | genomics |
|---|---|---|---|
| **Ingestion scripts** | 60+ `tools/*.py` (SEC, FRED, FOIA, Substack, dataset downloaders) | 40+ `scripts/connectors/*.py` (Crossref, PubMed, ClinVar, CPIC, KEGG, OnSIDES, genomics-bridge, …) | 10+ `scripts/knowledge/adapters/*.py` (PubMed, PMC, ClinVar, gnomAD, PharmGKB, Unpaywall, OpenAlex, ClinGen, Crossref) — uniform `SourceAdapter` ABC |
| **Verifier entry points** | inline within ingestion + hook-enforced evidence-quality gates | 5 verifiers (`verify_quantitative_claims.py`, `verify_citation_ids.py`, `verify_pgx_consistency.py`, `verify_protocol_claims.py`, `verify_variant_claims.py`) | `DirectionDQuorumRunner` (verifier-first extraction) + canary windows |
| **Calls research-mcp?** | not yet (planned Phase 4 bridge; "highest-ROI lone-wolf piece") | optional; native verifiers preferred | adapters return `SourceBundle`; cross-repo corpus via agent-infra `corpus-mcp` |
| **Writes to corpus/** | not yet | not yet | via `research-mcp.fetch_paper` (already routed to canonical store) |
| **Drift detection** | atomic rebuild + verbatim re-extraction | `upstream_check_artifacts` + retraction polling | `audit_immutability.py` + `verdict_binding_mismatch` audit table + `canary_results` for model drift |

### 1.6 Verdict mechanism — three flavors of the same idea

**intel — closure-FSM (12 axes entry + 6 axes monitoring):**
```
data_integrity → falsifier_present → kill_conditions → mandate_fit
→ compounding_gate → evidence_freshness → no_active_contradictions
→ cross_domain_convergence → ev_vs_benchmark → liquidity_adv
→ sleeve_cap → catalyst_calendar_validity
```
Each axis returns `AxisVerdict(state ∈ {VALID, WARN, INVALID}, refusal_codes, is_blocking)`. Final certificate `state ∈ {valid, warn, invalid}`. The same axis code path runs prospectively (pre-write hook, on overlay state) and retrospectively (post-rebuild).

**phenome — cert-stack (10 plans, 4 cert types):**
```
ClaimClosureCertificate     — per-assertion proof (Plan 03)
BridgeSnapshotCertificate   — genomics artifact FSM (Plan 04)
AnswerabilityCertificate    — orchestrator-level routing (Plan 07)
ExplainPathProof           — bounded typed explanation traces (Plan 06)
```
`hard_closure ∈ {VALID, INVALID, UNKNOWN}` (three-value, never boolean). Producer-side proof for cross-repo artifacts. **Refusal as first-class output** (typed refusals with codes, never quiet caveats). Plans 01–08 shipped 2026-04-27; zero transition shims; `phenome.explanations`, `phenome.genomics_bridge`, `phenome search` CLI hard-deleted.

**genomics — bitemporal verdict + projection-hash cascade:**
```python
class ClaimVerdict:
    support_state: SupportState  # 7-enum
    review_status: ReviewStatus  # 6-enum  
    asserted_at: datetime        # transaction time
    valid_from: datetime         # world time
    verdict_projection_hash: str # SHA256 — DRIVES CASCADE
    evidence_projection_hash: str # SHA256 — AUDIT ONLY
    claim_binding_hash: str      # SHA256(claim.identity_payload_at_render)
```
12 `TriggerKind` enum for rederivation (`SOURCE_CHANGED`, `MODEL_UPGRADED`, `PROMPT_TEMPLATE_UPDATED`, `CASCADE`, `REBIND`, `HYGIENE_DEFECT`, …). Drain coalesces triggers by `(claim_id, execution_context_hash)`. **Lazy cascade only on `verdict_projection_hash` change** — evidence rotation alone does not cascade.

**The unifying view:** all three answer "is this claim VALID given current evidence, given current models, as of this time?" They differ in granularity (axis-based vs. typed enum vs. projection hash) but share the three-value codomain.

---

## Section 2 — Per-project deep notes

### 2.1 intel — investment theses + closure FSM

- **Constitution-shaped:** entity files have frontmatter (conviction, mcap_band, ai_relationship, energy_relationship, forward_signal, analysis_mode, session_intent) + prose. **Frontmatter + prose + journals are the three canonical surfaces; DuckDB is a derivation.**
- **Idempotent rebuild:** `replay.py` reads markdown + JSONL journals, atomically swaps `theses.duckdb` for `theses.new.duckdb`, prior snapshot kept at `theses.prev.duckdb`.
- **Hooks-enforced:** 30 pre-tool hooks gate evidence quality, mandate consistency, contradictions, kill conditions; post-tool hooks append to conviction journals.
- **Domain divergence:** intel uses `predicates` like `core_thesis_for`, `scenario_probability`, `contradicts` — totally different vocabulary from phenome/genomics, but **same predicate+slots+identity shape**.
- **In flight:** Workstream A (NBIS earnings 2026-05-13), Workstream B (systemic-infra Phases 0–3 of 6, "DO ALL OF IT"), Workstream C (Phase 8 of thesis-graph-v2 rebuild). Three blocking user decisions parked.
- **Substrate Phase 4 status:** `claims_for_source` / `verdicts_for_claim` wire-shape exists in `theses_mcp.py:391-507`; `record_verdict` is disabled (write path not yet implemented).
- **Source attribution gap:** Phase 6 (intel entity citation extraction) shipped 2026-05-15 (agent-infra commit `a3f55ea`) — was the "missing source attribution" flagged in archaeology.

### 2.2 phenome — biomedical claim store + cert-stack

- **Cert-stack is shipped (10 plans, 2026-04-27).** Hard delete of legacy paths (no shims):
  - `phenome.explanations` → `phenome.explain` (path-finding semantics)
  - `phenome.genomics_bridge` → `phenome.bridge` (producer-side proof, `open_certified_payload()`)
  - `phenome search` CLI → deleted, `phenome ask` is canonical
- **Three knowledge surfaces:**
  1. `indexed/claims.duckdb` (64 MB, 40+ tables) — durable substrate
  2. `docs/entities/` — "filesystem as database" (genes/22, self/14, drugs/2, companies/4, people/3); frontmatter-driven search elevation; epistemic tiers T0/T1/T2/T3 implicit in provenance
  3. `src/phenome/certificates/` + `bridge/` + `answerability/` — immutable proof objects
- **10 hard invariants** (from `cert-stack-handoff.md`):
  1. Content-addressed hashes for all proofs (never surrogate IDs)
  2. Append-only history; compensation = event-typed
  3. Three real states + NA: VALID, INVALID, UNKNOWN (no boolean)
  4. Hard closure ≠ risk: cert may emit while unsafe to use
  5. No view dependency for proof: validators read base tables only
  6. No raw payload bytes in certs (hashes/refs only)
  7. Producer-side proof for cross-repo artifacts
  8. Authority by surface, not similarity
  9. Canonical IDs at storage layer (not aliases)
  10. **Refusal as first-class output** (typed refusals, never quiet caveats)
- **Five citation verifiers:** quantitative claims, citation IDs, PGx consistency, protocol claims, variant claims. Continuous ingestion from Crossref, PubMed, ClinVar, CPIC, KEGG, OnSIDES, genomics-bridge.
- **Genomics bridge integration:** consumes `~/Projects/markus-genotype/results/` artifacts via `BridgeSnapshotCertificate` (Plan 04).
- **In flight:** Substrate Phases 3–4 mostly shipped; schema-v4 test cleanup; checkpoint touches `.claude/rules/codebase-map.md` updates.
- **Phase 6 (2026-05-14, commit `ec01964`):** `primary_sources` table (28 rows) deprecated; references migrated to `canonical_source_id` in `assertion_evidence`.

### 2.3 genomics — bitemporal claim governance + Direction E

- **The most architecturally-rigorous of the three.** Substrate at `scripts/knowledge/` is **intentionally domain-agnostic** (decision 2026-05-09): "no genomics-specific imports in scripts/knowledge/."
- **`MutationGateway` is the only writer.** Lint hook `scripts/lint_no_direct_writes.py` enforces. Two-phase commit: DB BEGIN/COMMIT → staged FS renames. Crash-injection test harness validates every writer method's crash points (`tests/test_mutation_gateway_atomicity.py`).
- **Bitemporal everywhere:** `(asserted_at, valid_from)` on verdicts, observations, bindings, assertions. Bitemporal replay via `audit_history.duckdb` (6.4 GB append-only log).
- **Direction D + Direction E** (both completed 2026-05-10):
  - **D:** verifier-first extraction + quorum (`DirectionDQuorumRunner`, `BundleGateway` with 4 strategy adapters, `extract_candidate_spans`, `validate_span`)
  - **E:** rederivation infrastructure (Phase 0 shipped; phases 1–6 queued). Selective re-verification on source/model/evidence change. Trigger taxonomy (12 enum). Drain coalescing by `(claim_id, execution_context_hash)`. Per-drain budget gate (not per-claim). Canary windows + canary_results for model drift detection.
- **Claim binding attestation** — `claim_binding_hash = SHA256(claim.identity_bearing_payload_at_render)`. Detects stale-binding (claim text changes but verdict not re-rendered). `verdict_binding_mismatch` audit table; `migrate_to_needs_human.py` quarantine.
- **MCP exposure of knowledge layer = NONE** as of 2026-05-15. Consumed via CLI (`knowledge check|ingest|drain|rebind`), Python imports (Pattern B), or other MCPs that wrap knowledge calls (not yet implemented).
- **In flight:** Class A (3-claim attestation gap, 27 pre-F4 sources missing context, 41 refused source demotion, 28 applied-zero re-runs); Class B (revert guards, live tests); Class C (author-cluster dedup, replication-strength override, BFS cross-claim cascade).

### 2.4 agent-infra — the spine

- **Canonical store at `~/Projects/corpus/`** (226 sources, 395 annotations as of 2026-05-15). Renamed from `papers/` in Phase 0.5 (commit `498a411`) to generalize beyond papers (databases, tools, repo sources).
- **`corpus-core` library** (workspace package, `scripts/corpus/packages/corpus-core/`):
  - `annotate()` is **SOLE writer** to `annotations.jsonl`. Schema-validated, idempotent content-addressed `annotation_id`, atomic POSIX `O_APPEND`.
  - `store.py` — `get`, `paper_path`, `derive_paper_id`, `iter_papers`, `register_revision`, `compute_parsed_sha`
  - `ingest.py` — `ingest_pdf`, `ingest_url`
  - `lookup.py` — `lookup`, `annotations`, `by_repo`
  - Extraction pipelines: MinerU 3.1.0 (Apache-2.0), pymupdf4llm (deterministic), trafilatura (HTML), Marker-on-Modal (GPU), Gemini Flash 3 fallback. **Marker dropped from default (GPL-3.0 violates policy + empirically broken on macOS).**
- **`corpus-mcp.py`** (Phase 3, 6 tools, dedicated server):
  - Read: `corpus_lookup`, `corpus_graph_query`, `corpus_annotations_query`, `corpus_dashboard`
  - Write: `corpus_attest` (sole annotation writer), `corpus_ingest`
- **`agent_infra_mcp.py`** returned to narrow scope (Phase 3): single `search` tool over markdown sections across agent-infra + phenome + genomics research docs.
- **Migration plan** at `.claude/plans/2026-05-11-substrate-migration.md`:

  | Phase | Status | Ship date |
  |---|---|---|
  | 0 — fetch_log measurement | ✅ Running (1-week accrual) | 2026-05-11 |
  | 0.5 — papers→corpus rename + workspace reshape | ✅ Complete | 2026-05-11 |
  | 1 — corpus_core library + annotation primitive | ✅ Complete | 2026-05-11 |
  | 1.5 — extraction pipelines | ✅ Complete | 2026-05-11 |
  | 2 — global annotations table in graph.duckdb | ✅ Complete | 2026-05-11 |
  | 3 — corpus-mcp dedicated server | ✅ Complete | 2026-05-11 |
  | 4 — per-repo MCP shared interface + audit_corpus_sync | ✅ Complete | 2026-05-11 |
  | 5 — canonical_source_id rebase (genomics + phenome) | ✅ Complete | 2026-05-14 |
  | 6 — intel entity citation extraction | ✅ Complete | 2026-05-15 |
  | 6.5 — phenome primary_sources rebase | ✅ Complete | 2026-05-14 |
  | 7 — observability + docs | ⏳ In progress | 2026-05-15 |

- **`audit_corpus_sync.py`** — daily launchd job at 04:30. Reads per-repo verdict DBs, queries `corpus/graph.duckdb.annotations`, detects drift (verdicts without annotations, annotations without verdicts). Logs to `~/.claude/logs/corpus/`.
- **CLAUDE.md hard rule** (the two-call invariant):
  ```
  1. <repo>_mcp.record_verdict(...)   # repo-local write
  2. corpus_mcp.corpus_attest(...)    # provenance annotation
  NEVER MCP-to-MCP. Agent orchestrates both.
  ```

### 2.5 evals — in the ecosystem, NOT in the substrate

**Verdict: PARTIALLY integrated. Same MCP world, distinct concern.**

- **What evals is:** benchmark harness for claim verification. Curates seed cases from 9 public datasets (AVeriTeC, ClaimDB, FEVEROUS, HoVer, SciFact, MSVEC, SoMe, DeepSearchQA, LiveDRBench). 59 cases × 4 arms (sterile / project / project_plus_mcps / real_setup) × scoring (verdict_correct, verdict_correct_clean, false_confidence, abstention_correct, citation_quality).
- **Storage:** per-run JSONL artifacts at `data/processed/runs/{date}/{arm}/{case_id}/{run_id}/` (manifest, transcript, tools, score). `evals.duckdb` declared in `.mcp.json` but file is gitignored and created at runtime via duckdb-mcp.
- **What it reads from substrate:** `research-mcp` (called by agent during runs), `exa`, `duckdb-mcp`. `corpus-mcp` is configured in `.mcp.json` but **never invoked** from evals scripts.
- **What it writes to substrate:** nothing. No `corpus_attest` calls. No verdicts pushed.
- **The `corpus_attest` declaration** (CLAUDE.md / AGENTS.md lines 72–77): declares the two-call pattern as a cross-project rule. Implementation plan (`f45e8982-claim-verifier-eval-v1.md:161`) explicitly marks it **"best-effort, non-blocking"** — failures log to `score.json.attest_status` and do not block. The grader (`grade_case_v2.py`) does NOT call it.
- **Why not integrated:** scope is methodology validation, not provenance. Handoff doc explicitly defers corpus integration as priority #6 of 8.
- **Latent integration surface:** if evals moves to publishable benchmark, four hooks exist:
  1. Add `corpus_attest` in `grade_case.py` after grading (recommended by plan, deferred)
  2. Use `corpus_lookup` in agent prompts to check if corpus has parsed text before calling research-mcp
  3. Route biomedical claims via `corpus_graph_query` (handoff priority #6)
  4. Join with cross-project verdicts (currently no consumer of evals output exists)

---

## Section 3 — The unified spine (what shipped)

The 2026-05-11 substrate v1 architecture, mostly executed by 2026-05-15:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      LAYER 4 — MCP SURFACE                                 │
│  corpus-mcp    │ intel-theses │ phenome (claims+cert+substrate) │ genomics  │
│  6 tools         18 tools       9+8+3 tools                       (pipeline)│
│  + agent-infra-mcp (markdown search), research-mcp (fetch/discovery)       │
└────────┬───────────────┬─────────────────┬─────────────────┬──────────────┘
         │               │                 │                 │
┌────────┴───┐   ┌───────┴────┐   ┌────────┴───┐   ┌─────────┴───┐
│ LAYER 3    │   │ LAYER 3    │   │ LAYER 3    │   │ LAYER 3      │
│ Verdicts   │   │ Verdicts   │   │ Verdicts   │   │ (NONE — pipe-│
│ corpus-side│   │ FSMCert    │   │ ClaimClose │   │ line-first;  │
│ via attest │   │ in views   │   │ Cert in    │   │ but           │
│            │   │            │   │ claims.dd  │   │ ClaimVerdict │
│            │   │            │   │            │   │ in knowledge │
│            │   │            │   │            │   │ .duckdb)     │
├────────────┤   ├────────────┤   ├────────────┤   ├──────────────┤
│ LAYER 2    │   │ LAYER 2    │   │ LAYER 2    │   │ LAYER 2      │
│ Claims     │   │ Theses+    │   │ Assertions │   │ ClaimRecord  │
│ (none —    │   │ Assertions │   │ + Identity │   │ + Predicate  │
│  corpus    │   │ in theses  │   │ Overlay    │   │ Assertion    │
│  doesn't   │   │ .duckdb    │   │ in claims  │   │ in knowledge │
│  own       │   │            │   │ .duckdb    │   │ .duckdb      │
│  claims)   │   │            │   │            │   │              │
├────────────┴───┴────────────┴───┴────────────┴───┴──────────────┤
│ LAYER 1 — CANONICAL SOURCE STORE  (~/Projects/corpus/)             │
│   <source_id>/                                                     │
│     metadata.json (DOI/PMID/SHA + revisions[])                     │
│     paper.pdf + paper.<sha>.pdf (archived revisions)               │
│     parsed.<parser_id>/ (immutable per parser version)             │
│     citation_context/ (scite, openalex, crossref, pubmed)          │
│     citances_in.jsonl + citances_out.jsonl + references_resolved   │
│     annotations.jsonl  ← APPEND-ONLY, ≤4KB lines, O_APPEND atomic │
│     INDEX.json (derived cache of used_by)                          │
│   graph.duckdb (papers, edges, annotations — 3 tables)             │
│                                                                    │
│   IDENTITY: content-addressable                                    │
│   PRECEDENCE: DOI > PMID > SHA                                     │
│   FORMS: doi_<slug>, pmid_<n>, pmcid_<id>, db_<slug>, tool_<slug>, │
│          repo_<slug>, sha_<hash16>                                 │
└────────────────────────────────────────────────────────────────────┘
                              ▲
                              │  daily 04:30
                              │
             ┌────────────────┴─────────────────┐
             │  audit_corpus_sync.py             │
             │  Detects drift: verdicts without  │
             │  annotations / annotations without│
             │  verdicts. Logs to                │
             │  ~/.claude/logs/corpus/           │
             └───────────────────────────────────┘
```

**The federation answer:**
> "Which repos have verified this source?"  
> → read `~/Projects/corpus/<source_id>/annotations.jsonl`  
> "What did they conclude?"  
> → call the relevant `<repo>_mcp.verdicts_for_claim()` for each annotation pointing back to a verdict.

Two hops. No federation server. No shared library (besides `corpus-core` as the canonical writer).

---

## Section 4 — Commonalities (the stable kernel candidate)

If you wanted to extract a `claim_governance` library, this is what each repo would consume:

```
claim_governance/
  identity.py        # UUID5(namespace, content_hash) OR curator_stable_name policy
  bitemporal.py      # (asserted_at, valid_from) pair; window functions for "current"
  mutation_gateway.py  # fcntl lock + 2-phase commit + crash-injection-tested
  events.py          # SupersedingEvent, RebindEvent, CascadeTrigger taxonomies
  verdict.py         # ClaimVerdict ABC; subclassed for FSM/cert/projection variants
  evidence.py        # Span + verbatim quote + drift detection
  source.py          # Source identity rule + canonical_source_id resolver
  audit.py           # Append-only enforcement; mismatch detection
  refusal.py         # Typed RefusalCode (first-class output)
  pattern_b.py       # Facade module re-export utility
```

The vetoed-decisions file (2026-03-19) explicitly **rejected** shared utility libraries on maintenance grounds. The genomics decision (2026-05-09) re-opens the question — recognizing the substrate as domain-agnostic but **deferring extraction**. The argument: each repo's substrate is settling; extracting prematurely couples them to a moving schema.

**What's actually shared today (the kernel as it exists, not as it could exist):**

1. **The `corpus-core` library** (`scripts/corpus/packages/corpus-core/corpus_core/`) — the only true shared code. Owns canonical source identity, annotation primitive, extraction pipelines.
2. **The annotation schema** (`scripts/corpus/schemas/v1/annotation.v1.json`) — strict, SchemaVer-versioned, validates every annotation written.
3. **The substrate MCP interface contract** — `claims_for_source`, `verdicts_for_claim`, `record_verdict` shape declared in agent-infra plan + implemented signature-wise in intel + phenome (genomics not yet MCP-exposed).
4. **The two-call attestation invariant** — CLAUDE.md hard rule, enforced by `audit_corpus_sync.py` daily.
5. **The Pattern B convention** — read-side facade modules; no event subscription. Each repo's `__init__.py` re-exports the read API.

**What's NOT shared (and arguably should not be, per current decisions):**

- Schema definitions for verdicts (each repo's verdict shape is domain-specific)
- Trigger taxonomies (genomics' 12-enum vs. phenome's cert-stack vs. intel's monitoring axes)
- Predicate vocabularies (financial vs. biomedical vs. genomic — totally different)
- FSM definitions (intel's 12+6 axes vs. phenome's risk_axes vs. genomics' SupportState enum)
- Mutation gateway implementation (genomics' is fcntl+2PC; phenome's is producer-side proof; intel's is atomic-rename)

The eight-primitive kernel from the TL;DR is the **conceptual** kernel — not the implementation kernel. Each repo implements the primitives differently because their domains demand it.

---

## Section 5 — What's in flight (knowledge-infra slice)

### Substrate Phase 7 (in progress, 2026-05-15)
- Agent-infra commit `a3f55ea` partial: observability + docs
- OpenTelemetry spans on corpus operations
- LaunchD recipes for audit/maintain
- Metadata backfill

### Phase 0 measurement (1-week accrual ends ~2026-05-18)
- research-mcp `fetch_log` table accumulating duplicate-fetch evidence
- Decision gate: if duplicate rate ≥10% → Phase 2 (cache inside `fetch_paper`) justified. If <10% → premise wrong, deprioritize.

### Intel — three blocking user decisions
- NBIS $30K concentration trim (earnings 2026-05-13 BMO)
- Apply 2026-05-11 GOALS.md philosophy revision (Tier 0 conviction as primary)
- Power-layer name selection for first fresh BUY workup

### Intel — Workstream B (Phases 0–3 of 6 systemic-infra)
- Phase 0: archive coherence, hook orphan reconciliation
- Phase 1: conviction tracking refactor
- Phase 2: evidence-quality gate consolidation (5+ hooks → 1)
- Phase 3: friction-vs-EV mechanical gates

### Phenome
- Schema-v4 test cleanup (commits `6670ff0`, `723f50b`)
- Cert-stack Phase 6 close-review fixes (commit `ae14031`)
- Substrate Phases 3–4 implementation continuing

### Genomics — Class A backlog (gap-closing)
- 3-claim attestation gap (33 → 30 threshold); needs better OA fetcher (Unpaywall #1)
- 27 pre-F4 sources missing citation_context events — backfill
- 41 refused sources to demote (build `refused_quorum_demote.py`)
- 28 applied_zero sources to re-run

### Genomics — Direction E Phases 1–6 queued
- Phase 1–2: drain dispatcher + rebind handoff
- Phase 3–6: cascade walker, model_canary integration, executor cost gating

### Cross-cutting
- Phenome → research-mcp shared verification tools (deferred)
- Intel → research-mcp bridge write path (disabled, "highest-ROI lone-wolf piece")
- Evals → corpus integration (deferred, priority #6 of 8)

---

## Section 6 — Concrete files to read next (pointer list)

For deeper inspection, in priority order:

**The architectural spine:**
1. `~/Projects/agent-infra/research/scientific-substrate-target-architecture.md` — Layer 1–4 model, decisions made
2. `~/Projects/agent-infra/.claude/plans/2026-05-11-substrate-migration.md` — 7-phase plan, status, cost analysis
3. `~/Projects/agent-infra/decisions/2026-05-11-cross-attestation-substrate.md` — current substrate decision
4. `~/Projects/agent-infra/research/cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md` — archaeology synthesis
5. `~/Projects/corpus/SCHEMA.md` — canonical store schema
6. `~/Projects/agent-infra/scripts/corpus/packages/corpus-core/corpus_core/annotate.py` — sole annotation writer

**Per-project kernels:**
7. `~/Projects/genomics/scripts/knowledge/event_types.py` — typed contracts (the most rigorous)
8. `~/Projects/genomics/scripts/knowledge/mutation_gateway.py` — 2-phase commit + crash recovery
9. `~/Projects/genomics/decisions/2026-05-09-scientific-claim-governance-as-general-substrate.md` — substrate-as-general-primitive recognition
10. `~/Projects/phenome/src/phenome/certificates/claim_closure.py` — ClaimClosureCertificate (cert-stack proof object)
11. `~/Projects/phenome/.claude/cert-stack-handoff.md` — 10 hard invariants, plans 01–08
12. `~/Projects/intel/tools/theses/closure/certificate.py` — FSMCertificate + AxisVerdict
13. `~/Projects/intel/tools/theses/schema.sql` — 4-layer DuckDB schema
14. `~/Projects/intel/.claude/plans/f24889d4-thesis-graph-v2.md` — thesis-graph-v2 breaking refactor

**The cross-project archaeology (130 KB, 6 files):**
- `~/Projects/agent-infra/research/cross-project-synthesis-2026-05-11/{01..06}-*.md`

---

## Section 7 — Open questions surfaced by the inventory

These are observations from reading the dossiers, not recommendations. The user steers from here.

1. **Should the eight-primitive kernel become a library?**  
   Genomics 2026-05-09 decision explicitly defers ("substrate is intentionally general but not yet extracted"). Vetoed-decisions 2026-03-19 rejected shared utility libraries on maintenance grounds. The question reopens as direction-E + cert-stack + thesis-graph-v2 all settle. Re-evaluation likely after Phase 7 (observability) closes — call it ~2 weeks out.

2. **Why does genomics not expose knowledge governance via MCP?**  
   It exposes pipeline orchestration only. The Phase 4 contract (`claims_for_source` / `verdicts_for_claim` / `record_verdict`) is implemented in intel + phenome but not genomics. A `knowledge-mcp` wrapping `scripts/knowledge/` would close the trio.

3. **Intel `record_verdict` is disabled — why?**  
   Phase 4 wire shape exists in `theses_mcp.py:391-507` but write path is gated on intel's own mutation gateway, not yet implemented. Currently theses_mcp is read-only. The write path is the "intel → research-mcp bridge" called "highest-ROI lone-wolf piece" in the 2026-05-11 decision.

4. **Phenome's 9 citation verifier scripts — consolidate into research-mcp?**  
   The 2026-05-11 decision said "stay in place until `research_mcp.audit_citations()` ships AND a grep/import-graph proof shows no external callers." Status: deferred.

5. **The `claim_binding_hash` from genomics — generalize to phenome/intel?**  
   Genomics' attestation that "this verdict was rendered against claim text X" enables detection of stale-binding. Phenome's content-addressed certificate_id implicitly does this. Intel's UUID5 + content_hash on assertions does this. Could be standardized in the kernel.

6. **Is the `Pattern B` facade enough, or do projects need event subscription?**  
   All three repos chose Pattern B (read via thin module import). No cross-repo events. The audit_corpus_sync daily job is the only "subscriber" pattern, and it's pull-mode polling not push. This is intentional — events were considered and deferred in the 2026-05-11 decision.

7. **Where does evals fit if it ever publishes?**  
   Wiring `corpus_attest` into `grade_case_v2.py` is a ~50-line change. The latent value is using corpus as ground-truth source for biomedical claims (handoff priority #6) — but no one runs that today.

---

## Appendix — Three-pass reading list by depth

**5-minute scan:** Read sections TL;DR + Section 1 of this doc. You'll have the kernel + side-by-side.

**30-minute deep:** Add sections 2.1–2.4 + Section 3. You'll know each project's mechanism + the unified spine.

**Full audit (2-3 hours):** Read the four per-project source dossiers in `/tmp/*-knowledge-dossier.md`. Then read the seven concrete-pointers files in Section 6. You'll be at parity with whoever wrote the substrate.

---

*Dossier compiled 2026-05-15 from parallel Explore-agent inventories. Each per-project dossier is preserved verbatim at `/tmp/`. The "kernel" framing is empirical observation across three independent implementations, not advocacy — the user steers whether/when to extract.*

<!-- knowledge-index
generated: 2026-05-15T06:04:11Z
hash: d993b65ac9ca

index:title: Cross-Project Knowledge Infrastructure Dossier — intel × phenome × genomics × agent-infra (+ evals)
index:status: active
index:tags: knowledge-substrate, cross-project, kernel-synthesis, corpus, attestation
cross_refs: decisions/2026-03-17-shared-knowledge-substrate.md, decisions/2026-05-09-scientific-claim-governance-as-general-substrate.md, decisions/2026-05-11-cross-attestation-substrate.md, research/cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md, research/cross-project-synthesis-2026-05-11/{01..06}-*.md, research/scientific-substrate-target-architecture.md
table_claims: 23

end-knowledge-index -->
