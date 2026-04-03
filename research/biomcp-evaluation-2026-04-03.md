---
title: "BioMCP (GenomOncology) — Technical Evaluation vs biomedical-mcp"
date: 2026-04-03
---

# BioMCP (GenomOncology) — Technical Evaluation vs biomedical-mcp

**Question:** Should we adopt, integrate, or extract patterns from GenomOncology's BioMCP?
**Tier:** Standard | **Date:** 2026-04-03
**Ground truth:** We run `biomedical-mcp` (v0.5.0, FastMCP 3, Python, 82 tools across 18 domains, 30 APIs). Prior MCP landscape memo (`agent-tools-mcp-landscape-2026-03.md`) evaluated BioContextAI (20 stars, 14 DBs) but did not cover BioMCP.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | BioMCP replaced 36 MCP tools with a single CLI command, cutting context overhead by 95% | Blog post with before/after metrics | HIGH | [SOURCE: biomcp.org/blog/we-deleted-35-tools/] | VERIFIED |
| 2 | BioMCP covers ~40+ upstream data sources across 12 entity types | Entity list + data sources enumerated on biomcp.org | HIGH | [SOURCE: biomcp.org, github README] | VERIFIED |
| 3 | BioMCP achieves 86% pass rate on healthcare tasks (from 34% without skills) | SkillBench blog post, +51.9pp improvement | MEDIUM | [SOURCE: biomcp.org/blog/skillbench-biomcp-skills/] | VERIFIED (self-reported, no independent replication) |
| 4 | BioMCP exposes exactly 1 MCP tool (`biomcp`) + 1 resource (`biomcp://help`) | MCP server reference page | HIGH | [SOURCE: biomcp.org/reference/mcp-server/] | VERIFIED |
| 5 | BioMCP is Rust, single binary, MIT license, 480 stars, 9 contributors, 20 releases in March 2026 | GitHub API | HIGH | [SOURCE: github.com/genomoncology/biomcp] | VERIFIED |
| 6 | Our biomedical-mcp has 82 MCP tools across 18 domains, 30 APIs | Tool decorator count in source | HIGH | [DATA] | VERIFIED |
| 7 | BioMCP has oncology-specific sources (CIViC, OncoKB, cBioPortal, Cancer Genome Interpreter, AlphaGenome) not in our server | Entity source lists comparison | HIGH | [SOURCE: biomcp.org, our server.py] | VERIFIED |
| 8 | Our biomedical-mcp has sources not in BioMCP (ISBT blood groups, Orphanet rare disease, PanelApp gene panels, LitVar2, NPI provider registry, Ensembl sequences) | Source comparison | HIGH | [DATA] | VERIFIED |
| 9 | BioMCP's PGx coverage is CPIC + PharmGKB only | Entity source list | HIGH | [SOURCE: biomcp.org] | VERIFIED |
| 10 | Our PGx coverage includes PharmVar star alleles, OpenFDA labels, Open Targets pharmacogenetics | Domain file inspection | HIGH | [DATA] | VERIFIED |

---

## Architecture Comparison

### BioMCP (GenomOncology)

**Design philosophy: one tool, one grammar.**

BioMCP exposes a single MCP tool (`biomcp`) that accepts CLI-style subcommands:

```
biomcp search gene "BRCA1"
biomcp get variant "BRAF V600E" clinvar population
biomcp variant trials "BRAF V600E"
biomcp get pgx CYP2D6 recommendations
biomcp enrich BRCA1,TP53,EGFR
biomcp batch gene BRCA1,BRCA2,TP53
```

Key architecture decisions:
- **Rust single binary** — zero-dependency install via `uv tool install biomcp-cli` or curl
- **1 tool = ~800 tokens** context overhead (vs 16,600 tokens for their prior 36-tool version)
- **Auto-generated tool descriptions** from `list_reference.md` (descriptions never drift)
- **Minimal default responses** — compact output, agent iterates for detail
- **Cross-entity pivots** — `variant trials`, `gene articles`, etc. via helper commands
- **MCP + HTTP + stdio** — serves via `biomcp serve` (stdio) or `biomcp serve-http` (/mcp endpoint)
- **Read-only** — mutating commands (install, update, sync) blocked in MCP mode
- **rmcp 1.1.1** for MCP protocol implementation

### Our biomedical-mcp

**Design philosophy: domain-namespaced discrete tools.**

```
genetics_gene_info("BRCA1")
variants_clinvar("rs1234")
population_variant_frequency("chr17:41234...")
composite_variant_context("rs1234", gene_symbol="BRCA1")
```

Key architecture decisions:
- **Python + FastMCP 3** — mount() composition, namespace-prefixed
- **82 tools** across 18 namespaces = ~14-16K tokens context overhead [ESTIMATED]
- **SQLite cache** with 90-day TTL
- **Telemetry middleware** for usage tracking
- **Prompt templates** for structured workflows (variant_review, gene_dossier, pgx_review)
- **Composite tools** — `variant_context` and `gene_dossier` fan out to multiple APIs in parallel
- **3 dependencies** (FastMCP, httpx, tenacity) — lean

---

## Database Coverage Comparison

### Overlap (both systems cover)

| Domain | BioMCP Source | Our Source | Notes |
|--------|--------------|------------|-------|
| Gene annotation | MyGene.info | MyGene.info | Same upstream |
| Gene ontology | UniProt, QuickGO | Ensembl, HGNC | Different entry points, similar data |
| Variant annotation | MyVariant.info | MyVariant.info | Same upstream |
| ClinVar | via MyVariant.info | via MyVariant.info | Same |
| gnomAD | via MyVariant.info | Direct gnomAD API | Our = more granular (gene constraint endpoint) |
| Protein structure | UniProt, AlphaFold, PDB, InterPro, STRING | UniProt, AlphaFold, PDB, InterPro, STRING | Near-identical |
| Drug data | ChEMBL, OpenFDA | ChEMBL, OpenFDA | Same |
| Pathways | KEGG, Reactome | KEGG, Reactome | Same |
| Clinical trials | ClinicalTrials.gov v2 | ClinicalTrials.gov | Same |
| Disease-gene | OpenTargets, Monarch | OpenTargets, Monarch | Same |
| Phenotype | Monarch/HPO | HPO | Same |
| GWAS | GWAS Catalog | GWAS Catalog | Same |
| Gene expression | GTEx | GTEx | Same |

### Unique to BioMCP

| Source | Domain | Value |
|--------|--------|-------|
| CIViC | Oncology | Curated clinical interpretations for cancer variants |
| OncoKB | Oncology | Memorial Sloan Kettering cancer variant evidence levels |
| cBioPortal | Oncology | Cancer genomics data (somatic mutations, copy number) |
| Cancer Genome Interpreter | Oncology | Driver classification, resistance biomarkers |
| AlphaGenome | Structural | DeepMind structural predictions (gRPC integration) |
| PubTator3 | Literature | Biomedical NER over PubMed abstracts |
| Europe PMC / PMC OA | Literature | Full-text article access |
| Semantic Scholar | Literature | Citation-aware article search |
| NCI CTS API | Clinical trials | National Cancer Institute trial search |
| MyChem.info | Drug | Aggregated chemical/drug info |
| MyDisease.info | Disease | Aggregated disease info |
| DGIdb | Gene-drug | Drug-gene interaction database |
| ClinGen | Gene curation | Gene-disease validity (we have this too via curation domain) |
| Human Protein Atlas | Expression | Protein-level expression by tissue |
| ComplexPortal | Protein | Protein complex compositions |
| EMA | Drug | European Medicines Agency data |
| Drugs@FDA | Drug | FDA drug approvals |
| g:Profiler / Enrichr | Pathway | Gene set enrichment tools |

### Unique to Our Server

| Source | Domain | Value |
|--------|--------|-------|
| ISBT | Blood groups | Blood group systems, alleles, antigens, phenotypes |
| Orphanet | Rare disease | Rare disease epidemiology, natural history, phenotypes |
| PanelApp (Genomics England) | Gene panels | Curated diagnostic gene panels by condition |
| LitVar2 | Literature | Variant-specific literature mining |
| NPI Registry | Clinical | Healthcare provider lookup |
| Ensembl (direct) | Genetics | Sequences, cross-references, detailed gene models |
| HGNC | Nomenclature | Authoritative gene naming |
| PharmVar | PGx | Star allele definitions (CYP2D6*4, etc.) |
| ClinGen (direct) | Curation | Gene-disease validity + dosage sensitivity |
| ICD-10 | Clinical | Diagnosis code lookup |

---

## PGx Coverage Deep Dive

**BioMCP PGx:**
- CPIC guidelines (recommendations per gene/diplotype)
- PharmGKB clinical annotations
- Commands: `get pgx CYP2D6 recommendations`
- Cross-entity: `pgx drugs CYP2D6` (pivot to drug interactions)

**Our PGx (via `drugs_star_alleles`, `targets_pharmacogenetics`, `drugs_label`, `drugs_adverse_events` + pgx_review prompt):**
- PharmVar star allele definitions
- Open Targets pharmacogenetics data
- FDA drug labels (boxed warnings, clinical pharmacology sections)
- OpenFDA adverse events
- No direct CPIC or PharmGKB integration

**Gap analysis:** BioMCP has the critical PGx sources (CPIC + PharmGKB) that matter most for genotype-to-drug recommendations. Our server has PharmVar for allele definitions and OpenFDA for safety data, but lacks the recommendation layer. This is a real gap for our genomics pipeline.

---

## The "1 Tool vs 82 Tools" Design Question

BioMCP's most interesting contribution is architectural, not database-level. Their blog post provides hard numbers:

| Metric | 36 tools (before) | 1 tool (after) | Our 82 tools |
|--------|-------------------|----------------|--------------|
| Tool description tokens | ~16,600 | ~800 | ~14-16K [ESTIMATED] |
| Variant lookup output | ~1,400 tokens | ~350 tokens | Unknown |
| Round-trips per query | 3-4 | 1 | 1-3 |
| Speed per query | 2-5 seconds | 500ms-1s | Varies |

**Their argument:** Models handle hierarchical CLIs better than scattered function signatures. Context window savings compound across a conversation. Minimal default output lets the agent iterate on what it needs.

**Counter-argument for our approach:**
- FastMCP 3 mount() with namespaces is the Python equivalent of their command hierarchy
- Our composite tools (`variant_context`, `gene_dossier`) already aggregate multi-API calls into one round-trip
- Type-safe parameters with docstrings give the LLM more reliable calling than CLI string parsing
- Our prompt templates (variant_review, gene_dossier, pgx_review) serve a similar role to their "skills"
- 82 tools is larger than their pre-consolidation 36, but our namespace convention (`genetics_*`, `variants_*`) provides the same organizational signal

**The real question:** Is the context overhead of 82 tool descriptions (~14-16K tokens) causing measurable problems in our sessions? If not, the consolidation argument is academic. BioMCP was optimizing for Cursor-style editors with smaller context windows. Claude Code (Opus 4.6, 1M context) has headroom.

---

## Maturity Assessment

| Dimension | BioMCP | Score |
|-----------|--------|-------|
| Stars | 480 | Moderate traction |
| Contributors | 9 | Adequate |
| Release cadence | 10 releases in March 2026 alone (v0.8.11-v0.8.20) | Very active |
| Last push | 2026-04-03 (today) | Current |
| Open issues | 0 | Clean tracker |
| License | MIT | Permissible |
| Language | Rust (90.8%) | Performance advantage, harder to contribute |
| Dependencies | ~25 Rust crates (reqwest, tokio, axum, rmcp, tonic) | Moderate |
| Documentation | Dedicated site (biomcp.org), blog, examples repo | Good |
| Install | `uv tool install biomcp-cli`, curl, Docker | Easy |
| Test coverage | Unknown (not visible in README) | Cannot assess |

**GenomOncology context:** Cleveland-based precision oncology company. Not a hobby project. They sell enterprise genomics software. BioMCP is their OSS contribution / developer tool. This means: (a) oncology coverage reflects their core expertise, (b) maintenance is tied to company viability, (c) they have domain experts reviewing the data mappings.

---

## Integration Options Assessment

### Option A: Use BioMCP as upstream dependency
- **Mechanism:** Install `biomcp-cli`, call from our server or use alongside
- **Pros:** Get 18+ oncology/literature sources we don't have; maintained by domain experts; MIT license
- **Cons:** Rust binary = can't extend in Python; their single-tool MCP design is incompatible with our multi-tool architecture; running both = redundant context overhead for overlapping sources; no programmatic API (CLI-only interface means string parsing)
- **Verdict:** Not recommended. The CLI-only interface means our Python server can't compose with it at the API level. We'd have to shell out to `biomcp` and parse text output.

### Option B: Mount via FastMCP proxy/composition
- **Mechanism:** FastMCP 3's `from_client()` or stdio proxy to wrap BioMCP as a mounted sub-server
- **Pros:** Could expose BioMCP commands as additional tools in our namespace; FastMCP handles transport
- **Cons:** BioMCP exposes only 1 tool; wrapping 1 tool that accepts CLI strings defeats the purpose of typed tools; adds Rust binary dependency; output parsing required
- **Verdict:** Technically possible but architecturally awkward. We'd be wrapping a CLI tool that was designed to replace multiple tools, then re-exposing it as... one tool with string arguments. Loses type safety.

### Option C: Extract patterns
- **Pros:** Learn from their 95% context reduction, minimal output design, auto-generated descriptions, cross-entity pivots, and skill architecture
- **Cons:** Doesn't give us their data sources
- **Verdict:** Moderate value. Three patterns worth adopting:
  1. **Minimal default responses** — our tools should return compact summaries by default, with optional `detail` parameter for full data
  2. **Cross-entity helper commands** — our composite tools already do this, but we could add more (e.g., `variant_trials`, `gene_articles`)
  3. **Auto-generated tool descriptions** — generate INSTRUCTIONS block from actual tool signatures to prevent drift

### Option D: Cherry-pick their data sources into our server
- **Mechanism:** Add Python clients for CIViC, CPIC, PharmGKB, PubTator3, OncoKB (API-keyed) to our FastMCP server
- **Pros:** We maintain our typed Python tool architecture; get the sources we're missing; no Rust dependency; consistent with our design
- **Cons:** Implementation work per source; need to maintain the API integrations
- **Verdict:** Recommended for high-value sources. See recommendation below.

### Option E: Run both servers simultaneously
- **Mechanism:** Configure both `biomedical-mcp` and `biomcp` as MCP servers in `.mcp.json`
- **Pros:** Immediately get all BioMCP sources; no code changes
- **Cons:** ~15K additional context overhead from combined tool descriptions; massive overlap causes model confusion about which server to query; redundant calls to same upstream APIs (MyVariant, UniProt, etc.)
- **Verdict:** Not recommended. The overlap is too large (13+ shared data sources). Models would be confused about which tool to use for overlapping queries.

---

## Recommendation

**Option D (cherry-pick sources) + Option C (extract patterns).**

### Priority sources to add to our biomedical-mcp

| Source | Domain | Why | Effort [ESTIMATED] |
|--------|--------|-----|---------------------|
| CPIC API | PGx | Critical gap. CPIC guidelines = gold standard for genotype-to-drug recommendations. Direct JSON API available. | Low — REST API, well-documented |
| PharmGKB | PGx | Complements CPIC with clinical annotations, drug labels, variant-drug associations | Low — REST API |
| CIViC | Oncology | Open-source clinical interpretation of cancer variants. Free API. | Low — GraphQL API |
| PubTator3 | Literature | NER over PubMed for gene/variant/disease mentions. Free NCBI API. | Low — REST API |
| DGIdb | Gene-drug | Drug-gene interaction database. Useful for composite queries. | Low — REST API |

### Sources to skip (not worth the integration)

| Source | Why skip |
|--------|----------|
| OncoKB | Requires API key (academic license), oncology-specific, not our core use case |
| cBioPortal | Somatic cancer genomics; our focus is germline |
| AlphaGenome | Requires gRPC + protobuf; heavy integration for structural predictions we rarely need |
| Cancer Genome Interpreter | Oncology-only, narrow use case |

### Patterns to extract

1. **Compact default output with progressive disclosure** — Add an optional `summary: bool = True` parameter to verbose tools. When True, return key fields only. Let agent request full detail.
2. **Context overhead audit** — Measure our actual tool description token count. If >12K, consider consolidating rarely-used tools into composite endpoints.
3. **Auto-generated INSTRUCTIONS** — Generate the server INSTRUCTIONS block from tool docstrings at server startup, so descriptions never drift from implementations.

---

## What's Uncertain

1. **BioMCP's actual accuracy on PGx workflows** — the 86% SkillBench number is self-reported. No independent benchmark. The "90% accuracy with zero hallucinations" claim on biomedical paper validation is also self-reported. [UNVERIFIED]
2. **BioMCP's CPIC/PharmGKB coverage depth** — do they just hit the API, or do they add interpretation logic? Their `get pgx CYP2D6 recommendations` output format is unknown.
3. **Whether 82 tools actually causes context overhead problems in our setup** — we haven't measured this. If Opus 4.6 with 1M context handles it fine, the consolidation case weakens.
4. **GenomOncology's long-term OSS commitment** — they're a commercial company. BioMCP could become a loss leader that gets deprioritized.

---

## Search Log

| Query | Tool | Hits | Useful? |
|-------|------|------|---------|
| "GenomOncology BioMCP Rust biomedical MCP server" | Exa | 8 | Yes — repo, blog posts, press release |
| "genomoncology biomcp github" | Brave | 10 | Yes — releases, examples repo, registry listings |
| GitHub API repos/genomoncology/biomcp | gh API | 1 | Yes — stars, forks, push date |
| GitHub API contributors + releases | gh API | 2 | Yes — 9 contributors, release cadence |
| biomcp.org blog posts | WebFetch | 2 | Yes — architecture decisions, SkillBench |
| biomcp.org reference | WebFetch | 1 | Yes — exact MCP contract |
| biomcp.org home page | WebFetch | 1 | Yes — entity types + data sources |
| GitHub Cargo.toml | WebFetch | 1 | Yes — Rust dependencies |
| Our server.py | Read | 1 | Yes — our architecture baseline |
| Our tool count | grep | 1 | Yes — 82 tools confirmed |
| Prior MCP landscape memo | Read | 1 | Yes — BioContextAI comparison context |

<!-- knowledge-index
generated: 2026-04-03T19:27:54Z
hash: 7288fd584856

title: BioMCP (GenomOncology) — Technical Evaluation vs biomedical-mcp
table_claims: 10

end-knowledge-index -->
