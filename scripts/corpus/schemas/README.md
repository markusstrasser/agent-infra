# corpus schemas

JSON Schemas for the corpus substrate. Layered by SchemaVer version.

## SchemaVer convention

`schema_version` follows **SchemaVer** (`MODEL-REVISION-ADDITION`), **not** SemVer.

| Bump | Meaning | Reader impact | Writer obligation |
|---|---|---|---|
| **MODEL** (`1-0-0` → `2-0-0`) | Breaking change to existing field semantics or required fields. | Old readers MUST refuse new records. | New writers MUST emit only at the new MODEL. |
| **REVISION** (`1-0-0` → `1-1-0`) | Backward-incompatible to old readers; forward-compatible to new. | Old readers may produce wrong results — refuse. | New writers may emit only at the new REVISION. |
| **ADDITION** (`1-0-0` → `1-0-1`) | Additive only — new optional fields. | Old readers ignore unknown fields and stay correct. | New writers may emit at the new ADDITION freely. |

A MODEL bump triggers a DuckDB `annotations` projection rebuild in Phase 2.

## Layout

```
schemas/
└── v1/
    ├── annotation.v1.json   # per-source annotations.jsonl record schema
    ├── source_record.v1.json # per-source metadata.json schema
    ├── claim.v1.json         # per-repo MCP claims_for_source(...) return shape
    └── verdict.v1.json       # per-repo MCP verdicts_for_claim / record_verdict shape
```

When v2 exists, it lives at `schemas/v2/` alongside v1 — old records remain readable
against v1 indefinitely.

## Phase 1 ships v1 only

Pydantic v2 discriminated-union upcasters for read-time schema-version dispatch are
deliberately **deferred** (per plan §J.6). The SchemaVer convention and the
`schemas/v{N}/` directory layout are the contract; the upcaster machinery is built
when there is an actual v2 to upcast to. Don't build speculative migration plumbing.

## Per-record `conformsTo`

Annotation records MUST carry `conformsTo: "https://schema.local/corpus/annotation/v1.0.0"`
(or the matching URI for the v2 record's MODEL). Readers route by `conformsTo` first
(more reliable than file location) and fall back to `schema_version` for legacy records.

## Identity invariant

Every content-addressed identity in the corpus is derived as
`sha256_hex(canonical_json(stable_tuple))`. `canonical_json` is the
sorted-keys / compact-separators / UTF-8 JSON encoding (RFC 8785 JCS profile;
see `corpus_core/identity.py`).

This matches `phenome/identity/canonicalize.py` byte-for-byte on the inputs we
emit — verified in test fixtures in both repos.
