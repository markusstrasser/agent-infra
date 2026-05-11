# `~/Projects/papers/` — Canonical paper store schema

Single source of truth for layout, identity, and revision policy.

## Layout

```
~/Projects/papers/
  <paper_id>/
    metadata.json              # SINGLE authority — doi, pmid, title, authors,
                               # retrieved_at, pdf_sha256, parsed_sha256,
                               # citation_context_event_sha256, parser.json (current),
                               # revisions: [{retired_at, prior_pdf_sha256,
                               #              prior_parsed_sha256}, ...],
                               # fabio_class, wikidata_qid, openalex_id,
                               # contributions: [{contribution_id, claim_text,
                               #                  supporting_blocks: [...]}]
    paper.pdf                  # current canonical PDF
    paper.<sha_prefix>.pdf     # prior revisions, archived
    parsed/                    # immutable per parser_id version
      paper.md
      paper_meta.json
      _page_N_Figure_M.jpeg
      parsed.sha256
      parser.json              # {marker, surya, llm, ts, config_md5}
    parsed.<parser_id>/        # prior parser versions; never mutated
    citation_context/
      scite_response.json
      openalex_response.json
      pubmed_response.json
      crossref_response.json
      latest_event.json        # CitationContextEvidence event
    citances_in.jsonl          # DERIVED — papers citing THIS paper
    citances_out.jsonl         # DERIVED — papers THIS paper cites
    references_resolved.json   # DERIVED — reference-string → (doi, pmid)
    annotations.jsonl          # APPEND-ONLY — paper-level observations
    INDEX.json                 # DERIVED cache — {paper_id, used_by: [...]}
  graph.duckdb                 # corpus-wide graph index (Layer 4)
  collections/<name>.txt       # newline-delimited paper_ids
  scoring/                     # optional ranking lookup tables
  tables/<schema_id>.parquet   # Elicit-style cross-paper extraction cache
```

## Paper identity rule

`paper_id` is **DOI-based when a DOI exists**, otherwise PMID, otherwise PDF
SHA-256. It is **stable for the life of the paper, including reissues**.

| Source | `paper_id` |
|---|---|
| has DOI | `doi_<slugified_doi>` (e.g. `doi_10_1097_FPC_0000000000000456`) |
| has PMID, no DOI | `pmid_<pmid>` |
| neither | `sha_<sha256[:16]>` |

### DOI slugification

The DOI is lowercased, then non-alphanumerics are replaced with `_`, then
consecutive `_` are collapsed, trailing `_` stripped:

```
10.1097/FPC.0000000000000456 → 10_1097_fpc_0000000000000456
```

Final paper_id: `doi_10_1097_fpc_0000000000000456`.

### DOI slug collision handling

`slug(doi)` normalizes punctuation, which can collapse distinct DOIs.
Before materializing a new `paper_id`, ingest queries the filesystem for any
existing `paper_id == doi_<slug>` whose `metadata.json.doi != raw_doi`. If a
collision is found, ingest **fails closed** with the collision pair printed.
The operator disambiguates by appending `__sha_<prefix>` to the new id:

```
doi_10_1097_fpc_0000000000000456__sha_4f2a
```

## Reissue / revision policy

Reissues are versions inside the same `paper_id`, not new `paper_id`s. When
ingest sees a different `pdf_sha256` for the same paper_id:

1. Current `paper.pdf` is renamed to `paper.<old_sha_prefix>.pdf` (archive).
2. The new PDF lands as `paper.pdf`.
3. Current `parsed/` is renamed to `parsed.<old_parser_id>/`.
4. Reparse runs; new `parsed/` is written.
5. `metadata.json.revisions` gets a new entry
   `{retired_at, prior_pdf_sha256, prior_parsed_sha256}`.
6. `metadata.json.pdf_sha256` / `parsed_sha256` update to the new values.

Consumers' `claim_binding_hash` flips → freshness gate catches stale verdicts
→ claims re-enter the verifier queue.

## Immutability rule for parsed bundles

Marker output with `--use_llm` is not bit-deterministic across runs (Gemini
sampling). Once `parsed.sha256` is written, `parsed/` is immutable: re-runs
go to `parsed.<new_parser_id>/`, and `metadata.json` records which
`parser_id` is current. Existing verdicts keyed to an old `parsed.sha256`
can still resolve their evidence by looking up the archived
`parsed.<old_parser_id>/` directory until they are re-verified.

## `parser.json` shape

```json
{
  "parser_id": "marker-1.2.3+surya-0.4.0+llm-gemini-flash+cfg-<md5[:8]>",
  "marker_version": "1.2.3",
  "surya_version": "0.4.0",
  "llm_service": "marker.services.gemini.GoogleGeminiService" | null,
  "config_md5": "<md5 of frozen config dict>",
  "page_range_chunk": 3,
  "ts": "2026-05-11T10:23:00Z"
}
```

`config_md5` is the PaperQA2 `PQASession.config_md5` reproducibility pattern.

## Layer 2 citance schema

See `citances_{in,out}.jsonl` schemas in the plan at
`~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md`,
section "Citance, annotation, and graph layer".

Key invariants:
- `stance_cito` stores **full PURL strings** (e.g.
  `http://purl.org/spar/cito/supports`), not abbreviated prefixes.
- `citance_id = sha256(normalized_snippet)[:16]`.
- Edges A←B appear in both A's `citances_in.jsonl` and B's
  `citances_out.jsonl`. This redundancy is deliberate; per-paper
  directories are self-contained for inspection.

## Schema version

`SCHEMA_VERSION = "1.0.0"` — bump on any breaking change to filenames,
metadata keys, or paper_id derivation. Recorded in
`metadata.json.schema_version`.
