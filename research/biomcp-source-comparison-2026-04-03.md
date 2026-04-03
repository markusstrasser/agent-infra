---
title: "BioMCP vs biomedical-mcp: Source Code Comparison"
date: 2026-04-03
topics: [biomcp, biomedical-mcp, pharmacogenomics, variant-annotation, somatic]
confidence: high
scope: head-to-head source comparison
biomcp_commit: HEAD (cloned 2026-04-03)
biomedical_mcp_path: ~/Projects/biomedical-mcp/
---

# BioMCP vs biomedical-mcp: Source Code Comparison

## Scale

| Metric | BioMCP | biomedical-mcp |
|--------|--------|----------------|
| Language | Rust (async tokio) | Python (sync httpx) |
| Lines of source | ~99,000 | ~5,800 |
| API source clients | 48 files | 35 files |
| Entity types | 12 (gene, variant, drug, disease, trial, article, pathway, protein, pgx, adverse_event, study, discover) | 18 domains via FastMCP mount() |
| Tools exposed | 1 MCP tool (`biomcp` shell command) | ~82 individual MCP tools |
| Rendering | Jinja2 (.md.j2 templates, 28 templates) | Raw JSON dicts |
| CLI | Full CLI with `get`, `search`, `batch`, `discover`, `enrich` | MCP-only, no CLI |

## 1. Where BioMCP Is Genuinely Better

### 1.1 PGx: CPIC + PharmGKB Integration (Major Gap)

**BioMCP** has a complete PGx entity (`src/entities/pgx.rs`, 865 lines) that:
- Queries CPIC `pair_view` for gene-drug interactions with CPIC levels (A/B/C/D)
- Fetches `recommendation_view` for phenotype-specific clinical recommendations (e.g., "CYP2D6 Poor Metabolizer + codeine = Avoid codeine, classification=Strong")
- Pulls `population_frequency_view` for allele frequencies by population group with subject counts
- Retrieves `guideline_summary_view` for CPIC guideline metadata with URLs
- Enriches with PharmGKB clinical + guideline + label annotations via `api.pharmgkb.org/v1`, with a 10-second timeout so PharmGKB failures don't block CPIC results (`pgx.rs:342-358`)
- Sorts interactions by CPIC level rank (A=0, B=1, C=2, D=3) so the highest-evidence pairs surface first (`pgx.rs:241-246`)
- Auto-detects whether query is a gene or drug via `is_likely_gene()` heuristic, tries gene lookup first, falls back to drug (`pgx.rs:208-230`)
- Deduplicates allele frequency rows across populations (`pgx.rs:695-726`)

The output for `biomcp get pgx CYP2D6 recommendations` includes: drug name, phenotype (e.g., "Poor Metabolizer"), activity score (e.g., "0.0"), clinical implication, specific recommendation text, classification strength, population scope, and guideline URL.

**Our biomedical-mcp** has only `drugs_star_alleles` (PharmVar star allele definitions) and `targets_pharmacogenetics` (Open Targets PGx data). No CPIC integration at all. No phenotype-to-recommendation mapping. No population frequency data for PGx alleles. This is the largest functional gap.

**Concrete steal:** Add CPIC API client (`api.cpicpgx.org/v1`) with `pair_view`, `recommendation_view`, `population_frequency_view`, and `guideline_summary_view` endpoints. Add PharmGKB annotation client. Create a composite `pgx_lookup` tool that combines both.

### 1.2 Variant Enrichment: Multi-Source Somatic Pipeline (Major Gap)

BioMCP's variant entity (`src/entities/variant.rs`, 2534 lines) does section-based enrichment with these sources we lack:

**OncoKB** (`src/sources/oncokb.rs`): Requires `ONCOKB_TOKEN` env var. Annotates protein changes with oncogenic classification, highest sensitive/resistance level, mutation effect, and therapy implications. Has `annotate_by_protein_change` and `annotate_best_effort` (tries byProteinChange first, falls back to byHGVSg). Creates a `VariantOncoKbResult` with gene, alteration, oncogenic status, level, effect, and structured `TreatmentImplication` entries (level + drugs + cancer_type + note).

**CIViC** (`src/sources/civic.rs`): GraphQL client querying `evidenceItems` and `assertions` by molecular profile name, therapy, or disease. Fetches accepted evidence with type, level, significance, disease, therapies, and source citations. Also queries assertions with AMP level.

**cBioPortal** (`src/sources/cbioportal.rs`, `cbioportal_study.rs`): Mutation frequency across cancer types. Has a full `study` entity (`src/entities/study.rs`, 1458 lines) for querying cBioPortal datasets with filter/cohort/survival/co-occurrence/mutation-comparison capabilities.

**AlphaGenome** (`src/sources/alphagenome.rs`): gRPC client for variant effect prediction (expression log fold change, splice score, chromatin accessibility score, top affected gene). Resolves Ensembl gene IDs to symbols via MyGene. This is the Google DeepMind AlphaGenome model -- a genuinely novel prediction source.

**Cancer Genome Interpreter (CGI)**: Extracted from MyVariant.info `cgi` field. Drug associations with association type, tumor type, evidence level, and source.

**COSMIC context**: Mutation frequency, tumor site, mutation nucleotide from MyVariant.info `cosmic` field.

**GWAS Catalog**: Direct integration via `src/sources/gwas.rs` with rsID/trait/region search, full association details (p-value, effect size, confidence interval, risk allele frequency, study accession, PMID, author, sample description).

The variant `get` function fetches the base variant from MyVariant.info, then conditionally enriches with each section. Each enrichment has an 8-second timeout (`OPTIONAL_ENRICHMENT_TIMEOUT`) so failures don't block the response -- it just omits that section with a warning.

**Our biomedical-mcp** has `composite_variant_context` which calls gnomAD + MyVariant + GTEx + PanelApp + LitVar concurrently, but lacks OncoKB, CIViC, cBioPortal, AlphaGenome, CGI, COSMIC context, and GWAS enrichment.

**Concrete steals:**
- OncoKB client (requires API key, worth adding)
- CIViC GraphQL client (free, no key needed)
- cBioPortal mutation frequency (free REST API)
- AlphaGenome gRPC (if gRPC overhead is acceptable -- user confirmed it is)
- CGI associations from MyVariant.info `cgi` field (already in our MyVariant data, just not extracted)
- GWAS enrichment from GWAS Catalog (we have `gwas_variant_associations` but don't integrate into variant context)

### 1.3 Variant Input Parsing (Medium Value)

BioMCP's `classify_variant_input()` / `parse_variant_id()` (`variant.rs:524-589`) handles:
- rsIDs: `rs113488022` (case-insensitive)
- HGVS genomic: `chr7:g.140453136A>T`
- Gene + protein change: `BRAF V600E`, `EGFR L858R`, `KRAS G12C`
- Long-form HGVS: `BRAF p.Val600Glu` -> normalizes to `V600E`
- Prefixed short: `BRAF p.V600E` -> normalizes to `V600E`
- Gene + residue alias: `PTPN22 620W` -> suggests search
- Protein-only: `R620W`, `p.Val600Glu` -> suggests search with correct command

When a shorthand can't be directly looked up, it returns a `VariantGuidance` with `next_commands` showing exactly what to run. The error messages are actionable:
```
"search-only shorthand...try: biomcp search variant --hgvsp R620W --limit 10"
```

**Our biomedical-mcp** accepts rsIDs, HGVS, and dbSNP-style IDs via `variants_lookup`, but has no normalization layer. If someone passes "BRAF V600E", it just fails.

**Concrete steal:** Add a `normalize_variant_input()` function that handles gene+protein notation and suggests the right tool call on failure.

### 1.4 `discover` / `search all` -- Intent-Aware Routing (Medium Value)

`biomcp discover "<free text>"` (`src/entities/discover.rs`, ~500 lines) does:
- Classifies intent: TrialSearch, DrugSafety, TreatmentSearch, SymptomSearch, GeneDiseaseOrientation, GeneFunction, General
- Runs concept resolution against OLS4, UMLS, and MedlinePlus in parallel (with 4s/2.5s/0.8s timeouts)
- Returns structured concepts with types (Gene/Drug/Disease/Symptom/Pathway/Variant), cross-references, match tier (Exact/Prefix/Contains/Weak), confidence level
- Generates `next_commands` -- executable CLI commands for the next step
- Includes a `PlainLanguageTopic` from MedlinePlus for patient-facing context

`biomcp search all --gene BRAF --disease melanoma` (`src/cli/search_all.rs`) fans out to multiple entity searches in parallel with per-section timeouts (12s default, 20s for articles), returns unified results with counts, links, and suggested next commands.

**Our biomedical-mcp** has no discovery/routing layer. The agent must already know which tool to call. This is genuinely useful for exploratory queries.

### 1.5 Structured Markdown Output with Section Source Tracking (Medium Value)

BioMCP renders every entity as structured Markdown via Jinja2 templates (`templates/*.md.j2`, 28 templates). Each section is annotated with its data source:
- `render/provenance.rs` (1107 lines) tracks which sections are populated and their data sources (e.g., "Identity: MyVariant.info / ClinVar", "CIViC: CIViC", "Population: gnomAD via MyVariant.info")
- Templates use table formatting for structured data (predictions, drug associations, GWAS)
- Numeric values get custom formatters: `af` for allele frequencies, `pval` for p-values, `score` for general scores

**Our biomedical-mcp** returns raw JSON dicts. The LLM has to interpret the JSON structure every time. BioMCP's Markdown output is more token-efficient for the LLM consumer.

**Nuance:** The single-tool MCP architecture (shell command execution) means BioMCP can render before sending to the LLM. Our multi-tool architecture returns structured data that FastMCP serializes as JSON. We could add Markdown formatting inside tool responses without changing architecture.

### 1.6 HTTP Infrastructure (Medium Value)

**Caching:** BioMCP uses `http-cache-reqwest` with `CACacheManager` -- HTTP-native disk caching that respects Cache-Control headers, with `max-stale=86400` default (24h stale tolerance). Cache mode configurable via `BIOMCP_CACHE_MODE=infinite|off|default`. Authenticated requests automatically skip cache (`CacheMode::NoStore`). Has cache migration from legacy format and a full `cache` CLI for management.

**Our caching:** SQLite-based key-value cache with configurable TTL per domain (1/7/30 days). Simpler but functional. Doesn't respect HTTP cache headers.

**Rate limiting:** BioMCP has a proper middleware-based rate limiter (`src/sources/rate_limit.rs`, 418 lines) with per-API policies:
- Per-URL-prefix policies: PubTator (100ms with API key, 334ms without), Semantic Scholar (1s with key, 2s without), OpenTargets (500ms), CPIC (250ms), PharmGKB (500ms), KEGG (334ms)
- Default 100ms for unknown hosts
- Longest-prefix matching for same-host APIs
- Async `sleep_until` for precise timing

**Our rate limiting:** Simple per-host `time.sleep()` with configurable `max_rate` per domain. No API-key-aware adjustment, no prefix matching.

**Retries:** BioMCP uses `reqwest-retry` with exponential backoff (3 retries, DEBUG log level). Plus a custom `retry_send` for streaming requests that honors `Retry-After` headers. Response body size limited to 8MB.

**Our retries:** tenacity with 3 attempts, exponential backoff (2-15s), retries on 429/500/502/503/504 and connection/timeout errors.

Both are adequate, but BioMCP's is more sophisticated in rate limiting.

### 1.7 Error Types (Small Value)

BioMCP's `BioMcpError` (`src/error.rs`) has specific variants:
- `NotFound { entity, id, suggestion }` -- always includes an actionable suggestion
- `ApiKeyRequired { api, env_var, docs_url }` -- tells user exactly what to set
- `SourceUnavailable { source_name, reason, suggestion }` -- graceful degradation with alternatives
- Separate `Api` / `ApiJson` / `Http` / `HttpMiddleware` for debugging

The error messages include executable commands:
```
gene 'BRAF' not found.
Try searching: biomcp search gene -q BRAF
```

**Our biomedical-mcp** returns `{"error": "Gene not found: BRAF"}`. No suggestions, no structured error types.

### 1.8 Sources We Lack Entirely

| Source | BioMCP file | What it provides | Worth adding? |
|--------|-------------|------------------|---------------|
| OncoKB | `oncokb.rs` | Somatic oncogenicity, therapy levels | Yes (with API key) |
| CIViC | `civic.rs` | Clinical evidence for variants, genes, drugs | Yes (free GraphQL) |
| cBioPortal | `cbioportal.rs`, `cbioportal_study.rs`, `cbioportal_download.rs` | Cancer mutation frequencies, study-level data | Yes (free REST) |
| AlphaGenome | `alphagenome.rs` | Expression/splice/chromatin variant effect prediction | Yes (gRPC, user approves) |
| DGIdb | `dgidb.rs` | Drug-gene interactions, druggability, tractability | Yes |
| DisGeNET | `disgenet.rs` | Gene-disease associations with scores | Yes (free) |
| EMA | `ema.rs` | EU drug regulatory info, safety, shortages | Nice-to-have |
| MedlinePlus | `medlineplus.rs` | Plain-language health topics | Nice-to-have |
| ComplexPortal | `complexportal.rs` | Protein complex membership | Nice-to-have |
| HPA | `hpa.rs` | Human Protein Atlas tissue/subcellular localization | Yes |
| Enrichr | `enrichr.rs` | Gene set enrichment analysis | Yes |
| g:Profiler | `gprofiler.rs` | Pathway/GO enrichment | Already have via Reactome |
| WikiPathways | `wikipathways.rs` | Community-curated pathways | Nice-to-have |
| Semantic Scholar | `semantic_scholar.rs` | Citation counts, TLDRs, recommendations | Already have via research-mcp |
| NCBI ID Converter | `ncbi_idconv.rs` | PMID/PMCID/DOI conversion | Nice-to-have |
| MyChem | `mychem.rs` | Drug-level BioThings aggregation | Yes |
| MyDisease | `mydisease.rs` | Disease-level BioThings aggregation | Yes |
| OLS4 | `ols4.rs` | Ontology Lookup Service concept resolution | Nice-to-have |
| UMLS | `umls.rs` | Concept normalization and cross-referencing | Nice-to-have |
| NCI CTS | `nci_cts.rs` | NCI clinical trial search | Nice-to-have (already have CT.gov) |

## 2. Where We Are Better or Equivalent

### 2.1 Tool Granularity (We're Better)

Our 82-tool architecture with namespace prefixing (`genetics_gene_info`, `variants_lookup`, `population_variant_frequency`) lets the LLM call exactly the tool it needs. BioMCP exposes a single `biomcp` MCP tool that takes a shell command string. The LLM has to construct the right CLI command, which is less discoverable and more error-prone.

Our FastMCP mount() composition with typed parameters per tool is architecturally superior for MCP. BioMCP's shell-command approach works around MCP's design rather than with it.

### 2.2 Germline / Personal Genomics Coverage (We're Better)

We have stronger coverage for:
- **ISBT blood groups** (`bloodgroups.py`) -- BioMCP has no blood group coverage
- **Orphanet rare diseases** (`rare_disease.py`) -- BioMCP has no Orphanet integration
- **ClinGen gene-disease validity + dosage** (`curation.py`) -- BioMCP has `clingen.rs` but only for gene validity, not dosage sensitivity
- **PharmVar star alleles** (`drugs.py:star_alleles`) -- BioMCP has no PharmVar

### 2.3 Evidence Grading in Provenance (We're Better)

Our `provenance.py` includes evidence grade tags (A1=systematic review through F6=LLM-generated). BioMCP's provenance system (`render/provenance.rs`) tracks data sources per section but doesn't grade evidence quality.

### 2.4 Composite Tools (Equivalent, Different Design)

Our `composite_variant_context` and `composite_gene_dossier` fan out to 6-8 APIs concurrently and return unified results. BioMCP does the same via its entity `get` functions with section-based enrichment. The approaches are equivalent in design; they differ in which sources are called.

## 3. Prioritized Recommendations

Ordered by clinical utility and implementation difficulty:

### Must-Add (High Clinical Value)

1. **CPIC PGx client** -- `api.cpicpgx.org/v1` with pair_view, recommendation_view, population_frequency_view, guideline_summary_view. Integrate with PharmGKB annotations. This is the #1 gap. (~300 lines)

2. **CIViC GraphQL client** -- Query evidence items and assertions by molecular profile, therapy, disease. No API key needed. Integrate into `composite_variant_context`. (~200 lines)

3. **OncoKB client** -- `annotate/mutations/byProteinChange` and `annotate/mutations/byHGVSg`. Requires `ONCOKB_TOKEN`. Returns oncogenic classification, therapy levels. (~150 lines)

4. **cBioPortal mutation frequency** -- `cbioportal.org/api` mutation summary by gene. No key needed. Cancer type frequency table. (~150 lines)

### Should-Add (Medium Clinical Value)

5. **Variant input normalization** -- Handle "BRAF V600E" and "p.Val600Glu" input formats. Port BioMCP's regex-based parser. (~100 lines)

6. **CGI drug associations** -- Already in MyVariant.info response data under `cgi` field. Just extract and structure it. (~50 lines)

7. **COSMIC context** -- Already in MyVariant.info response under `cosmic` field. Extract mutation frequency, tumor site. (~50 lines)

8. **DGIdb** -- Drug-gene interactions with druggability/tractability data. Free API. (~150 lines)

9. **DisGeNET** -- Gene-disease associations with scores and publication counts. Free API. (~100 lines)

10. **Enrichr** -- Single-gene set enrichment analysis. Free API. (~100 lines)

### Nice-to-Have

11. **AlphaGenome gRPC** -- Novel but requires protobuf compilation. User confirmed gRPC is acceptable.

12. **HPA** -- Tissue/subcellular localization. Complements GTEx expression data.

13. **Markdown output formatting** -- Add formatted markdown rendering inside tool responses for token efficiency.

14. **Discovery/routing layer** -- `discover` equivalent for exploratory queries where the user doesn't know what entity type they're looking for.

15. **Actionable error messages** -- Return suggested tool calls in error responses.

## 4. What NOT to Copy

- **Single-tool MCP architecture** -- Their shell-command approach is a workaround. Our multi-tool design is correct for MCP.
- **CLI infrastructure** -- We don't need a CLI; MCP is the interface.
- **cBioPortal study entity** -- The full study analysis pipeline (filter, cohort, survival, co-occurrence) is substantial engineering (~1500 lines) for a narrow use case. Start with mutation frequency only.
- **Template rendering engine** -- Minijinja + 28 templates is heavy. Adding Markdown directly in tool responses is lighter.
- **Benchmark framework** -- Their `cli/benchmark/` is for evaluating LLM agent performance. Different purpose from our needs.

## 5. Architecture Observations

BioMCP separates cleanly into layers:
- `sources/` -- raw API clients, HTTP utilities, rate limiting
- `entities/` -- domain logic, enrichment orchestration
- `transform/` -- raw API response -> entity model mapping
- `render/` -- entity model -> Markdown/JSON output
- `mcp/` -- thin shell that routes CLI commands to entities

This is a good pattern. Our codebase mixes API client logic with domain formatting in each client class. A transform layer between raw API data and tool output would improve maintainability, especially as we add more sources.

BioMCP's optional enrichment timeout pattern (`tokio::time::timeout(OPTIONAL_ENRICHMENT_TIMEOUT, fut)`) is worth adopting. Each section enrichment is isolated -- if CIViC is slow, you still get the base variant + all other enrichments. We should do the same in `composite_variant_context` (partially done but not consistently).

<!-- knowledge-index
generated: 2026-04-03T19:39:23Z
hash: c1ff2b6a8656

title: BioMCP vs biomedical-mcp: Source Code Comparison

end-knowledge-index -->
