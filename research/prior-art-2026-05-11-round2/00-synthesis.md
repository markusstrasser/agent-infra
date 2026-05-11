---
title: Round 2 Prior-Art Synthesis — Substrate Refinements
date: 2026-05-11
tags: [synthesis, prior-art, round2, schema, graph, content-addressing, dx, on-disk-layout, annotation-storage]
status: complete
inputs:
  - 01-graph-storage-at-scale.md
  - 02-schema-versioning.md
  - 03-skill-mcp-dx-2026.md
  - 04-content-addressing.md
  - 05-on-disk-layout-standards.md
  - 06-annotation-storage-at-scale.md
prior_round: ../prior-art-2026-05-11/
---

# Round 2 Synthesis

Six parallel research dispatches answered the open design questions remaining after round 1. All six reports landed. No contradictions across reports.

## Verdicts at a glance

| Axis | Round-1 plan | Round-2 verdict | Change |
|---|---|---|---|
| Graph storage | DuckDB | **Stay DuckDB.** Kuzu (main alternative) was archived on GitHub 2025-10-10 after Apple acquired the team. DuckPGQ extension is the upgrade path. | Confirmed |
| Schema versioning | `schema_version: "1.0.0"` (SemVer) | **Switch to SchemaVer** (`"1-0-0"`, MODEL-REVISION-ADDITION). Pydantic v2 discriminated-union upcasters at read time; JSONL never rewritten. | CHANGE |
| Skill/MCP DX | Ad-hoc | Ship `corpus_core.testing` fixtures, OTel-from-day-one, lint stdio prints, 5-15 tools/MCP budget. Use Anthropic's official `mcp-server-dev` + `skill-creator` (no scaffolder reinvention). | ADD |
| Content addressing for source IDs | sha256_hex(canonical_json) | **Stay plain sha256.** CIDs unneeded — no 2026 consumer wants them. Add `to_cidv1_b32()` as a 5-line view when a consumer asks. | Confirmed |
| Content addressing for annotation IDs | UUID5-with-namespace (phenome alignment) | **REVERSAL: use sha256-based** (`"ann_" + sha256_hex(canonical_json(tuple))[:16]`). UUID5 is SHA-1 truncated to 122 bits — strictly weaker. Phenome's UUID5 stays for assertions (historical compromise). | CHANGE |
| On-disk layout | Native (`<source_id>/{paper.pdf, parsed.<pid>/, ...}`) | **Stay native, stamp `metadata.json` with RO-Crate JSON-LD shell** (~30 LOC). Adds export-compat for free. Reject OCFL (different scale), Frictionless/BIDS (wrong domain). | EXTEND |
| Annotation storage canonical | per-source JSONL | Confirmed. **DuckLake 1.0** (April 2026) is the projection-layer upgrade path if needed; NOT Iceberg (DuckDB-Iceberg schema-evolution broken, issue #805) and NOT Lance (loses human-grokkability). | Confirmed |
| In-memory graph algorithms | (not in plan) | **rustworkx** is the right NetworkX replacement for PageRank/centrality/community ops. Apache-2.0, IBM/Qiskit-backed. Optional dep; NOT in core plan; future "corpus analyze" subcommand. | NOTE FOR FUTURE |
| JCS canonicalization conformance | Phenome's `canonical_json` | Add `rfc8785.py` (`trailofbits/rfc8785.py`) as dev-dep property test only. Don't swap runtime. | ADD (test infra) |

## Per-axis details and actions

### 1. Graph storage (01-) — DuckDB confirmed

**Headline:** Kuzu archived October 2025 after Apple acquisition (verified at 1.0 confidence: The Verge, BetaKit, MacRumors, Waterloo CS, kuzudb/kuzu commit log).

**Numbers (M3 MacBook Pro, our scale-bracket):**
- prrao87/kuzudb-study, 100K nodes / 2.4M edges: multi-hop 8.6–95 ms
- DuckPGQ v1.4.4 (CWI, March 2026): bounded triangle Q1–Q3 7.7–28.8 ms; unbounded multi-hop Q4–Q6 16.5–67.7 ms (arXiv 2505.07595)
- CIDR 2023: DuckDB wins 1-hop selective sub-ms; Kuzu won 2-hop+ over many-to-many
- NetworkX ≈ 100 bytes/edge → 3M edges ≈ 300 MB resident — ephemeral analysis only, wrong primary store

**Caveat:** None of these benchmarks are p95. Document expected p95 ranges (<5ms for selective 1-hop, tens of ms for bounded k-hop with k≤3) and measure on real corpus before publishing SLO.

**Plan unchanged.** Note `rustworkx` (Apache-2.0, Qiskit-backed) as the modern NetworkX swap when in-memory graph algorithms become needed.

### 2. Schema versioning (02-) — switch to SchemaVer

**Headline change.** `schema_version: "1.0.0"` → `"1-0-0"` (SchemaVer MODEL-REVISION-ADDITION).

- SemVer doesn't describe schema compatibility (the spec literally says "for an API"). SchemaVer (Snowplow) describes data-shape compatibility:
  - MODEL bump = breaking
  - REVISION bump = backward-incompatible to old readers, forward-compatible to new
  - ADDITION = additive (new optional fields), readers ignore unknowns
- **Path layout:** `~/Projects/corpus/schemas/v1/{annotation.v1.json, source_record.v1.json, claim.v1.json, verdict.v1.json}`
- **Migration:** Pydantic v2 discriminated-union upcasters at read time. JSONL never rewritten. DuckDB index rebuilt only on MODEL bumps.
- **Adapter pattern for per-repo MCPs on different schema versions** — discriminated-union keeps v1 class alive in parallel with v2.

**Rejected:** Avro/Protobuf/Iceberg-direct (binary breaks grep-ability — the 10-year-archive value prop), W3C VC `@context` (dead weight without crypto), field IDs (problem we don't have with append-only), out-of-band migrations.

### 3. Skill/MCP DX (03-) — ship test fixtures, observability from day one

**Bake into `corpus_core` scaffolding:**

- **`corpus_core.testing` module** exporting:
  - FastMCP `Client(server)` async fixture (5 lines)
  - Copy-paste `conftest.py` template (3-6 lines per test, sub-ms execution)
  - Test database fixtures
  - This is THE highest-leverage gift to downstream MCP authors
- **OpenTelemetry from day one** — FastMCP emits MCP semantic conventions natively. Zero config. Downstream observability is just an OTLP endpoint config.
- **Lint against `print()` from stdio** — runtime check in `corpus_core` rejects stdout writes outside the JSON-RPC stream. This bites every new MCP author.
- **Tool budget invariant: 5-15 tools per MCP.** Hard ceiling at 20. Speakeasy data: 95% accuracy at 20 → near-0 at 107. Industry case studies converge: GitHub Copilot 40→13, Block Linear 30+→2.

**Don't reinvent:**
- Skill scaffolder → use Anthropic's official `skill-creator` plugin
- MCP server scaffolder → use Anthropic's official `mcp-server-dev` plugin
- Typed client codegen → export tool schemas via `just export-schemas` recipe; let downstream codegen with whatever (Speakeasy/Stainless/openapi-mcp-generator)

**Hello-world install:**
```
/plugin marketplace add <our-url>
/plugin install corpus@corpus-marketplace
/reload-plugins
```

**Audit needed (Phase 4 or follow-up):** genomics-mcp has ~30 tools — likely above the accuracy cliff. Phenome-mcp and intel-mcp should be designed to the 5-15 budget from the start.

### 4. Content addressing (04-) — sha256 confirmed; annotation-ID reversal

**Stay plain `sha256_hex(canonical_json(...))`** for source IDs:
- sha256 IS already a multihash (`0x12 0x20 + 32 bytes`); CIDv1 base32 is a 5-line view function the day a consumer asks. No rehashing, no migration.
- **No 2026 consumer wants CIDs.** Zenodo = DOIs; HuggingFace = git-LFS hash; S2 = sequential CorpusID; Crossref/DataCite/arXiv same. The "future-proofs for distributed sharing" argument is unsupported by the actual landscape.

**REVERSAL for annotation IDs:** my prior round-1 alignment used UUID5-with-namespace matching phenome v4. The reviewer correctly distinguishes:
- Phenome's UUID5-with-namespace is a *historical compromise* for the assertion-ID namespace (3622 existing rows; migrating costs more than the upgrade buys).
- **For corpus_core's NEW ID space** (annotations: zero existing data), use `annotation_id = "ann_" + sha256_hex(canonical_json(stable_tuple))[:16]`.
- UUID5 uses SHA-1 truncated to 122 bits — deprecated and strictly weaker.
- Phenome's INVARIANT (`sha256_hex(canonical_json(...))`) is what we inherit. The UUID5 wrapper is layer-specific.

**JCS conformance:** add `rfc8785.py` (`trailofbits/rfc8785.py`) as **dev-dep property test only**. Assert `canonical_json` produces identical bytes to JCS for our actual input types (UTF-8 BMP keys, integers, no control chars). Don't swap the runtime — divergence (UTF-16 vs Unicode codepoint sort, ES6 number serialization) only matters for inputs we don't have.

**Rejected wholesale:** W3C VC Data Integrity, Sigstore/Rekor, CBOR canonical — each solves a problem we don't have. Revisit only when publishing a redistributable corpus.

### 5. On-disk layout (05-) — stay native + RO-Crate stamp

**Layout itself unchanged:** `~/Projects/corpus/<source_id>/{paper.pdf, parsed.<parser_id>/, citances_in.jsonl, citances_out.jsonl, annotations.jsonl, metadata.json, INDEX.json}`.

**Add: stamp `metadata.json` with RO-Crate JSON-LD shell.**

```json
{
  "@context": "https://w3id.org/ro/crate/1.2-DRAFT/context",
  "@graph": [
    {
      "@id": "ro-crate-metadata.json",
      "@type": "CreativeWork",
      "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2-DRAFT"},
      "about": {"@id": "./"}
    },
    {
      "@id": "./",
      "@type": "Dataset",
      "identifier": "doi_10_1234_foo",
      "name": "Vector2Variant preprint",
      "datePublished": "2026-04-10",
      "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
      "author": [{"@id": "https://orcid.org/0000-0001-..."}],
      "relatedIdentifier": ["pmid:38123456", "doi:10.1101/2026.04.10.26350624"],
      "hasPart": [
        {"@id": "paper.pdf", "encodingFormat": "application/pdf", "sha256": "..."},
        {"@id": "parsed.mineru@3.1.0/page.md", "encodingFormat": "text/markdown", "sha256": "..."}
      ],
      "corpus:source_type": "preprint",
      "corpus:source_id": "doi_10_1234_foo",
      "corpus:content_hash": "sha256:..."
    },
    {"@id": "https://orcid.org/0000-0001-...", "@type": "Person", "name": "Jane Doe"}
  ]
}
```

**Added fields (~11):** `@context`, `@graph` wrapping, `@type: Dataset`, `identifier`, `name` (= title), `datePublished`, `license` (URI), `author[]` (ORCID URIs), `relatedIdentifier[]` (DOI/PMID aliases), `hasPart[]` (component files with per-file `sha256`), custom `corpus:*` properties under a namespace prefix.

**Cost asymmetry:** ~30 LOC to add fields now; retroactive migration after sources accumulate is a schema migration. Add now.

**Why not OCFL:** OCFL is the gold standard for *petabyte-scale 100-year preservation* (Stanford SDR, Cambridge, Princeton). Its version-directory model (`v1/v2/.../content/`) explicitly contradicts our append-only-JSONL-provenance approach. Wrong scale, wrong fit.

**BagIt is the right EXPORT format, not the live layout.** When/if we publish: `corpus export --format bagit` wraps the RO-Crate in a Bag (the `bagit-ro` pattern). Manifests are mechanically computable from per-file `sha256` already cached in `metadata.json`. One-pass emitter.

**Rejected:** Frictionless Data Packages (tabular-data focused), Croissant (HuggingFace ML datasets), BIDS (neuroimaging-specific), DCAT (catalog metadata layer, not corpus layout).

### 6. Annotation storage at scale (06-) — JSONL canonical + DuckLake upgrade path

**Confirmed:** per-source `annotations.jsonl` + DuckDB projection (current plan).

**Critical added invariant for SCHEMA.md:**
> Annotation records MUST be ≤4096 bytes when serialized. The 4KB ceiling preserves POSIX-append atomicity on Linux/macOS local filesystems. Records that exceed this MUST reference large blobs by hash to a content-addressed store, not inline. Writers MUST use `os.open(path, O_WRONLY | O_APPEND | O_CREAT)` + single `os.write(line.encode() + b"\n")` syscall.

**Migration trigger** if DuckDB single-file projection ever bottlenecks (won't for foreseeable scale):
- **Use DuckLake** (DuckDB Labs, hit 1.0 April 2026). Designed for exactly our envelope (50GB-2TB, small writes, data inlining solves small-files problem).
- **Reject Iceberg.** DuckDB-Iceberg schema evolution is broken in 2026 (column-add against old files crashes — issue #805).
- **Reject Lance.** Loses human-grokkability; ecosystem still vector-flavored.

**Pattern validation:** Cognee, Mem0, paperclip RFC #801 all converge on the same architecture (append-only canonical + indexed cache derived from it). The pattern is correct; we differ only in choice of canonical (JSONL vs SQLite+vector).

## All plan changes from round 2 (summary)

| Change | Where | Severity |
|---|---|---|
| `schema_version: "1.0.0"` → `"1-0-0"` (SchemaVer) | Annotation schema, source_record schema | Medium |
| `schemas/v{N}/` directory layout | Phase 0.5 (move into reshape) + Phase 1 | Medium |
| Pydantic v2 discriminated-union upcasters at read time | Phase 1 corpus_core, all schema readers | Medium |
| Annotation IDs use sha256 (not UUID5) — REVERSAL | Phase 1 annotation schema | Medium |
| Phenome's UUID5 stays for assertions; corpus_core uses sha256 for sources/annotations | Memo + plan clarification | Documentation |
| Add `rfc8785.py` dev-dep + property test against `canonical_json` | Phase 1 tests | Low |
| Ship `corpus_core.testing` module with FastMCP Client fixture + conftest template | Phase 1 (NEW corpus_core surface) | Medium |
| OpenTelemetry from day one (FastMCP MCP-semconv) | Phase 3 corpus-mcp + per-repo MCPs | Medium |
| Lint against `print()` from stdio MCPs (corpus_core util) | Phase 1 | Low |
| Tool-budget invariant: 5-15 tools/MCP, hard cap 20 | All MCPs | Medium |
| Genomics-mcp 30-tool audit | Phase 4 follow-up | Note |
| Stamp `metadata.json` with RO-Crate JSON-LD shell + 11 fields | Phase 1 (source_record schema v1) | Medium |
| `corpus export --format bagit` capability (future) | Phase 8 | Low (deferred) |
| 4KB ceiling invariant on annotation line size | SCHEMA.md + corpus_core.annotate() | Medium |
| `rustworkx` noted as future analytics layer (NOT in current plan) | Memo footnote | Low (future) |
| DuckLake noted as projection-layer upgrade path (NOT current) | Memo footnote | Low (future) |
| Skip Anthropic-official scaffolders for skill-creator + mcp-server-dev | Phase 3 | Low |

## Convergent state

After two rounds of prior-art research + one /critique deep review, the plan is:

1. **Canonical store:** native filesystem layout, with RO-Crate JSON-LD stamping on `metadata.json` for export-compat
2. **Identity:** `sha256_hex(canonical_json(...))` invariant (matches phenome v4); UUID5 stays in phenome for assertions only; corpus_core annotation IDs use sha256-based content addressing
3. **Schemas:** SchemaVer versioned, `schemas/v{N}/` in-corpus, Pydantic v2 upcasters
4. **Extractors:** MinerU (paper lane), pymupdf4llm (fast lane, AGPL local-only), trafilatura (HTML)
5. **Graph storage:** DuckDB with DuckPGQ extension when ergonomics warrant
6. **Annotation storage:** per-source JSONL (4KB ceiling invariant) + DuckDB projection; DuckLake upgrade path if needed
7. **Packaging:** uv workspace with 5 packages (`corpus-core`, `corpus-cli`, `corpus-mcp`, `corpus-extractors`, `corpus-plugin-claude`); Phase 8 deferred publication
8. **MCP shape:** per-repo MCPs with shared interface (`claims_for_source`, `verdicts_for_claim`, `record_verdict`); corpus-mcp owns annotation writes
9. **DX:** `corpus_core.testing` fixtures, OTel from day one, lint stdio prints, 5-15 tool budget
10. **Standards alignment:** RO-Crate vocab for annotations + metadata; JCS property-tested; BagIt export capability when needed

This is the convergent design. Next step: final `/critique model --axes deep` on the full updated memo + plan before any execution.

<!-- knowledge-index
generated: 2026-05-11T07:48:51Z
hash: 697bdc15c42e

title: Round 2 Prior-Art Synthesis — Substrate Refinements
status: complete
tags: synthesis, prior-art, round2, schema, graph, content-addressing, dx, on-disk-layout, annotation-storage

end-knowledge-index -->
