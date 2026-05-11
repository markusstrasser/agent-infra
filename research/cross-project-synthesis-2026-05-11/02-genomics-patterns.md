# Genomics — Attestation & Knowledge Infrastructure Patterns

Pattern-extraction pass on `~/Projects/genomics` for cross-project synthesis.
The user's framing — "genomics leads the way on attestation" — is borne out:
this repo has the most mature event-sourced, model-attributed,
source-versioned claim ledger in the constellation.

## What Genomics Does

Personal WGS interpretation platform: Nebula 30x short-read, scaling to PacBio
HiFi and Illumina blood. Modal-backed stage DAG processes raw VCFs through
variant calling → annotation → trait/PGx/blood-group/oncology interpretation →
clinical-grade review packets. The repo has ~700+ scripts (`scripts/`), a
DuckDB knowledge ledger, ~10 domain skills, an MCP server, and a curation
substrate that tracks which model said what about which claim based on which
source release. Recent commit activity is dominated by `[direction-e]` —
the "rederivation infrastructure" workstream that built the event-sourced
attestation core.

## Attestation Pattern (DETAILED)

The schema lives in `~/Projects/genomics/data/knowledge/knowledge.duckdb`,
defined by `migrations/2026-05-09-knowledge-tables.sql` plus four follow-up
migrations. **All tables INSERT-only at the application layer**, enforced by
three layers:

1. `scripts/knowledge/mutation_gateway.py` — sole writer (two-phase commit
   across DuckDB + FS sidecars, file lock at `data/knowledge/writer.lock`)
2. `scripts/lint_no_direct_writes.py` — bans `INSERT` outside the gateway
3. `scripts/knowledge/audit_immutability.py` — periodic audit

### Core Tables (12, current counts in parens)

```
claim_verdicts          (492)   — model verdict on a claim, bitemporal
assertions              (0)     — predicate-registry-pinned claim text
evidence_bindings              — verdict ↔ source_observation N:M binding
source_observations            — per-fetch immutable observation row
knowledge_releases             — source release registry (gnomAD r4, ClinVar 2026-03, ...)
rederivation_triggers   (1980) — kinds: hygiene_defect(1312), rebind(494), cascade(174)
trigger_drain_events           — append-only drain log per trigger
canary_windows                 — model-version calibration windows
canary_results                 — per-window canary outcomes
verdict_supersedings           — supersede edges between verdicts
claim_evidence_rebounds        — curator rebind events
cycle_defects                  — per-cycle defect ledger
```

### claim_verdicts columns (the core attestation row)

```
verdict_id                VARCHAR PRIMARY KEY
claim_id                  VARCHAR NOT NULL
support_state             VARCHAR NOT NULL    -- {unexamined, weak, moderate, strong,
                                              --  contradicted, refuted, unevaluable}
review_status             VARCHAR NOT NULL    -- {current, stale_no_trigger,
                                              --  stale_with_trigger, conflicting,
                                              --  superseded, needs_human}
model_version             VARCHAR NOT NULL    -- WHO did the work
prompt_template_hash      VARCHAR NOT NULL    -- WHICH prompt template
canary_window_id          VARCHAR NOT NULL    -- WHICH calibration window
asserted_at               TIMESTAMP NOT NULL  -- transaction time
valid_from                TIMESTAMP NOT NULL  -- world time (bitemporal)
evidence_event_id         VARCHAR NOT NULL    -- pointer to event log
verdict_projection_hash   VARCHAR NOT NULL    -- content hash of verdict
evidence_projection_hash  VARCHAR NOT NULL    -- content hash of evidence bundle
claim_binding_hash        VARCHAR NOT NULL    -- pinned claim version
```

### source_observations columns

```
observation_id        PK
source_id             -- e.g., "db:gnomad:r4", "doi:10.1038/...", "pmid:18042988"
source_release_id     -- FK into knowledge_releases
status                -- {fetched, deleted, rate_limited, oa_flip}
source_content_hash   -- REQUIRED iff status=fetched (CHECK constraint)
fetched_at            TIMESTAMP
fetched_via           -- the adapter that fetched it
evidence_depth        -- {structured, full_text, abstract, metadata, not_applicable}
valid_from, asserted_at  -- bitemporal pair
```

The `evidence_depth` enum drives the **clinical full-text gate**: claims
tagged `stake_tier=clinical` whose evidence set lacks any
`structured`/`full_text` observation are routed to `unevaluable` rather than
`supported`. This is the key "epistemic adequacy" lever.

### Write path

```
Adapter (clinvar.py / gnomad.py / pubmed.py / pharmgkb.py / openalex.py / ...)
  → MutationGateway().write_release(release)
  → MutationGateway().write_observation(obs)        # immutable
  → quorum_runner / verifier produces verdict
  → MutationGateway().write_verdict(verdict, supersedes_event=...)
  → MutationGateway().write_evidence_binding(binding)
```

Atomicity: one DuckDB BEGIN/COMMIT spans the whole `with` block; FS sidecars
(`config/claim_registry.json`, per-claim files under `config/source_retrievals/`)
are staged to tempfiles, then `os.replace`d after DB COMMIT. Recovery via
`_reap_orphaned_staged_writes()` on next gateway entry.

### Read path

- `scripts/knowledge/cli.py check` — read-only freshness/coverage report
- `scripts/knowledge/project_verdicts.py` — projects DuckDB verdicts onto
  `config/claim_registry.json` (the human/curator surface)
- `scripts/knowledge/as_of.py` — bitemporal "as of" replay
- `scripts/genomics_mcp.py` — MCP tools `query_review_packets`, `query_json`,
  `artifact_realization` for agents to query verdicts

### Example record (live, from claim_verdicts)

```
verdict_id              = vrd-cd0159a791424d719ea0454216d16f8c
claim_id                = sbrc_cad_rs10757278
support_state           = weak
review_status           = current
model_version           = direction-d-router-stub
prompt_template_hash    = direction-d-router-stub
asserted_at             = 2026-05-10 15:37:41.314559
evidence_event_id       = evt-1cd0c883564d43ff8245461c098337e4
verdict_projection_hash = c179ebdae2f0240ceb7ed1b772e4182bebeaa9f432bf1247bea03752bdf1f390
```

### What it prevents

- **Stale verdicts after source updates** — new `knowledge_release` row fires
  `rederivation_triggers(kind=cascade)`, queuing affected claims for re-verdict
- **Silent model drift** — `model_version` + `canary_window_id` let you
  partition verdict streams by which model produced them; canary windows
  detect when a new model would have produced different outputs
- **Cherry-picked evidence** — `evidence_bundle_sha256` is materialized from
  the source registry at verdict time; later evidence edits trigger rebinds
- **Untraceable claim edits** — `claim_binding_hash` pins the exact claim
  version a verdict was about; if the claim text changes, the verdict goes
  to `superseded`
- **Lost retractions** — Crossref Retraction Watch adapter writes a
  `source_observation(status=deleted)`, cascading retraction across all
  derived claims

## Domain Entities

The `config/claim_registry.json` schema (923+ claims at last counted shift)
shows the typed-claim model. Each claim row carries:

```
claim_id, claim_type, surface, target_kind, target_ref
owner_path, owner_key_path, caller
basis_kind                  -- {database_release, paper, derived, ...}
source_ids                  -- list of source_id strings
epistemic_class             -- {descriptive, predictive, mechanistic, ...}
evidence_grade              -- {A1, A2, B, C, ...}
verification_method, verification_scope
lifecycle_state             -- {supported, deprecated, needs_human, quarantined, ...}
stake_tier                  -- {clinical, behavioral, exploratory}
support_state               -- mirror of latest claim_verdicts
attestation: {kind, evidence_model, database_version, database_query,
              release_sha256, verification_method, verification_response_sha256}
coordinate_provenance: {genome_build, database_releases: {...}}
verification_outcome, verification_receipt_at
```

Domain entities surfaced by config files and skills:
**variants** (rsID + chr/pos/ref/alt quadruple, GRCh38-pinned),
**gene-drug** (CPIC/ClinPGx star alleles, drug labels),
**blood groups** (ISBT v4.3.0 — antigen × allele × rsID),
**traits/GWAS** (effect-allele + OR/beta + population),
**oncology variants** (OncoKB/CIViC/cBioPortal tiers),
**HLA alleles**, **CNVs/SVs** (ACMG-SV class),
**clinical guidelines** (ACMG SF v3.2, CPIC, ClinGen).

## MCP Servers and Tools Exposed

Two FastMCP servers in-repo:

- `scripts/genomics_mcp.py` — ~30+ tools covering pipeline status, artifact
  inspection, debug-run management:
  `query_json`, `query_review_packets`, `pipeline_status`,
  `artifact_realization`, `stale_runtime`, `run_frontier`, `run_remaining`,
  `run_closure`, `stage_consumers`, `sample_readiness`, `watch_active_apps`,
  `launch_order`, `current_attempt`, `attempt_runtime`, `attempt_receipt`,
  `stage_checkpoints`, `tail_attempt_events`, `tail_attempt_logs`,
  `artifact_growth`, `resume_explain`, `truth_diff`, `active_apps`,
  `controller_causality`, `launch_debug_fixture`, `list_debug_runs`,
  `debug_run_state`, `stop_debug_run`, `validate_python_syntax`,
  `modal_logs_tail`
- `scripts/mcp_genomics_adjudication_tools.py` — `build_adjudication_body`,
  `record_adjudication`, `record_retraction`

Also depends on **`biomedical-mcp`** (sibling repo, editable install) which
exposes ClinVar/gnomAD/PharmGKB/dbSNP/Ensembl/PanelApp/HPO tools used by
`bio-verify`.

## Scripts/Tools Inventory (Attestation-Specific)

```
add_claim_attestation.py            apply_attestation_manifest.py
attest_database_release_from_sources.py
attestation_proposals.py            auto_attest_from_cached_abstracts.py
auto_attest_mechanism_notes.py      bio_verify_to_attestation.py
build_trait_panel_association_attestation_queue.py
clinical_attestation_gate.py        commit_proposed_attestation.py
derivation_provenance_validator.py  drain_attestation_queue.py
finding_provenance.py               lint_attestation_kind_switch.py
lint_provenance.py                  prepare_attestation_fulltext_queue.py
propose_attestation_batch.py        propose_attestation.py
provenance_audit.py                 provenance_dag.py
provenance_event_commits.py         provenance_events.py
provenance_mutation_tests.py        provenance.py
triage_unattested_claims.py         verify_claim_attestation.py
verify_run_provenance.py            backfill_coordinate_provenance.py
```

Adapters (one file per source, uniform `SourceAdapter` Protocol):
`scripts/knowledge/adapters/{clinvar,clingen,pharmgkb,gnomad,pubmed,pmc,crossref,openalex,unpaywall}.py`

Skills inventory:
`annotsv, bio-verify, clinpgx-database, data-transform, genomics-pipeline,
genomics-status, gget, life-science-research, vcfexpress`

## Knowledge Artifacts

- `research/` — sparse (1 memo); the bulk of "what we know" is in
  `decisions/` (~20 dated decision records) and per-direction plan files in
  `docs/ops/plans/`
- `improvement-log.md`, `CYCLE.md`, `MAINTAIN.md`, `DECISIONS.md` —
  active operating ledgers
- `proposals/attestation/` — proposed quote bundles awaiting human commit
- `governance/verdict_waivers.json` — explicit human overrides
- `config/source_retrievals/*_provenance.json` — per-source-fetch provenance
  sidecars (50+ files)

## Recurring Patterns Likely Shared with Phenome/Intel

1. **Single-writer mutation gateway + lint enforcement.** Three-layer
   immutability (gateway / lint / audit) generalizes to any "knowledge state
   must not be silently rewritten" use case. Phenome's behavioral data and
   intel's research notes both want this.
2. **Bitemporal verdict storage** (`asserted_at` + `valid_from`) with
   `verdict_projection_hash` + `evidence_projection_hash` for tamper-evidence.
3. **Source-release ledger with content hash** — every fetched source row
   carries `source_content_hash` + `source_release_id`. Detects upstream
   silent edits.
4. **Trigger queue → drain log pattern** for "stale claim → re-verify"
   without spinning. `rederivation_triggers` (1980 rows across hygiene /
   cascade / rebind) feeds `quorum_runner` which appends `trigger_drain_events`.
5. **SourceAdapter Protocol** — uniform interface for fetch / parse /
   normalize across heterogeneous APIs (REST, S2, Crossref). Reusable for
   phenome (Garmin/Whoop/Apple) and intel (RSS, S2, Brave).
6. **Paper fetch + parse + markdown summary** — Sci-Hub + OA + EuropePMC +
   biorxiv fallback chain in `_bulk_fetch_via_research_lib.py`,
   `_last_resort_fulltext.py`, `_prefetch_fulltext_summaries.py`.
   Cached at `data/knowledge/source_summaries.duckdb`.
7. **Dedup-before-fetch** via `(source, version_tag)` UNIQUE on
   `knowledge_releases` and `source_content_hash` keying on observations.
8. **Source grading + epistemic tiers** — `.claude/rules/epistemic-tiers.md`,
   `evidence_grade` field, `stake_tier` enum. Decouples "how good is the
   source" from "how high are the stakes for this claim."
9. **Two-phase commit across DB + FS** for atomic registry/sidecar updates.
10. **LLM-as-proposer, not committer** — `propose_attestation.py` writes
    proposals to `proposals/attestation/`; `commit_proposed_attestation.py` is
    the gated entry point.
11. **Predicate-registry-pinned assertions** — `predicate_id` +
    `predicate_registry_version` + `predicate_slot_schema_hash` so claim
    semantics are versioned even when the text doesn't change.
12. **Canary windows** for model-drift detection.

## Build-Then-Undo / Friction Signals

- Heavy Direction-D / Direction-E commit storm (50+ commits in 2 weeks)
  suggests the rederivation core is **still settling**. Several
  Phase-A/B/C/D/E/F/G/H sequences with "/critique close finding #N" commits
  indicate aggressive cross-model review pressure.
- `dd2dd2e8 Add 'unevaluable' SupportState — split transport from science` —
  late realization that "we can't verify" and "evidence refutes" must be
  separate states. Pattern: enum was under-specified, now corrected.
- `lint_no_stdlib_shadow`, `lint_no_direct_writes`, `lint_no_direct_fs_writes`,
  `lint_attestation_kind_switch`, `lint_provenance` — five custom lints
  enforcing the architecture. **Signal:** every "instructions alone" guardrail
  got promoted to architecture after failing in practice.
- `assertions` table is empty (0 rows) despite full schema — predicate
  registry exists but predicate-pinned assertions haven't been backfilled.
  Migration in progress.
- `model_version='direction-d-router-stub'` on all 492 verdicts —
  real-model verdicts haven't replaced the stub yet. The schema is real,
  the model attribution is currently degenerate. **First test of cross-model
  attestation is upcoming.**
- `source_summaries.duckdb` exists but is empty — fulltext summary cache
  table created, not yet populated.
- Multiple backfill scripts (`backfill_ast_density.py`,
  `backfill_code_hash.py`, `backfill_coordinate_provenance.py`,
  `backfill_evidence_model.py`, `backfill_legacy_retraction_audit_events.py`,
  `backfill_pmid_retrieved_at.py`) — schema evolution has outrun data
  migration; expect more of these.
- "needs_human as first-class lifecycle" (commit `6bad47fc`, cleared 22
  fatal/quarantined claims) — earlier attempts to make the verifier fully
  autonomous failed; explicit human-in-loop state was added back.

## Candidates for Shared Infrastructure

**Strongest candidates** (genomics-led, generalizable):

1. **`attestation-core`** library: DuckDB schema + `MutationGateway` +
   bitemporal verdict storage + trigger queue. Phenome can attest "Garmin
   reported HRV=X on date D, source_release=garmin-api-v2.3, content_hash=…"
   identically. Intel can attest "S2 returned paper P on date D, citing X."
2. **`SourceAdapter` protocol** + standard adapters (Crossref, S2, OpenAlex,
   PubMed, Unpaywall, EuropePMC, Sci-Hub fallback). Already largely lives in
   `research-mcp` — genomics has hardened variants worth promoting.
3. **`paper-fetch-fallback-chain`**: Sci-Hub → OA → EuropePMC → biorxiv-by-title
   pattern from `scripts/_last_resort_fulltext.py`. Reusable everywhere.
4. **`bio-verify`-style claim-extraction + cross-source-verification skill**
   generalized to "hardcoded-constant audit" for any domain.
5. **Three-layer immutability** (gateway + lint + audit) as a project
   template. The pattern transfers to any "append-only fact store" use case.
6. **Stake-tier × evidence-depth gate** (`clinical_attestation_gate.py`,
   `evidence_depth` enum). Generalizable as "block low-evidence claims at
   high-stakes surfaces."
7. **Two-phase commit utility** (`MutationGateway.__exit__` pattern) for
   atomic DB + FS sidecar writes — useful anywhere config sidecars mirror
   DB rows.
8. **Predicate-registry pattern** for versioned claim semantics —
   prerequisite for any cross-project "what does this claim mean today vs
   when it was made" replay.

**Avoid extracting prematurely:**
- The full Direction-E rederivation engine — still settling; extract after
  it stabilizes (assertion backfill complete, real model_versions in
  claim_verdicts).
- Trigger queue specifics — the kind enum (`hygiene_defect`, `cascade`,
  `rebind`) is domain-shaped.

<!-- knowledge-index
generated: 2026-05-11T04:08:32Z
hash: 4ab608439d0b


end-knowledge-index -->
