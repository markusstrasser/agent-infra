# `~/Projects/corpus/` — Canonical corpus store schema

Single source of truth for layout, identity, and revision policy.

> **Storage invariant:** the corpus store MUST live on a local POSIX filesystem.
> NFS/SMB are not supported (atomic-append guarantees rely on local kernel POSIX semantics).

## Layout

```
~/Projects/corpus/
  <source_id>/
    metadata.json              # SINGLE authority — doi, pmid, title, authors,
                               # retrieved_at, pdf_sha256, parsed_sha256,
                               # citation_context_event_sha256, parser.json (current),
                               # revisions: [{retired_at, prior_pdf_sha256,
                               #              prior_parsed_sha256}, ...],
                               # fabio_class, wikidata_qid, openalex_id,
                               # contributions: [{contribution_id, claim_text,
                               #                  supporting_blocks: [...]}]
    paper.pdf                  # current canonical PDF (paper-typed sources)
    paper.<sha_prefix>.pdf     # prior revisions, archived
    parsed.<parser_id>/        # immutable per parser_id version (Phase 1.5)
      page.md
      page_meta.json
      _page_N_Figure_M.jpeg
      parsed.sha256
      parser.json              # {parser_id, parser_version, llm, ts, config_md5}
    citation_context/
      scite_response.json
      openalex_response.json
      pubmed_response.json
      crossref_response.json
      latest_event.json        # CitationContextEvidence event
    citances_in.jsonl          # DERIVED — sources citing THIS source
    citances_out.jsonl         # DERIVED — sources THIS source cites
    references_resolved.json   # DERIVED — reference-string → (doi, pmid)
    annotations.jsonl          # APPEND-ONLY — per-source observations (Phase 1)
    INDEX.json                 # DERIVED cache — {source_id, used_by: [...]}
  graph.duckdb                 # corpus-wide graph + annotations index (Layer 4)
  collections/<name>.txt       # newline-delimited source_ids
  scoring/                     # optional ranking lookup tables
  tables/<schema_id>.parquet   # cross-source extraction cache
```

## Source identity rule

`source_id` is **DOI-based when a DOI exists**, otherwise PMID, otherwise content
SHA-256. It is **stable for the life of the source, including reissues**.

| Source | `source_id` |
|---|---|
| has DOI | `doi_<slugified_doi>` (e.g. `doi_10_1097_fpc_0000000000000456`) |
| has PMID, no DOI | `pmid_<pmid>` |
| neither | `sha_<sha256[:16]>` |

### DOI slugification

The DOI is lowercased, then non-alphanumerics are replaced with `_`, then
consecutive `_` are collapsed, trailing `_` stripped:

```
10.1097/FPC.0000000000000456 → 10_1097_fpc_0000000000000456
```

Final source_id: `doi_10_1097_fpc_0000000000000456`.

### DOI slug collision handling

`slug(doi)` normalizes punctuation, which can collapse distinct DOIs.
Before materializing a new `source_id`, ingest queries the filesystem for any
existing `source_id == doi_<slug>` whose `metadata.json.doi != raw_doi`. If a
collision is found, ingest **fails closed** with the collision pair printed.
The operator disambiguates by appending `__sha_<prefix>` to the new id:

```
doi_10_1097_fpc_0000000000000456__sha_4f2a
```

## Reissue / revision policy

Reissues are versions inside the same `source_id`, not new `source_id`s. When
ingest sees a different `pdf_sha256` for the same source_id:

1. Current `paper.pdf` is renamed to `paper.<old_sha_prefix>.pdf` (archive).
2. The new PDF lands as `paper.pdf`.
3. Current `parsed.<parser_id>/` stays in place (already immutable per Phase 1.5).
4. Reparse runs into a new `parsed.<new_parser_id>/`.
5. `metadata.json.revisions` gets a new entry
   `{retired_at, prior_pdf_sha256, prior_parsed_sha256}`.
6. `metadata.json.pdf_sha256` / `parsed_sha256` update to the new values.

Consumers' `claim_binding_hash` flips → freshness gate catches stale verdicts
→ claims re-enter the verifier queue.

## Immutability rule for parsed bundles

Once `parsed.sha256` is written to a `parsed.<parser_id>/` directory, that directory
is immutable. Re-parses go to a new `parsed.<new_parser_id>/`, and `metadata.json`
records which `parser_id` is current. Existing verdicts keyed to an old
`parsed.sha256` can still resolve their evidence by looking up the archived
`parsed.<old_parser_id>/` directory until they are re-verified.

## License policy

Extractor and parser dependencies must be Apache-2.0, MIT, or BSD by preference.
AGPL-3.0 is acceptable for local-only personal use; the AGPL network clause means
AGPL-licensed code MUST NOT be deployed behind a public network endpoint.
GPL-3.0 is prohibited (this is why Marker was dropped in Phase 1.5).

## `parser.json` shape

```json
{
  "parser_id": "mineru@<version>+cfg-<md5[:8]>",
  "parser_version": "<version>",
  "llm_service": null,
  "config_md5": "<md5 of frozen config dict>",
  "ts": "2026-05-11T10:23:00Z"
}
```

`config_md5` is the PaperQA2 `PQASession.config_md5` reproducibility pattern.

## Layer 2 citance schema

See `citances_{in,out}.jsonl` schemas in the substrate plan at
`~/Projects/agent-infra/.claude/plans/2026-05-11-substrate-migration.md`.

Key invariants:
- `stance_cito` stores **full PURL strings** (e.g.
  `http://purl.org/spar/cito/supports`), not abbreviated prefixes.
- `citance_id = sha256(normalized_snippet)[:16]`.
- Edges A←B appear in both A's `citances_in.jsonl` and B's
  `citances_out.jsonl`. This redundancy is deliberate; per-source
  directories are self-contained for inspection.

## Schema version

`SCHEMA_VERSION = "1.0.0"` — bump on any breaking change to filenames,
metadata keys, or source_id derivation. Recorded in
`metadata.json.schema_version`.
