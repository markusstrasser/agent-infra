# Phenome — Pattern Extraction for Cross-Project Synthesis

Repo: `~/Projects/phenome` (personal knowledge manifold + medical/genomics knowledge graph).
Scan date: 2026-05-11. Methodology: CLAUDE.md, `.claude/{skills,rules,runbooks,plans}`, `scripts/`, `src/phenome/`, `git log -100`, `git log --grep=fix|wrong|undo`, knowledge dirs (`docs/research`, `docs/entities`, `self-reports/`, `indexed/*.duckdb`).

---

## What Phenome Does

Personal knowledge manifold + clinical/genomics knowledge graph for one user (Markus). Unifies semantic search across 25 sources / 89K entries (ChatGPT, Claude, Twitter, Git, Gmail, Calendar, YouTube, Drive, iMessage, Signal, WhatsApp, Oura, medical records, browser clippings). Also hosts a **cert-stack architecture** (proof-carrying answers over a typed claim store) + **gene/drug entity dossiers** + **Synthoria business research** (productizing the cert stack). Codebase ~50K LOC, MCP-heavy (`phenome`, `genomics-consumer`, `research`, `paperclip`, `biomedical`, `biomcp`, `scite`, `duckdb`, `modal-triage`, plus web search).

Three intertwined systems: (1) **substrate** — embeddings + DuckDB claim store, (2) **certificates** — content-addressed proofs that an answer is grounded in the substrate, (3) **research/strategy memos** — `docs/research/` (314 memos) + `docs/entities/` (35 gene pages, 2 drug pages) with append-only governance.

## Domain Entities

Canonical entity types with standards codes (mirrors what genomics/intel both need):

- **Gene** — `HGNC:SYMBOL`; entity page at `docs/entities/genes/<gene>.md` with YAML frontmatter (`title`, `tags`, `summary`, `last_reviewed`). 35 pages.
- **Drug / supplement** — `RxNorm:NNN` (e.g. `RxNorm:2601723` for tirzepatide); entity page under `docs/entities/drugs/`.
- **Variant / phenotype / condition / lab** — standards-coded (ClinVar/dbSNP, HPO, ICD/SNOMED, LOINC).
- **Primary source / paper** — DOI/PMID/PMCID/NCT/arXiv.
- **Person / company / contract / filing** — `docs/entities/{people,companies,contracts,filings}/`.
- **Self** — `docs/entities/self/genomics_findings.yaml` (clinical registry of own variants).

The `entity-management` skill (`.claude/skills/entity-management/SKILL.md`) is the contract for all of this; one-file-per-entity, git-versioned, frontmatter is load-bearing for search rank-0 elevation.

## Scripts/Tools Inventory

`scripts/` (~50 files) clusters cleanly:

| Class | Files | Pattern |
|---|---|---|
| **Citation auditing** | `audit_citations.py`, `extract_citation_ids.py`, `verify_citation_ids.py`, `audit_research_memo_contract.py`, `validate_genomics_citations.py`, `verify_quantitative_claims.py`, `verify_variant_claims.py`, `verify_pgx_consistency.py`, `verify_protocol_claims.py` | Extract DOI/PMID/PMCID/NCT regex → resolve via CrossRef + NCBI E-utils + S2 → diff title/year/authors against context → "ceiling check" rejects out-of-frontier PMIDs. 9 separate verifier scripts, lots of overlap. |
| **PDF / data ingestion** | `extract_lab_pdfs.py`, `extract_medical_pdfs.py`, `scripts/connectors/parse_*.py` (~15), `ingest_pdf.py` | PDF → markdown → structured rows; per-source parsers (Twitter, Oura, Gmail, HealthKit, Apple Photos, Instagram, Logseq, lab PDFs). |
| **External corpus loaders** | `load_ctd.py`, `load_onsides.py`, `load_pathways.py`, `fetch_pharmgkb.py`, `dsld_supplement_labels.py`, `usda_food_nutrient_lookup.py`, `openfda_adverse_events.py`, `scrape_examine*.py` | Pull and stage public biomedical corpora. |
| **Claim store ops** | `src/phenome/claims/{ingest,store,canonicalize,identity,rebuild,enrich/*,audit/*,migrations/v3_to_v4}.py` | Extract → identity-hash → store → enrich (dates, quote context, embeddings, code resolve) → audit (entity coverage, single-source detection) → migrate. |
| **Cert stack** | `src/phenome/{bridge,certificates,answerability,identity,diagnostics,explain,upstream}/` | 8-plan architecture (`8799d138-cert-stack-{00..08}`). |
| **Hooks** | `scripts/hooks/` + symlinks into `~/Projects/skills/hooks/` | Citation provenance audit, todos lint/rebuild, MCP health check, ruff-format, append-only/data guards. |
| **Genomics export bridges** | `materialize_genomics_bridge_report.py`, `sync_genomics_bridge.py`, `export_genomics_phenotype_contract.py`, `build_genomics_registry.py` | Cross-repo contract between phenome and `~/Projects/genomics/`. |

## Knowledge Artifacts (DBs, memos, attestations, schemas)

DuckDB files in `indexed/`: `claims.duckdb` (3622 assertions / 5211 entities / 12653 links), `medical_data.duckdb` (PHI, subject-scoped), `umls_reference.duckdb` (global UMLS), `pgx.duckdb`, `pending_edges.duckdb`, `todos.duckdb`, `onsides.db`, `pharmgkb_parsed.json`. Plus rolling `claims.prev.duckdb` / `todos.prev.duckdb` snapshots — append-only audit pattern.

Schemas at `src/phenome/claims/{schema.sql,views.sql,predicates.py}` — 56 typed predicates across 9 families (PK, PD, molecular, clinical, statistical, causal, observational, temporal, freeform). Content-addressable IDs (`UUID5` over canonical slot tuples) so re-ingest doesn't break references — see `claims/identity.py`, IDENTITY_VERSION=4.

**Attestation system (the load-bearing pattern):**

- `src/phenome/bridge/kg.py` — `KGAttestation` + `attest()`. Every MCP tool that surfaces KG-derived data **must** wrap output with this. Non-clinical semantics enforced as constants (`source_authority="third_party_aggregated_kg"`, `safe_for_unqualified_use=False`, etc.) — callers cannot relax them.
- `src/phenome/answerability/certificate.py` — `AnswerabilityVerdict` lattice: `SURFACE_ERROR < CANNOT_CERTIFY < CANNOT_ANSWER_FROM_LOCAL_REPO < ANSWERABLE_WITH_WARNINGS < CERTIFIED`. Lattice-meet folds dependency certs into composite verdicts.
- `src/phenome/bridge/{certify,proof}.py` — `BridgeSnapshotCertificate` (content-addressed; `CANONICAL_HASH_EXCLUSIONS` excludes wall-clock + per-emission UUIDs so identical substrate produces identical cert_id).
- `src/phenome/certificates/claim_closure.py` — `ClaimClosureCertificate` per-assertion proof.
- `CertifiableDependency` protocol — `bridge/kg.py:27` — uniform interface so KG attestation, claim closure, bridge snapshot, and path proof all compose into answerability.

Memos: `docs/research/` 314 files; append-only enforced by `~/Projects/skills/hooks/pretool-append-only-guard.sh`. Template at `_MEMO_TEMPLATE.md`. Provenance preambles required by `stop-research-gate.sh`.

Plans: `.claude/plans/8799d138-cert-stack-{00..08}` (overview, identity, upstream-oracle, claim-closure, bridge-snapshot, diagnostic-events, explain-path, answerability, consumer-migration) — eight-phase architectural spike.

## Recurring Patterns

1. **Citation extract + resolve + diff context** — 9 overlapping scripts. Same regex pack (`DOI_RE`, `PMID_RE`, `PMCID_RE`, `NCT_RE`), same resolvers (CrossRef, NCBI E-utils, S2), same context-comparison logic.
2. **Content-addressable IDs over identity v4** — `UUID5(namespace, canonical-slot-tuple)`. Used by claims, citation blocks, evidence spans, bridge certs.
3. **Append-only with annotation-not-edit** — self-reports, research memos, entity pages, todos. `pretool-append-only-guard.sh` is shared.
4. **Cert stack as composable verdicts** — each domain emits a typed cert; answerability composes via lattice meet. `CertifiableDependency` protocol is the seam.
5. **MCP per concern** — phenome (search + medical ontology + claims), genomics-consumer (typed views over WGS), research (papers + sources), paperclip (8M bio papers), biomedical (32 APIs).
6. **Entity dossiers with frontmatter-for-search** — tags/summary feed `surface_search`'s rank-0 elevation. Same shape regardless of entity kind.
7. **Fact tags `<!-- fact:name -->VALUE<!-- /fact -->`** in CLAUDE.md auto-synced from DB via `just sync-docs` — keeps docs from drifting.
8. **Schema-level invariants over caller discipline** — "if the DB can refuse a bad state, make it refuse." Explicit in CLAUDE.md "Design Stance: Correctness-Maximal."

## Build-Then-Undo Signals

- **Claims store** v3 → v4 breaking refactor (`16879bd7-claim-store-v3-breaking-refactor.md`, `2026-04-17-claims-v4-citation-block-refactor.md`, `claims/migrations/v3_to_v4.py`, commit `ec67242 Phase 1 migration + Phase 3 rebuild replay`). Then `c692eef Phase 1-3 close — apply cross-model review fixes`, `b99947a Phase 4b close`, `449f4ae Phase 4 follow-up close` — three rounds of cross-model review fixes on the same phase.
- **Cert stack** 8 plans + 8 "Plan NN close" commits (`48dc6a8`, `08d1b00`, `f27f36b`, `8afec7f`, `be94e87`, `87ee120`) — every plan needed critique-close rework.
- **Genomics bridge** v1 → v2 (`b51a1519-genomics-bridge-contract-emit.md` → `b51a1519-v2-...`), and `eba7145 Delete genomics_bridge.py — full cert-stack consumer migration` — wrappers replaced when cert stack landed.
- **Cert-stack productization** opened (`e150546 cert-stack-as-product spec`), closed (`d170c92 Defer cert-stack productization`), reopened (`a1e3c8a Cert-stack-as-product reopening — 90-day evidence gate post Roche/PathAI`).
- **Synthoria architecture flips** — EU entity decision flipped twice (`0afe507 → d0236fc`); Forschungsprämie scope corrected (`af8b738`); Phase 3 LoRA deleted (`dab065c`); 5-call test annotated as misattributed (`d5ce41b`).
- **CLAUDE.md drift** — `a91c79f CLAUDE.md audit — fix stale counts`, then the fact-tag system was built specifically to prevent this.
- **Citation audit verifiers proliferated** — `verify_citation_ids.py` first, then `audit_citations.py` (does more), then specialised `verify_{pgx,protocol,quantitative,variant}_claims.py`, then `validate_genomics_citations.py`. Each new verifier copies-pastes the regex/resolve core.
- **Subject-id silent zero-row bug** (`2059f1c`) — fixed via `resolve_subject_id` alias resolver. Class: identity-mismatch silently returning empty.
- **IL6R wrong PMIDs annotated inline** (`caf8867`) — append-only convention forced inline correction instead of edit.

## Candidates for Shared Infrastructure

**A. Citation-audit MCP / skill (very high value).** Five-plus repos (phenome, genomics, intel, agent-infra/research, research-mcp) all touch DOI/PMID/PMCID/NCT extraction + resolution + context-diff. Phenome alone has 9 partially-overlapping verifier scripts. Extract: `citation-audit` skill or `mcp__citations__{extract,resolve,verify_context,detect_drift}` with PMID-ceiling-check, CrossRef + NCBI + S2 backends, and standard "ID present but title/year/author mismatch" output schema. Subsumes `audit_citations.py`, `extract_citation_ids.py`, `verify_citation_ids.py`.

**B. Attestation/cert-stack as a portable schema.** `KGAttestation`, `AnswerabilityVerdict`, `CertifiableDependency`, `BridgeSnapshotCertificate`, content-addressed `certificate_id` with explicit `CANONICAL_HASH_EXCLUSIONS` — this is general "proof-carrying answer" infrastructure. Genomics already consumes via `genomics-consumer` MCP; intel could attest on financial filings the same way. Promote `bridge/kg.py:KGAttestation` + `answerability/certificate.py:AnswerabilityVerdict` to a shared `attest` package, or at minimum publish the schema (JSON-schema + Python dataclasses) in agent-infra.

**C. Entity-dossier convention** is already a skill (`entity-management`), but the **frontmatter contract is duplicated** across projects (search elevation in selve, phenome `surface_search`, intel's company files). Standardize the YAML keys (`title`, `tags`, `summary`, `last_reviewed`, `provenance`, `status`) and the elevation logic.

**D. Identity v4 module** — content-addressable IDs over canonical slot tuples (UUID5 + namespace constants). `phenome/claims/identity.py` is the reference impl; phenome cert-stack, genomics variant calls, and intel filing IDs all want this. Extract as `agent-infra/lib/identity` or a tiny library.

**E. Append-only guard + annotate-inline pattern.** Already partly shared (`~/Projects/skills/hooks/pretool-append-only-guard.sh`). The *convention* needs documenting in agent-infra: completed-but-superseded items get inline `**⚠ YYYY-MM-DD update:**` annotation, not deletion. Apply to research memos in genomics + intel.

**F. Research-memo contract auditor.** `audit_research_memo_contract.py` enforces required sections by heading. Generalize as a skill or hook in agent-infra; all three repos write research memos with similar structure (TL;DR, sources, claims, contradictions, decisions).

**G. Fact-tag injection (`<!-- fact:name -->VALUE<!-- /fact -->`) + `just sync-docs`** — clean solution to stale doc counts that recurs in every repo's CLAUDE.md. Extract the regex + a `sync-docs` template recipe.

**H. PDF→markdown is solved** by the existing `markitdown` skill; phenome still has bespoke `extract_lab_pdfs.py` / `extract_medical_pdfs.py` / `ingest_pdf.py`. Migration target, not a candidate — note in cross-project synthesis that these should be rewritten on top of `markitdown` + `research-mcp.fetch_paper`.

**I. Predicate vocabulary** in `claims/predicates.py` (56 predicates × 9 families) is bio-specific but the *pattern* of declared, frame-typed, inverse-linked, ontology-anchored predicates would extract to a shared `predicate-registry` schema. Intel could declare financial predicates (`acquires`, `disclosed_in`, `restated_from`) with the same shape.

**J. Self-attesting scripts pattern.** `audit_research_memo_contract.py` has its docstring tell you the invocations, glob, and fail-mode. Make this a convention so every script in `scripts/` is a runbook.

**Anti-candidates (already vetoed in agent-infra):** Knowledge-substrate MCP rebuilds (vetoed 2026-03-24), repo-tools MCP (retired 2026-03-20), PyMC for telemetry. Don't re-propose.

## Notes for synthesis model

- Phenome's defining bet is **correctness-maximal, breaking-refactors-by-default**, even on 2K-row personal data. This is opposite of intel's "ship-the-finding" stance and shapes everything below.
- The cert-stack is the most ambitious shared-infrastructure target but also the most opinionated. Productization was deferred once already (`d170c92`) and reopened (`a1e3c8a`). Don't over-promote it without re-checking that gate.
- Phenome already consumes the cross-project research-MCP (papers + sources cached at `~/Projects/research-mcp/data/`). The pattern works. Replicate it for citations + attestations.
- "Provenance tags added to memo — stop hook compliance" (`60f0a28`, `3af0fc5`, `b10509d`) appears 3× in the last 100 commits — the stop-research-gate hook works and the convention propagates.

<!-- knowledge-index
generated: 2026-05-11T04:08:28Z
hash: dc029c6482c9

cross_refs: docs/entities/genes/<gene>.md
table_claims: 3

end-knowledge-index -->
