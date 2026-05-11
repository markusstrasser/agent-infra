---
title: Prior-Art Synthesis — Scientific Substrate (2026-05-11)
date: 2026-05-11
tags: [synthesis, prior-art, extractors, provenance, packaging]
status: complete
inputs:
  - 01-pdf-html-extractors.md
  - 02-provenance-attestation-patterns.md
  - 03-scientific-corpus-libs.md  # pending
  - 04-reusable-packaging.md
---

# Prior-Art Synthesis

User asked for a sanity check that the migration plan isn't reinventing existing solutions. Four parallel research agents surveyed (1) PDF/HTML extractors, (2) provenance/attestation standards, (3) scientific corpus libraries, (4) reusable infra packaging. Three reports back; corpus-libs re-dispatched after timeout. This synthesis acts on what's firm and flags the open report.

## Firm findings — applying to plan immediately

### 1. Extractor stack flips: Marker → MinerU

**Status: HARD BLOCKER on the previous plan.**

- **Marker is GPL-3.0.** Violates the "MIT/Apache only" policy the user set.
- **Marker is empirically broken on Apple Silicon Mac** — 4 confirmed open issues (#993 surya MPS, #967 table-decoder no MPS, #960 20× slowdown post-v1.9, #966 CLI failure). Today's own benchmark (parallel agent, `pdf-to-markdown-tooling-2026-05.md`) crashed at p.10 of a 41-page preprint.
- **MinerU 3.1.0 wins on quality** — Apache-2.0-derivative license (with 100M-MAU / $20M-MRR commercial trigger, ~8 orders of magnitude below us), CPU-runnable, +14.6 OmniDocBench points over Marker (93.04 vs 78.44) on academic_literature subset. Pipeline backend (DocLayout-YOLO + UniMERNet) explicitly supports Apple Silicon.

**pymupdf4llm is AGPL-3.0.** Fine for personal-local use; AGPL network clause activates if served behind a network endpoint. Document the boundary in SCHEMA.md but keep — its speed advantage (25-50× over MinerU for native-text PDFs) is real and irreplaceable without quality loss. The "MIT/Apache-only" rule needs an explicit carve-out for local-only AGPL libraries (no published consumer service); document the rule.

**Trafilatura stays for HTML** — F1 0.909, Apache-2.0, no contender has surpassed it since 2022. Resiliparse is faster but documented lower-recall.

**No single library does PDF + HTML + Office well.** Docling is the only credible "one library" candidate (MIT, supports DOCX/PPTX/XLSX/HTML/audio + PDF) but trades ~5-8 OmniDocBench points and ~2× speed vs MinerU on scientific PDFs. Keep the three-tool stack: MinerU + pymupdf4llm + trafilatura.

**Plan updates required:**
- Phase 1.5 swap Marker → MinerU
- SCHEMA.md add license-policy invariant: "Apache-2.0 / MIT preferred; AGPL acceptable for local-only personal use; GPL-3.0 prohibited"
- `corpus_core/extract/pdf_marker.py` → `pdf_mineru.py`
- Drop the `/tmp/pdf-bench/` Marker venv fallback (developer artifact, broken)
- Optional: add GROBID as a separate "citation extraction" lane (TEI-XML; different niche, used by S2/scite)

### 2. Annotation schema: stay bespoke, borrow RO-Crate vocab

**Status: confirms our design, with small renames.**

None of the surveyed standards fit cleanly. The closest match is **RO-Crate Process Run Crate** — its `CreateAction` with `agent`/`instrument`/`object`/`result`/`endTime` is exactly our model semantically, but its JSON-LD per-output-folder packaging is incompatible with per-source append-only JSONL.

The recommendation: **rename our fields to align with RO-Crate vocab; do NOT adopt the JSON-LD `@context`/`@graph` wrapper.**

| Our current field | RO-Crate equivalent | Action |
|---|---|---|
| `actor_type` + `actor_id` | `agent` (Person) OR `instrument` (SoftwareApplication) | Add — disambiguates human-vs-tool |
| `tool` / `model` | `instrument` | Use `instrument` for tool/model identity |
| `scope` + source_id | `object[]` (inputs) | Map but keep `scope` (we have semantics RO-Crate doesn't) |
| `output_uri` + `output_hash` | `result` (nested) | Nest under `result.uri` + `result.hash` |
| `asserted_at` | `endTime` | Add `endTime` alias for export compatibility |

**What we keep that the standards don't have** (legitimate workflow needs):
- `recorded_at` ≠ `asserted_at` split (multi-agent clock drift handling)
- `idempotency_key` from stable tuple
- `supersedes_annotation_id` as first-class field

**What to add cheaply:**
- `conformsTo` field per record — names the schema version (`https://schema.local/corpus/annotation/v1.0.0`)
- Stable URI-form agent IDs (`urn:agent:claude-opus-4-7`, `urn:agent:research-mcp@0.1.2`)
- Flat namespace keys following OpenTelemetry convention (`agent.id`, `agent.type`, `result.uri`, `result.hash`)

**Other standards explicitly rejected:**
- W3C PROV-O direct adoption (RDF/Turtle/SPARQL infrastructure overhead)
- in-toto / SLSA (wrong domain — software supply chain, not ML annotations; zero ML-specific predicates)
- OpenLineage (right architecture, wrong noun — pipeline-orchestration model)
- OpenTelemetry GenAI (tracing layer, not persistent assertions — but USE as the upstream span source when annotation is created)
- MLflow / DataHub / Marquez / DVC / sigstore (heavy / wrong layer / wrong scale)

**Plan updates required:**
- Phase 1 annotation schema: rename fields to RO-Crate vocab; add `conformsTo`, `agent.id`, `result.uri`/`result.hash` namespace; document mapping

### 3. Packaging: uv workspace + monorepo + plugin bundle

**Status: clear pattern, easy to copy.**

The 2026 standard, verified across PaperQA2, DVC, mem0, cognee, fastmcp: **single GitHub repo, `uv` workspace, multiple PyPI packages, Claude Code plugin bundle on top.**

Recommended shape for the substrate:

```
~/Projects/corpus/                     (eventual repo root; today: in agent-infra)
├── pyproject.toml                     (workspace root: tool.uv.workspace = ["packages/*"])
├── packages/
│   ├── corpus-core/                   pip install corpus-core      schemas + IDs + store layout
│   ├── corpus-cli/                    pip install corpus-cli       CLI on top of corpus-core
│   ├── corpus-mcp/                    uvx corpus-mcp               MCP server
│   ├── corpus-extractors/             optional, opt-in extractor adapters
│   └── corpus-plugin-claude/          Claude Code plugin bundle
├── schemas/                           versioned JSON Schema (in-tree, bundled)
├── data/                              gitignored — the canonical store (<source_id>/ dirs + graph.duckdb)
├── docs/
└── tests/
```

**Three resolution layers for `CORPUS_ROOT`:**
1. Explicit kwarg → 2. `CORPUS_ROOT` env var → 3. `[tool.corpus]` in caller's pyproject.toml → 4. `platformdirs.user_data_dir("corpus")` default

**MCP distribution:** PyPI + `uvx corpus-mcp` (2026 standard, verified across `mcp-server-git`, `aws-mcp`, `azure-mcp`, `cognee-mcp`). Each repo's `.mcp.json` declares the `uvx` invocation. NO Docker as primary distribution.

**Per-repo schema registration:** Entry-points (`[project.entry-points."corpus.schemas"]`). Genomics/phenome/intel register their own claim/verdict schema versions with `corpus_core` at install time.

**Patterns to copy:**
- PaperQA2's workspace declaration verbatim
- mem0's factory pattern (reject its bundled extras)
- cognee's subdirectory MCP layout (reject its 60-dep core)
- fastmcp as the server framework (reject telemetry-by-default)
- DVC's `dvc[extra] → dvc-extra-pkg` subpackage architecture

**Plan updates required:**
- Phase 1: `scripts/papers/` (renamed `scripts/corpus/` in Phase 0.5) is shaped as a workspace root from the start. `corpus_core` is `packages/corpus-core/` with its own pyproject.toml.
- Phase 1.5: extractors live in `packages/corpus-extractors/` (or are bundled into corpus-core's optional deps initially)
- Phase 3: `corpus-mcp` lives in `packages/corpus-mcp/`
- Add new Phase 8 (FUTURE): repo extraction + PyPI publish + Claude Code plugin marketplace. Triggers when there's >1 user; deferred for now. Today the code stays in `agent-infra` because there's no publishing need.

### 4. Repo separation: code stays in agent-infra today; eventual standalone repo

Tension: the canonical store path is `~/Projects/corpus/` (data); the workspace layout above implies that path is ALSO the repo root (code). They can coexist if `.gitignore` separates `data/` from `packages/`, OR the code can stay in agent-infra under `scripts/corpus/` and the canonical store stays at `~/Projects/corpus/` as a separate filesystem location.

Recommendation: **today, code at `~/Projects/agent-infra/scripts/corpus/`; data at `~/Projects/corpus/`.** When Phase 8 extracts to a standalone repo, the new repo root becomes the canonical store path with data/ gitignored. Single-developer phase doesn't need the unified repo today.

## Resolved — corpus-libs verdict

**Build `corpus_core` (~400 LOC), cherry-pick PaperQA2's identity convention.** Final outcome of the re-dispatched corpus-libs report.

Why not adopt PaperQA2's `Docs`:
- `extra="forbid"` Pydantic — hard to extend without forking
- Mandatory `texts_index: VectorStore` field — can't use the container without the embedding/RAG machinery
- `Doc` extends `Embeddable` from FutureHouse's `lmi` package, transitively requiring `litellm` + `openai` + `anthropic` clients
- `Docs.aadd()` default makes 2 LLM calls per document — bypassable but the API is built around them
- No opinionated on-disk layout — single-blob `model_dump_json()` persistence, awkward for per-source directories

What's worth borrowing from PaperQA2 (Apache-2.0, well-maintained, FutureHouse-backed):
- **`compute_unique_doc_id(doi, content_hash)` from `utils.py`** — stable ID derivation matching the canonical convention. Reimplement (~10 LOC) for interop OR vendor the function.
- **`DocDetails.lowercase_doi_and_populate_doc_id` validator** — DOI normalization rules.
- **The `paperqa.clients/` directory IS the gem.** `crossref.py`, `openalex.py`, `semantic_scholar.py`, `unpaywall.py`, `retractions.py`, `journal_quality.py` + `DocMetadataClient` orchestrator. No LLM dependency, hits external APIs, returns `DocDetails`. **Use as an optional enrichment dependency** — when `corpus_core.enrich.metadata(source_id)` is wired in, the call is between (a) `paperqa-clients` import (free, well-maintained, transitive deps include `aiohttp` and `pybtex`) and (b) 150 LOC of homegrown REST clients (more control, more drift). Defer the call until metadata enrichment is actually needed.

Other candidates explicitly rejected by the audit:
- **Aviary / LDP** — language-agent gym + decision-process framework. Not corpus libraries.
- **OpenScholar** — research code (`run.py + retriever/ + training/`), dormant since 2025-08-13, no library API surface.
- **ASReview** — active-learning screening tool; no DOI/PMID dedup. Wrong problem.
- **pyzotero** — HTTP client to Zotero REST. Not a corpus manager.

**Plan updates required:**
- Phase 1 `corpus_core/identity.py` adopts PaperQA2's DOI normalization (`compute_unique_doc_id` pattern, ~10 LOC vendored with attribution)
- Phase 1.5 (or new Phase): IF/when we wire metadata enrichment, default to importing `paperqa.clients` (Apache-2.0) over hand-rolling REST clients. Deferred until needed.

## Other things the reports did NOT flag (negative findings worth noting)

- No 2026 convergence on "agent annotations" as a standardized schema. The space is bespoke. Our schema can become the convergent answer in this niche, not just one of many.
- No drop-in "scientific corpus management" library that handles paper + non-paper + provenance + extractor dispatch in one package. The niche is unfilled.
- No mature Apple-Silicon-first PDF extraction library. Most tools are NVIDIA-first; MinerU works on MPS but isn't optimized for it. Some performance ceiling to expect.
- No emerging MCP that does what `corpus-mcp` will. The personal-scientific-substrate niche is genuinely empty in 2026 OSS.

## Plan-level changes triggered by this synthesis

| Change | Where | Severity |
|---|---|---|
| Marker → MinerU swap | Phase 1.5 of plan, memo §Extraction pipelines | Critical (license + correctness) |
| Document AGPL local-only carve-out | SCHEMA.md, license policy | Medium |
| Rename annotation fields to RO-Crate vocab + add conformsTo + flat namespace | Phase 1 schema, memo §Annotation schema | Medium |
| Reshape `scripts/papers/` → workspace-ready (`packages/corpus-core/` + workspace root) | Phase 0.5 / Phase 1 | Medium |
| Note Phase 8 for eventual PyPI publish + Claude plugin bundle + repo extraction | New phase, memo | Low (deferred work) |
| GROBID as optional citation lane | Phase 1.5 footnote / future work | Low |

## What I'm doing next (this session)

1. Apply the firm findings to memo + plan (Marker→MinerU, RO-Crate vocab, workspace shape).
2. Wait for corpus-libs report.
3. Once that lands, fold in adopt-vs-build call.
4. Commit.

The plan does NOT execute on any phase until this synthesis is fully integrated and (optionally) cross-model-reviewed one more time.

<!-- knowledge-index
generated: 2026-05-11T07:30:54Z
hash: fb473198f5f3

title: Prior-Art Synthesis — Scientific Substrate (2026-05-11)
status: complete
tags: synthesis, prior-art, extractors, provenance, packaging

end-knowledge-index -->
