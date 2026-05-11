---
title: On-Disk Layout Standards for `~/Projects/corpus/`
date: 2026-05-11
tags: [corpus, on-disk-layout, ocfl, bagit, ro-crate, frictionless, preservation, fair]
status: research-memo
audience: AI Agent developers picking the corpus filesystem contract
inputs:
  - research/scientific-substrate-target-architecture.md
  - research/prior-art-2026-05-11/04-reusable-packaging.md (workspace shape)
  - OCFL 1.1 spec; RFC 8493 (BagIt); RO-Crate 1.1/1.2; Frictionless Data Package v1; PMC OA layout; DCAT-3; BIDS 1.11.1; Croissant
---

# On-Disk Layout Standards for `~/Projects/corpus/<source_id>/`

## TL;DR — adopt, align, or stay native?

**Stay native today, design metadata.json for one-way export to RO-Crate + (optionally) BagIt.** Don't reshape the working directory to satisfy any preservation standard, because none of them match our access patterns (append-only annotations, multi-parser variants, citance fan-out), but all of them can be *produced on demand* from a well-structured `metadata.json` + `INDEX.json`. The cheap insurance is adding ~8 fields to `metadata.json` now so that `corpus export --format ro-crate <source_id>` or `corpus export --format bagit <source_id>` becomes a 100-line emitter later, not a schema migration.

Specifically:
- **Don't adopt OCFL** as the live layout — it forces `v1/v2/.../content/` versioning we don't need (annotations are append-only JSONL with their own provenance), and the `0=ocfl_object_1.1` Namaste sidecars, sha512 sidecar files, and content-addressable digest manifest are write-amplification we'd pay every commit for marginal benefit at our scale (<10K sources).
- **Don't adopt BagIt** as the live layout — `data/` payload separation is sensible for *transfer*, but inside a live working store it forces a useless directory level. Generate a Bag on `corpus export`.
- **Don't adopt Frictionless Data Package** — it's tabular-CSV-centric. Our payload is PDFs + JSONL, not tables.
- **Don't adopt Croissant** — ML-dataset-specific (features, splits, records). Wrong shape for paper corpora.
- **Reference RO-Crate** — adopt its **vocabulary** (`@context`, schema.org types, ORCID/DOI/ROR identifier conventions) inside `metadata.json` so the file is already a valid RO-Crate Metadata File (`ro-crate-metadata.json` is the formal name, but the spec only requires the file *content* shape, not the filename — see below). This is near-zero cost and buys us standardization the day we want to publish.
- **Drop the rest** — DCAT, Zenodo, PMC, BIDS are not layouts to adopt; they're useful sources of field names and structural patterns.

---

## Per-standard fit assessment

| Standard | What it actually is | Fit for our `<source_id>/` dir | Verdict |
|---|---|---|---|
| **OCFL 1.1** | Application-independent **versioned** object store. Object root holds `0=ocfl_object_1.1` Namaste, `inventory.json` + `inventory.json.sha512` sidecar, then `v1/`, `v2/`, ... with `content/` subdirs. Manifest is content-addressable (sha512 digest → file path). Designed for institutional digital preservation; Stanford, Cornell, Emory, Oxford originators. | Forces version directories. Our annotations are append-only JSONL, our parsed-text variants are `parsed.<parser_id>/` directories (semantic, not temporal). Imposing `v1/`, `v2/` would require copying every annotation event to a new version — write amplification. The content-addressable manifest is nice but DuckDB graph index already gives us O(1) `source_id → files`. | **No.** Refs only. |
| **BagIt (RFC 8493)** | A bag is a directory with `data/` (payload) + `bagit.txt` (declaration) + `manifest-<algo>.txt` (`<checksum> <relpath>` lines) + optional `bag-info.txt` and `tagmanifest-<algo>.txt`. Transfer-focused; LoC, DataONE, Dryad, Rockefeller use it. | The `data/` indirection is overhead inside a live working dir (everything is "payload"). The fixity manifests are good but stale: any new annotation invalidates `manifest-sha256.txt`, forcing rewrite. **However**, BagIt is the right *export* format for shipping a snapshot — `corpus export --bag <source_id>` should produce a valid bag for Zenodo/long-term archive. | **Export-only.** |
| **RO-Crate 1.1/1.2** | A JSON-LD file (`ro-crate-metadata.json`) at the root of any directory that describes the directory's contents using schema.org + DOI/ORCID/ROR identifiers. **No mandated directory shape.** Only the metadata file is required; "the rest" can be whatever. | This is exactly our shape. `metadata.json` is already a single root-level descriptor; making it RO-Crate-compatible is mostly about adopting `@context` + `@graph` and naming things via schema.org types. The companion BagIt-RO ([`ResearchObject/bagit-ro`](https://github.com/ResearchObject/bagit-ro)) wraps an RO-Crate in a BagIt for transfer — exactly the export pattern. | **Reference / align metadata.json.** |
| **Frictionless Data Package** | `datapackage.json` at root, `resources[]` array of file descriptors, **Table Schema** for tabular fields. CSV-centric. | Our payload is PDFs + parsed text + JSONL events, not columnar tables. The `resources` array idea is sound but RO-Crate's `hasPart`/`@graph` already covers it with richer typing. | **No.** |
| **Zenodo deposit layout** | Zenodo accepts arbitrary files plus a `.zenodo.json` (optional) with DataCite-derived metadata. Internally stores everything in DataCite XML / Dublin Core / MARCXML. No directory layout requirement — they accept a ZIP. | Not a layout standard for us. Useful only as the *destination* shape if we ever publish. The `.zenodo.json` field set (creators, license, related_identifiers, version, communities) is worth mirroring in `metadata.json` because the export to Zenodo becomes trivial. | **Reference field names.** |
| **PMC OA bulk layout** | Articles distributed in `oa_package/xx/xx/PMCXXXXXX.tar.gz` (2-level hash-bucket directory) with JATS NXML + PDF + media + supplementary inside. | Their hash-bucket sharding is a useful pattern *if* we ever exceed FS directory limits (~10K entries on macOS HFS+/APFS is fine; ~100K starts to drag on `ls`). Not relevant <10K corpus. The JATS NXML structure is irrelevant — that's about article XML, not corpus organization. | **No (pattern only at scale).** |
| **DCAT-3** | RDF vocabulary for *catalogs of datasets*. Top-level concepts: `dcat:Catalog`, `dcat:Dataset`, `dcat:Distribution`. Use case is federated catalog discovery, not on-disk shape. | Wrong layer. DCAT describes catalogs; RO-Crate describes datasets. If we ever serve a federated index from `graph.duckdb`, DCAT is the right vocab for the *index*, not for `<source_id>/`. | **No (potentially future at index layer).** |
| **BIDS 1.11.1** | Brain Imaging Data Structure. Imposes `sub-<id>/ses-<id>/<modality>/` directories with strict file-naming conventions and `.json` sidecars (`*_T1w.nii.gz` + `*_T1w.json`). | Wrong domain. The valuable pattern is "every data file has a JSON sidecar with the same stem" — but our equivalent (`paper.pdf` + `metadata.json` at root, plus `parsed.<parser_id>/` directories with their own `metadata.json`) already does this. BIDS is overkill for scientific paper packaging. | **No (pattern adopted independently).** |
| **Croissant** | MLCommons schema for ML-ready datasets. JSON-LD on top of schema.org, describes `Dataset`, `RecordSet`, `Field` with ML-specific framing (splits, features). | We're not packaging ML training datasets. If we ever build a citance-classification dataset for ML, Croissant is right for *that*, not for `<source_id>/`. | **No.** |
| **Workflow RO-Crate / WorkflowHub profile** | An RO-Crate *profile* (constraint) for packaging executable workflows. Used by WorkflowHub.eu. | Worth knowing because our `parsed.<parser_id>/` resembles "outputs from a workflow run" — `parsing-workflow-ro-crate-profile` exists. Not adopting it; just noting that a future profile of our metadata.json could declare itself a Workflow Run Crate to inherit existing tooling. | **Future profile.** |

---

## What `metadata.json` should include for future RO-Crate / BagIt export-compat

**Goal:** never have to *restructure* `<source_id>/` to publish. Adding these fields now costs ~30 lines of code; adding them later costs schema migrations across every record.

### Mandatory minimum (RO-Crate flat-JSON profile)

```jsonc
{
  "@context": "https://w3id.org/ro/crate/1.2/context",
  "@graph": [
    {
      "@type": "CreativeWork",
      "@id": "ro-crate-metadata.json",
      "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
      "about": {"@id": "./"}
    },
    {
      "@id": "./",
      "@type": "Dataset",
      "name": "<paper title>",
      "datePublished": "2024-06-15",      // ISO 8601
      "identifier": "doi:10.1234/xyz",   // doi: / pmid: / db: / tool: prefix
      "author": [{"@id": "https://orcid.org/0000-0000-0000-0000"}],
      "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
      "hasPart": [
        {"@id": "paper.pdf"},
        {"@id": "parsed.grobid_0.8.2/"},
        {"@id": "citances_pmc.jsonl"},
        {"@id": "annotations.jsonl"}
      ]
    },
    {"@id": "paper.pdf", "@type": "File", "encodingFormat": "application/pdf", "contentSize": 1234567},
    {"@id": "parsed.grobid_0.8.2/", "@type": "Dataset", "description": "GROBID 0.8.2 parse output"},
    {"@id": "citances_pmc.jsonl", "@type": "File", "encodingFormat": "application/x-jsonlines"},
    {"@id": "annotations.jsonl", "@type": "File", "encodingFormat": "application/x-jsonlines"}
  ]
}
```

This is **already a valid RO-Crate 1.2 Metadata File** — exporters can just rename `metadata.json` → `ro-crate-metadata.json` and the directory is RO-Crate-compliant.

### Add these fields proactively (cheap insurance, big optionality)

| Field | Why | Source standard |
|---|---|---|
| `identifier` with prefix (`doi:`/`pmid:`/`db:`/`tool:`/`repo:`) | Stable cross-corpus identity, already in our IDs but should be in the JSON too. | RO-Crate + DataCite |
| `datePublished`, `dateAcquired`, `dateModified` (ISO 8601) | DataCite/Zenodo require `publicationDate`. We need `dateAcquired` for our own provenance. | DataCite, ours |
| `license` as IRI | Zenodo and most repos require a SPDX/CC URI, not a string. | RO-Crate + SPDX |
| `author[]` with ORCID `@id` URIs | Zenodo + DataCite require ORCID where known. ~30% of recent papers will have ORCID-tagged authors. | RO-Crate |
| `publisher` with ROR `@id` | ROR (Research Organization Registry) IRIs let us deduplicate institutions later. | RO-Crate |
| `conformsTo` profile URI | Lets future agents detect "this is a `corpus-source-v1` crate" and dispatch correctly. | RO-Crate Profiles |
| `wasDerivedFrom` / `prov:wasGeneratedBy` for `parsed.<parser_id>/` entries | Connects parsed output to parser tool entity (a `SoftwareApplication` node in the graph). Lets us export to a full Workflow Run Crate later. | PROV + RO-Crate |
| `contentSize`, `encodingFormat`, `sha256` per File entity | BagIt requires per-file checksums in `manifest-sha256.txt`. Pre-computing them in metadata means `corpus export --bag` is a one-pass file scan. | BagIt + RO-Crate |
| `version` (semver string for the source record itself) | Lets us bump the metadata schema independent of payload — Zenodo "new version" deposit relies on this. | Zenodo, semver |
| `relatedIdentifier[]` (DOI of preprint version, DOI of dataset, etc.) | DataCite required, useful for our citation graph too. | DataCite |
| `keywords[]` and `about[]` (MeSH/schema.org concepts) | Discoverability inside our own DuckDB index. | Schema.org |

This brings `metadata.json` from ~6 fields to ~14 fields. Everything else (BagIt's `bag-info.txt`, OCFL's `inventory.json` digest manifest) can be **computed from these on export** — they don't need separate persistence.

### What stays in `INDEX.json` (not in metadata.json)

`INDEX.json` is the *file inventory* — list of every artifact path under the source directory with their sizes and (optionally) digests. This is what gets serialized to BagIt's `manifest-sha256.txt` and OCFL's `inventory.json.manifest` if/when we export. Keep it separate from `metadata.json` because INDEX is mechanically regenerable from the filesystem, whereas `metadata.json` is semantic and human-curated.

---

## Recommendation (and why some seemingly-relevant standards don't fit)

**Adopt:** the RO-Crate **vocabulary** inside `metadata.json` (add `@context`, `@graph`, schema.org types, the 11 fields above). No directory restructuring. Treat the file as already a valid `ro-crate-metadata.json` even while we keep the filename `metadata.json` for our own clarity.

**Build (one weekend, after substrate is live):**
- `corpus export --format ro-crate <source_id>` → copies dir, renames `metadata.json` → `ro-crate-metadata.json`, writes RO-Crate profile preamble.
- `corpus export --format bagit <source_id>` → builds a bag wrapping the RO-Crate using the `bagit-ro` pattern. Writes `bagit.txt`, computes `manifest-sha256.txt` from the cached digests in metadata, writes `tagmanifest-sha256.txt`.
- `corpus publish-zenodo <source_id>` → submits the bag with `.zenodo.json` derived from `metadata.json`.

**Reject:**
- **OCFL** despite Stanford/Cambridge adoption — those institutions need 100-year preservation across storage migrations. We need a working store for an AI agent across <10K sources. The version-directory model contradicts our append-only JSONL provenance model. The maintenance cost (digest sidecars on every commit, version directory promotion semantics, ocfl-py is "limited popularity") buys us nothing the DuckDB index doesn't already give. *Stanford uses it because they own petabyte-scale Moab→OCFL migrations; we don't have that problem.*
- **BagIt as live layout** — `data/` indirection in a working directory is friction. As an export format it's perfect. The `bagit-ro` pattern (RO-Crate inside a Bag) is the export shape.
- **Frictionless** — tabular-first, wrong shape.
- **DCAT** at the source-record layer — it's a catalog vocab; if we add it anywhere it's at the `INDEX.json` / DuckDB-view layer, not per-source.
- **Croissant, BIDS** — wrong domains.

**Why this is not "stay native and hope for the best":** Every field in §"Add proactively" is one we want anyway for our own queries (license-aware filtering, ORCID dedup, datePublished sorting). The RO-Crate `@context`+`@graph` shell is ~20 bytes of overhead per source. We're not adopting a standard; we're choosing field names that happen to be standard, which is free.

**The single trap to avoid:** keep `metadata.json` flat and queryable for *our* code. RO-Crate's `@graph` is a JSON array of typed nodes, which means looking up "license" requires walking the graph for the Root Data Entity. Wrap our reader: `metadata.root()` returns the dataset node, `metadata.files()` returns the file nodes. Internal callers never see `@graph` directly. This is the "RO-Crate-compatible bytes, ergonomic Python API" split — same pattern PaperQA2's corpus uses.

---

## Sources

- [OCFL 1.1 Specification](https://ocfl.io/1.1/spec/) — `inventory.json` mandatory fields, Namaste declaration, version directory layout
- [OCFL on GitHub](https://github.com/OCFL/spec) — editorial group, institutional originators (Cornell, Stanford, DuraSpace, Oxford, Emory)
- [The Oxford Common File Layout: A Common Approach to Digital Preservation (MDPI, 2019)](https://www.mdpi.com/2304-6775/7/2/39) — design rationale (completeness, parsability, robustness, versioning, storage independence)
- [ocfl-py on PyPI](https://pypi.org/project/ocfl-py/) — reference Python impl, "limited popularity" (158 weekly downloads) — maturity caveat
- [rocfl (Rust CLI)](https://github.com/pwinckles/rocfl) — Rust impl, S3 support, pre-built binaries
- [RFC 8493 — The BagIt File Packaging Format (V1.0)](https://datatracker.ietf.org/doc/html/rfc8493) — `data/` + `manifest-<algo>.txt` + `bagit.txt` spec, LoC authorship
- [BagIt on Wikipedia](https://en.wikipedia.org/wiki/BagIt) — institutional adoption (DataONE, Dryad, Rockefeller)
- [RO-Crate 1.1 Metadata Specification](https://www.researchobject.org/ro-crate/specification/1.1/metadata.html) — JSON-LD format, ro-crate-metadata.json, schema.org vocab
- [RO-Crate 1.1 Structure](https://www.researchobject.org/ro-crate/specification/1.1/structure.html) — root-only metadata file, no directory mandate
- [RO-Crate 1.2 Specification (Zenodo)](https://zenodo.org/records/13751027) — current published version
- [ro-crate-py Python library](https://github.com/ResearchObject/ro-crate-py) — Python reference impl, FAIR Signposting integration (2025)
- [bagit-ro — Research Object BagIt archive](https://github.com/ResearchObject/bagit-ro) — formal combo pattern of RO-Crate inside BagIt
- [Packaging research artefacts with RO-Crate (Peroni et al., 2022)](https://content.iospress.com/articles/data-science/ds210053) — design rationale + BagIt separation of concerns
- [FAIR Signposting + RO-Crate (FAIR-IMPACT)](https://fair-impact.eu/support-offer-2-enabling-fair-signposting-and-ro-crate-contentmetadata-discovery-and-consumption) — 2025 adoption update
- [Frictionless Data Package spec](https://specs.frictionlessdata.io/) — datapackage.json + tabular resources
- [Tabular Data Package](https://old.frictionlessdata.io/specs/tabular-data-package/) — tabular-CSV scope confirmation
- [Zenodo deposit documentation](https://help.zenodo.org/docs/deposit/) — DOI registration, 50GB limit, ZIP support
- [Zenodo developers API](https://developers.zenodo.org/) — `.zenodo.json` metadata format
- [PMC FTP service / OA bulk layout](https://pmc.ncbi.nlm.nih.gov/tools/ftp/) — 2-level hash-bucket directory structure for `oa_package/`
- [PMC OA Subset on AWS](https://registry.opendata.aws/ncbi-pmc/) — NXML + PDF + media bundling
- [DCAT-3 W3C Recommendation](https://www.w3.org/TR/vocab-dcat-3/) — catalog vocabulary, dcat:Catalog/Dataset/Distribution
- [DCAT vs RO-Crate analysis](https://www.researchobject.org/initiative/data-catalog-vocabulary-dcat/) — DCAT for catalogs, RO-Crate for packages
- [BIDS 1.11.1 — Brain Imaging Data Structure](https://bids-specification.readthedocs.io/en/stable/common-principles.html) — sidecar JSON pattern
- [BIDS Scientific Data paper (Gorgolewski et al., 2016)](https://www.nature.com/articles/sdata201644) — adoption + design rationale
- [Croissant: A Metadata Format for ML-Ready Datasets (arxiv:2403.19546)](https://arxiv.org/abs/2403.19546) — ML-specific, schema.org-derived
- [Croissant Format Specification](https://docs.mlcommons.org/croissant/docs/croissant-spec.html) — RecordSet/Field framing
- [Workflow RO-Crate profile 1.0 (WorkflowHub)](https://about.workflowhub.eu/Workflow-RO-Crate/) — relevant if we ever profile parsed.<parser_id>/ as workflow output
- [research/scientific-substrate-target-architecture.md](file:///Users/alien/Projects/agent-infra/research/scientific-substrate-target-architecture.md) — Q3 atomic append, append-only JSONL provenance model
- [research/prior-art-2026-05-11/04-reusable-packaging.md](file:///Users/alien/Projects/agent-infra/research/prior-art-2026-05-11/04-reusable-packaging.md) — workspace/identity context

<!-- knowledge-index
generated: 2026-05-11T07:46:34Z
hash: b5c4d9a30fe2

title: On-Disk Layout Standards for `~/Projects/corpus/`
status: research-memo
tags: corpus, on-disk-layout, ocfl, bagit, ro-crate, frictionless, preservation, fair
cross_refs: research/prior-art-2026-05-11/04-reusable-packaging.md, research/prior-art-2026-05-11/04-reusable-packaging.md](file:///Users/alien/Projects/agent-infra/research/prior-art-2026-05-11/04-reusable-packaging.md, research/scientific-substrate-target-architecture.md, research/scientific-substrate-target-architecture.md](file:///Users/alien/Projects/agent-infra/research/scientific-substrate-target-architecture.md

end-knowledge-index -->
