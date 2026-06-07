---
title: "BioMCP / FastMCP Upstream Delta — 2026-06-07"
date: 2026-06-07
topics: [biomcp, fastmcp, mcp-spec, biomedical-mcp, pharmacogenomics, oncology]
confidence: high
scope: delta since 2026-04-03 — what changed upstream and what's worth porting
prior_memos:
  - biomcp-evaluation-2026-04-03.md
  - biomcp-source-comparison-2026-04-03.md
  - fastmcp3-integration-plan.md
---

# BioMCP / FastMCP Upstream Delta — 2026-06-07

**Delta period:** 2026-04-03 → 2026-06-07 (65 days)
**Ground truth:** Our server is `~/Projects/biomedical-mcp/` v0.5.0, FastMCP 3.4 (pinned `>=3.4,<4.0`), 81 tools, 18 domains, 30 APIs. We run BioMCP alongside as a second MCP server in genomics + selve `.mcp.json`.

---

## Claims Table

| # | Claim | Version/Date | Source | Port-worthiness |
|---|-------|-------------|--------|-----------------|
| 1 | BioMCP added `diagnostic` entity backed by GTR (Genetic Testing Registry) + WHO Prequalified IVD + FDA 510(k)/PMA overlays | v0.8.22, 2026-05-01 | GitHub release page (direct fetch) | **HIGH** — GTR diagnostic coverage is a real gap in our server |
| 2 | BioMCP added DDInter drug-drug interaction workflows (`drug interactions <name>`) via local DDInter bundle | v0.8.22, 2026-05-01 | GitHub release page | **HIGH** — we have zero drug-drug interaction coverage; complements our PGx work |
| 3 | BioMCP added CDC CVX/MVX vaccine identity bridge + CDC WONDER VAERS as aggregate vaccine adverse-event source | v0.8.22, 2026-05-01 | GitHub release page | **MED** — relevant if we serve patient-facing genomic reports; low-maintenance add |
| 4 | BioMCP added EMA regulatory region support (`--region eu`) with local EMA human-medicine feeds, synced via `biomcp ema sync` | v0.8.21, 2026-04-16 | GitHub release page | **MED** — we have no EMA coverage; EU regulatory important for EU clinical use |
| 5 | BioMCP added article date-range filtering (`--date-from`/`--date-to`) | v0.8.21, 2026-04-16 | GitHub release page | **LOW** — we use research-mcp for literature; won't port |
| 6 | BioMCP added `biomcp suggest <question>` offline routing for workflow guidance without live tool calls | v0.8.22, 2026-05-01 | GitHub release page | **LOW** — their CLI feature; no MCP-side value for us |
| 7 | BioMCP reached 522 stars (up from 480 on 2026-04-03) | 2026-06-07 | GitHub README fetch | **INFO** — still actively maintained; traction increasing |
| 8 | BioMCP entity count grew from 12 to 13 (new: `diagnostic`) | v0.8.22, 2026-06-07 | GitHub README | **INFO** |
| 9 | No BioMCP v0.9 or v1.0 release exists yet; latest is v0.8.22 | 2026-06-07 | GitHub releases page | **INFO** — no architectural break |
| 10 | FastMCP latest is 3.4.2 (2026-06-06); no 4.0 exists; our pin `>=3.4,<4.0` is safe | 2026-06-06 | PyPI + gofastmcp.com changelog | **VERIFIED** — no upgrade pressure |
| 11 | FastMCP 3.4.0 (2026-06-03) introduces breaking proxy change: proxies now forward `initialize` upstream, failing loudly when backend misconfigured | v3.4.0, 2026-06-03 | gofastmcp.com changelog | **LOW** — we don't use ProxyProvider; not affected |
| 12 | FastMCP 3.4.0 introduces `fastmcp-remote`, a standalone bridge for connecting stdio-only hosts to HTTP MCP servers | v3.4.0, 2026-06-03 | gofastmcp.com changelog | **MED** — interesting if we want to expose our server remotely; currently all stdio |
| 13 | FastMCP 3.3.0 (2026-05-15) launches `fastmcp-slim` for lightweight client-only installs without Starlette/Uvicorn | v3.3.0, 2026-05-15 | gofastmcp.com changelog | **LOW** — we're a server, not a client |
| 14 | FastMCP 3.2.4 (2026-04-14): BREAKING — background tasks now scoped to auth context, not MCP session | v3.2.4, 2026-04-14 | gofastmcp.com changelog | **LOW** — we don't use background tasks |
| 15 | FastMCP 3.2.4 auto-extracts parameter descriptions from docstrings | v3.2.4, 2026-04-14 | gofastmcp.com changelog | **MED** — free improvement to our tool descriptions if we upgrade to 3.4 |
| 16 | FastMCP 3.2.0 (2026-03-30) introduced FastMCPApp + 5 built-in UI providers (FileUpload, Approval, Choice, FormInput, GenerativeUI) | v3.2.0, 2026-03-30 | gofastmcp.com changelog | **LOW** — needs MCP Apps client support; Claude Code doesn't support yet |
| 17 | MCP 2026-07-28 RC removes protocol-level sessions: `initialize`/`initialized` handshake gone, `Mcp-Session-Id` gone; capabilities travel in `_meta` per request | RC locked 2026-05-21; ships 2026-07-28 | blog.modelcontextprotocol.io (direct fetch) | **HIGH** — potential breaking change for FastMCP SDK; FastMCP (Tier 1) will ship support within 10-week window before July 28 |
| 18 | MCP RC deprecates Roots, Sampling, and Logging (12-month window for removal) | RC 2026-05-21 | blog.modelcontextprotocol.io | **LOW** — we don't use any of these |
| 19 | MCP RC adds JSON Schema 2020-12 support for tool schemas: `oneOf`, `anyOf`, `allOf`, `$ref` now valid | RC 2026-05-21 | blog.modelcontextprotocol.io | **MED** — enables richer parameter unions in tool definitions; useful for variant input normalization tool |
| 20 | MCP RC adds `ttlMs`/`cacheScope` caching headers on list/read results | RC 2026-05-21 | blog.modelcontextprotocol.io | **MED** — could let clients cache our tool list; reduces handshake overhead |
| 21 | MCP RC SSE deprecated: servers now return `InputRequiredResult` with embedded prompt for interactive flows | RC 2026-05-21 | blog.modelcontextprotocol.io | **LOW** — we have no interactive/streaming tools |
| 22 | BioContextAI (was 20 stars in March 2026 memo) now has 24 stars; latest release v0.2.1 Dec 2025; covers 14 DBs | 2026-06-07 | GitHub fetch | **LOW** — minimal growth; not worth depending on |
| 23 | OpenPGx (open-pgx/openpgx) emerged as standalone pharmacogenomics MCP server: 9 tools, 118 studies, 109 genes, 219 medications, 19 disease risk conditions; TypeScript; 10 stars | 2026-06-07 | GitHub fetch | **LOW as dep** — tiny, 10 stars, no institutional backing; useful as inspiration for standalone PGx tool design |
| 24 | OpenClaw Medical Skills (2.6k stars) is a skills plugin library (869 skills, 40+ DBs) for OpenClaw/NanoClaw — NOT an MCP server; covers COSMIC, GWAS, GTEx, gnomAD, Orphanet etc. | 2026-06-07 | GitHub fetch | **LOW as dep** — skill format incompatible with our architecture; design patterns worth reading |
| 25 | GenomOncology's OncoMCP is a commercial HIPAA-compliant enterprise extension of BioMCP with EHR integration, real-time trial matching, 15K+ trials KB, patient matching | 2026-06-07 | Search + PR Newswire | **INFO** — upstream commitment signal; OSS BioMCP is their developer funnel |
| 26 | BioContextAI published in Nature Biotechnology as community hub for agentic biomedical systems | Unverified date | Search result (skywork.ai summary) | **UNVERIFIED** — could not confirm via primary source; treat as LOW confidence |

---

## Section 1: BioMCP Delta (GenomOncology, v0.8.21 → v0.8.22)

### 1.1 New Entity: `diagnostic`

BioMCP v0.8.22 adds a 13th entity type: `diagnostic`, backed by:
- **GTR** (NCBI Genetic Testing Registry) — searchable/retrievable via `biomcp search diagnostic` / `biomcp get diagnostic`
- **WHO Prequalified IVD** — infectious-disease in-vitro diagnostic products (synced locally via `biomcp who-ivd sync`)
- **FDA 510(k) and PMA regulatory overlays** — device regulatory status on diagnostic records
- **Diagnostic pivots** — gene and disease cards now show hints for relevant diagnostic tests

**Gap assessment:** Our `biomedical-mcp` has no GTR coverage whatsoever. GTR is the authoritative registry of 100K+ genetic tests with method, analyte, purpose, and ordering lab info. For a genomics-adjacent server this is notable. FDA 510(k) is covered in some specialty servers but we have none.

**Port-worthiness: HIGH.** GTR is a free NCBI REST API (`eutils.ncbi.nlm.nih.gov/entrez/eutils/` with `db=gtr`). Implementation is ~150 lines. The FDA 510(k) regulatory overlay is available via our existing OpenFDA client with a new endpoint (`device/510k`). ClinVar already links to GTR for many variants. Worth adding as `diagnostics_genetic_tests` in a new `diagnostics` domain.

### 1.2 New Source: DDInter Drug-Drug Interactions

BioMCP v0.8.22 adds DDInter as a local-bundle source for drug-drug interaction (DDI) queries via `biomcp drug interactions <name>`.

**DDInter** (ddinter.scbdd.com) is a curated DDI database from CNCB/Beijing with 240K+ interaction records covering 1.8K drugs, annotated with mechanism (PK/PD), severity (major/moderate/minor), and clinical management. BioMCP uses a local bundle (synced offline), not API calls.

**Gap assessment:** We have zero DDI coverage. Our `drugs_adverse_events` covers individual drug safety but not drug-drug interaction pairs. This is a genuine clinical gap — PGx genotype recommendations need DDI context to be actionable.

**Port-worthiness: HIGH.** DDInter's web API is available (ddinter.scbdd.com/api/), or we could sync a local SQLite cache from their downloadable data dumps. ~200 lines for a `drugs_drug_interactions` tool. Aligns with our existing `drugs` domain. Check license: DDInter is free for academic/non-commercial use.

### 1.3 New Source: EMA Regulatory Data (v0.8.21)

BioMCP v0.8.21 adds EMA (European Medicines Agency) human-medicine feeds, synced locally via `biomcp ema sync`, surfacing EU regulatory status in drug search and retrieval.

**Port-worthiness: MED.** EMA publishes machine-readable product data at the European Medicines Web API. Adding `drugs_ema_regulatory` alongside our existing `drugs_fda_approval` (Drugs@FDA) would give EU-facing regulatory parity. ~150 lines. EMA API is at `www.ema.europa.eu/en/medicines/download-medicine-data`.

### 1.4 New Behavior: `clinical_features` via MedlinePlus + HPO

v0.8.22 adds a disease card output section (`clinical_features`) backed by MedlinePlus summaries with HPO phenotype mapping. This gives plain-language clinical descriptions linked to structured phenotype terms.

**Port-worthiness: LOW.** We have Monarch/HPO integration already. MedlinePlus is consumer-oriented. Not a priority.

### 1.5 BioMCP "Skills" System

BioMCP ships validated skill markdown files (per `biomcp.org/how-to/skill-validation/`). Each skill has:
- Quick Check (command path health)
- Full Workflow (step-by-step intent)
- Validation Checklist (expected outcomes: command fidelity, evidence traceability, clinical relevance, constraint awareness, reproducibility)

This is structurally similar to our `~/Projects/skills/` system. **No SkillBench numbers are publicly posted on the validation page** — the prior 86% claim from the April memo came from the original SkillBench blog post and appears not to have been updated with fresh numbers in this period.

**Port-worthiness: LOW.** We already have prompt templates (`variant_review`, `gene_dossier`, `pgx_review`) in our server. The validation checklist pattern is worth reading for our skill authoring. Not a code port.

### 1.6 Ongoing Gaps (unchanged from April memo — still unported)

All five "Must-Add" items from `biomcp-source-comparison-2026-04-03.md` remain unimplemented in our server:
1. CPIC PGx client (gap confirmed)
2. CIViC GraphQL client (gap confirmed)
3. OncoKB client (gap confirmed)
4. cBioPortal mutation frequency (gap confirmed)
5. Variant input normalization (gap confirmed)

These pre-date this delta period but are still the highest-ROI ports. The April memo should be re-consulted for implementation details.

---

## Section 2: FastMCP Delta (3.2.0 → 3.4.2)

**Bottom line: our pin `fastmcp>=3.4,<4.0` is valid. No 4.0 exists. No breaking changes affect our specific usage (stdio transport, @tool decorators, mount(), middleware, no background tasks, no proxy).** One net-positive: 3.2.4 now auto-extracts parameter descriptions from docstrings — upgrading from 3.2 to 3.4 gives us this for free.

### Relevant Changes Summary

| Version | Date | Impact on us |
|---------|------|-------------|
| 3.2.1 | 2026-04-08 | Auth fixes; OpenAPI 3.0 `nullable` no longer leaks into tool schemas. Positive for any `from_openapi()` usage. |
| 3.2.4 | 2026-04-14 | **Auto-extracts parameter descriptions from docstrings** — free improvement to our tool schemas. BREAKING on background tasks (we don't use). |
| 3.3.0 | 2026-05-15 | `fastmcp-slim` (client-only); `run_in_thread` opt-out for sync tools with thread affinity. Not relevant for us. |
| 3.3.1 | 2026-05-15 | Hotfix for packaging circular import — relevant only if using `from fastmcp.tools import tool` standalone. |
| 3.4.0 | 2026-06-03 | `fastmcp-remote` bridge (stdio host → HTTP server). Breaking: proxy `initialize` forwarding. Neither affects us. |
| 3.4.1 | 2026-06-05 | Security: CVE-2026-48710 (Starlette). We don't run HTTP transport but upgrading is still good practice. |
| 3.4.2 | 2026-06-06 | JWT compatibility for Clerk-style tokens. Not relevant (local stdio only). |

### Action: Verify We're on 3.4

We bumped from 3.2 to 3.4 on 2026-06-04 per the task description. Confirm `pyproject.toml` has `fastmcp>=3.4,<4.0` and the installed version in the venv is ≥3.4.0. The docstring-to-parameter-description auto-extraction (3.2.4) will already be active.

---

## Section 3: MCP Spec 2026-07-28 RC

The RC was locked 2026-05-21. Final spec ships 2026-07-28. FastMCP is a Tier 1 SDK — support expected within the 10-week window, i.e., before the July 28 final date.

### Breaking changes and our exposure

| Change | Our exposure | Action |
|--------|-------------|--------|
| Session/handshake removal (`Mcp-Session-Id`, `initialize` round-trip gone) | **NONE** — we're stdio-only; session management is handled by FastMCP SDK, not our code | Monitor FastMCP releases for `mcp-2026-07-28` compatibility flag |
| SSE deprecated (servers return `InputRequiredResult` instead) | **NONE** — no streaming/interactive tools | None |
| Error code: missing resource → `-32602` instead of `-32002` | **LOW** — we catch HTTP errors, not MCP error codes directly | None |
| Tasks API redesign (extension, new lifecycle) | **NONE** — we don't use Tasks | None |
| JSON Schema 2020-12 support | **POSITIVE** — enables `oneOf`/`anyOf` in tool schemas | Optional: use for variant input normalization (accept rsID | HGVS | gene+change) |
| `ttlMs`/`cacheScope` on list results | **POSITIVE** — clients can cache our tool list | None required; FastMCP will emit headers automatically |
| Roots, Sampling, Logging deprecated | **NONE** — we use none of these | None |

**Assessment:** The stateless change is a non-event for our stdio deployment. The session model was always invisible to us — FastMCP handles the protocol layer. The main action item is to monitor the FastMCP release that declares `mcp-2026-07-28` compatibility and upgrade our pin to include it (likely FastMCP 3.5.x or 4.0 if they use it for a major bump).

**Risk for pinning `<4.0`:** If FastMCP ships MCP 2026-07-28 support in a major version bump (4.0), our pin will block it. Given FastMCP's history of shipping breaking changes as minor versions (3.x), this seems unlikely, but monitor. The plan should be to update the pin to `>=3.4,<5.0` once FastMCP 4.0 ships and we validate it.

---

## Section 4: Broader Biomedical MCP Ecosystem

### 4.1 BioContextAI — Stalled

As of 2026-06-07, BioContextAI (`biocontext-ai/knowledgebase-mcp`) has grown only from 20 to **24 stars** since the March 2026 memo. Latest release is v0.2.1 from December 2025 — **no 2026 release** visible. Covers 14 DBs via Apache 2.0. The BioContextAI registry lists additional community MCP servers but the core knowledgebase-mcp appears to be in slow-maintenance mode.

**Dependency verdict: still LOW.** Same rationale as March memo — minimal traction, no institutional backing beyond an academic group. The Nature Biotechnology publication claim could not be verified via primary source — treat as LOW confidence.

### 4.2 OpenPGx — New, Too Small

`open-pgx/openpgx` is a standalone PGx MCP server (TypeScript, MIT, 10 stars) covering 118 studies, 109 genes, 219 medications, 19 disease risk conditions, 31+ traits. 9 tools including `check_medication`, `full_pgx_report`, `supplement_protocol`, `check_risk`. Architecture: local data files (JSON), no live API calls.

**Dependency verdict: LOW.** 10 stars, no institutional backing, TypeScript (incompatible with our Python server composition). Its data scope (118 studies, 109 genes) is narrower than what we'd get from CPIC + PharmGKB integration. The design pattern (local data bundle for PGx, no API latency) is worth considering for our own CPIC integration if CPIC API latency becomes an issue.

### 4.3 OpenClaw Medical Skills — Not an MCP Server

2.6k stars, but this is a **skill library for the OpenClaw/NanoClaw Claude-based framework**, not an MCP server. 869 markdown skills wrapping 40+ biomedical tools (gnomAD, COSMIC, Orphanet, GWAS, etc.). Architecturally incompatible with our setup. High star count reflects OpenClaw's user base, not MCP ecosystem traction.

### 4.4 Healthcare MCP Public (Cicatriiz) — Narrow Scope

`Cicatriiz/healthcare-mcp-public` covers FDA drug info, PubMed, medRxiv, NCBI Bookshelf, clinical trials, ICD-10, DICOM metadata. Significant overlap with our existing tools. No star count found in fetched content. Not worth depending on.

### 4.5 OncoMCP (GenomOncology) — Commercial Upmarket

GenomOncology announced OncoMCP as a commercial HIPAA-compliant enterprise extension of BioMCP with: EHR integration, real-time trial matching, 15K+ curated trials KB, patient matching via clinical + molecular profiles, NLP-based structured extraction. This is their commercial product; BioMCP remains OSS.

**Implication for our server:** Signals GenomOncology is upmarketing toward clinical deployment. The OSS BioMCP will continue to be maintained as their developer funnel. The oncology sources (CIViC, OncoKB, cBioPortal) are unlikely to be locked behind OncoMCP — they're already in OSS BioMCP.

---

## Port Priority Ranked by Value

Ordered highest-to-lowest including both the pre-existing April gaps (still not ported) and the new delta items:

1. **CPIC + PharmGKB PGx client** [pre-April gap, HIGH] — genotype-to-drug recommendation pipeline; most clinically impactful gap; BioMCP already ships this; ~300 lines. No new BioMCP changes, but this is still #1 unported item.

2. **DDInter drug-drug interactions** [NEW in v0.8.22, HIGH] — zero DDI coverage in our server; DDInter has 240K+ records; free API or offline bundle; ~200 lines. New delta item, additive to existing drug domain.

3. **GTR genetic test registry** [NEW in v0.8.22, HIGH] — NCBI GTR covers 100K+ tests; free eutils API; ~150 lines; expands our clinical utility for "what genetic test should I order?" questions. New delta item.

4. **CIViC GraphQL client** [pre-April gap, HIGH] — free, key oncology source; integrates into `composite_variant_context`; ~200 lines.

5. **OncoKB client** [pre-April gap, HIGH] — Memorial Sloan Kettering cancer variant levels; requires API key; ~150 lines.

6. **cBioPortal mutation frequency** [pre-April gap, HIGH] — cancer type frequency table; free REST; ~150 lines.

7. **EMA regulatory data** [NEW in v0.8.21, MED] — EU drug regulatory parity; free EMA web API; ~150 lines; relevant for EU clinical use.

8. **Variant input normalization** [pre-April gap, MED] — handle "BRAF V600E" notation; ~100 lines.

9. **FDA 510(k) diagnostic overlay** [NEW in v0.8.22, MED] — via our existing OpenFDA client, new endpoint only; ~50 lines.

10. **JSON Schema 2020-12 `oneOf` for variant input** [MCP RC, MED] — enables typed variant input (rsID | HGVS | gene+change) in tool schemas; cosmetic but improves LLM tool calling.

---

## FastMCP Version Action Items

1. **Verify 3.4 is installed** — `uv run python3 -c "import fastmcp; print(fastmcp.__version__)"` in `~/Projects/biomedical-mcp/`. Should be ≥3.4.0.
2. **Docstring descriptions are free** — if any tool decorators lack parameter descriptions but have them in docstrings, 3.2.4+ will auto-populate. No code change needed.
3. **Monitor FastMCP for MCP 2026-07-28 support** — expected in FastMCP 3.5.x or 4.0.x between now and July 28, 2026. When it ships, validate and update our pin. The RC stateless change is not a breaking change for stdio-based servers — FastMCP will absorb it.
4. **No rush to upgrade beyond 3.4.2** — all changes from 3.4.0 onwards are auth/proxy/security improvements not relevant to local stdio deployment.

---

## What Has NOT Changed Since April (verify independently)

- BioMCP's single-tool MCP architecture (still 1 tool + 1 resource) — no change to the architectural tradeoff assessed in April memo.
- AlphaGenome gRPC integration still present — still unported in our server.
- No new BioMCP PGx sources beyond CPIC + PharmGKB already tracked in April.
- Our decision to run BioMCP alongside (Option E revised in April) remains valid — the two new entities (`diagnostic`, DDInter) add additive value rather than creating new overlap.

---

## Search and Verification Log

| Query / Fetch | Tool | Result | Confidence |
|---|---|---|---|
| github.com/genomoncology/biomcp/releases | WebFetch | v0.8.21, v0.8.22 release notes | HIGH |
| github.com/genomoncology/biomcp | WebFetch | Current version, star count, entity list | HIGH |
| github.com/jlowin/fastmcp/releases | WebFetch | Release list 3.4.2 is latest, no 4.0 | HIGH |
| gofastmcp.com/changelog | WebFetch | Full changelog 3.0.0–3.4.2 | HIGH |
| pypi.org/project/fastmcp | WebFetch | Confirmed 3.4.2 latest | HIGH |
| blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ | WebFetch | Full RC breaking changes | HIGH |
| WebSearch: MCP spec 2026 stateless | WebSearch | Multiple confirming sources | HIGH |
| github.com/biocontext-ai/knowledgebase-mcp | WebFetch | 24 stars, v0.2.1 Dec 2025, no 2026 releases | HIGH |
| github.com/open-pgx/openpgx | WebFetch | 10 stars, 9 tools, TypeScript | HIGH |
| github.com/FreedomIntelligence/OpenClaw-Medical-Skills | WebFetch | 2.6k stars, skill library not MCP | HIGH |
| WebSearch: OncoMCP commercial | WebSearch | PR Newswire + search sources | MED |
| biomcp.org/how-to/skill-validation/ | WebFetch | Validation system docs — no SkillBench numbers | HIGH |
| BioContextAI Nature Biotech claim | Not verified at primary source | LOW confidence | LOW |

<!-- knowledge-index
generated: 2026-06-07T00:00:00Z
hash: biomcp-fastmcp-delta-2026-06-07

title: BioMCP / FastMCP Upstream Delta — 2026-06-07
topics: [biomcp, fastmcp, mcp-spec, biomedical-mcp, DDInter, GTR, diagnostic, EMA, pharmacogenomics]
prior: biomcp-evaluation-2026-04-03.md | biomcp-source-comparison-2026-04-03.md | fastmcp3-integration-plan.md

end-knowledge-index -->
