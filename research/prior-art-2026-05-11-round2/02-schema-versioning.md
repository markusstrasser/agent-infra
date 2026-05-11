# Schema Versioning for a 10-Year-Lived Scientific Corpus

**Context:** Per-source JSONL files (append-only) + DuckDB derived index (rebuildable) + per-repo claim/verdict stores. Single user today, AI agent developers as primary maintainers, possibly reusable later. Current state: `schema_version: "1.0.0"` + `$schema` URI on each record.

## TL;DR — recommended versioning pattern

**Adopt: SchemaVer (MODEL-REVISION-ADDITION) + JSON Schema + `$schema` URI per record + in-corpus `schemas/v{N}/` directory + Pydantic v2 discriminated-union upcasters.** This is the smallest pattern that gets you Iceberg-style guarantees without Iceberg-style overhead.

Concretely:
- Keep `schema_version` as a record field (you already have it).
- Migrate from SemVer (`1.0.0`) to **SchemaVer** (`1-0-0`) — semver does not describe schema compatibility ([Snowplow][1]).
- Treat the `$schema` URI as the authoritative pointer (matches Iceberg's "schema is the catalog" stance and JSON Schema 2026's dialect mechanism).
- Don't migrate JSONL files. JSONL is your append-only ledger; migration runs at **read time** via upcasters that target the latest model. The DuckDB index is rebuilt from the latest read view.
- Field IDs are unnecessary for JSON (steal the *behavior* from Iceberg, not the mechanism).
- Reject Avro/Protobuf/Iceberg as direct dependencies — overkill for single-user JSONL.

## Comparison matrix

| Pattern | Migration story | Runtime check | Tooling | Scientific adoption |
|---|---|---|---|---|
| **Iceberg schema evolution** | Metadata-only ops on the catalog; field IDs decouple name from identity. ADD/DROP/RENAME/REORDER all safe ([Apache Iceberg][2]) | Read-side ID resolution (writer-schema vs reader-schema) | Catalog server + manifest files + Spark/Flink/Trino | Heavy lakehouse use; almost none in single-user scientific archives |
| **Avro + Schema Registry** | Reader/writer schemas, registry checks BACKWARD/FORWARD/FULL on each schema submission ([Confluent][3]) | Strong: registry rejects incompatible changes; reader uses both schemas to project | Confluent SR (server), python-schema-registry-client | Kafka ecosystem; almost zero in scientific corpora |
| **Protocol Buffers (proto3/editions)** | Field numbers immutable; `reserved` keyword prevents reuse; optional-by-default in proto3 ([protobuf.dev][4]) | Numbers, not names — old code reads new wire format and ignores unknown numbers | `protoc` + per-language codegen | High in genomics interchange (htslib, GA4GH `htsget`, VCF tooling at byte level), low in agent corpora |
| **JSON Schema + `$schema` URI side-by-side** | `$schema` declares dialect; multiple schema versions coexist as separate URIs; readers select handler by URI ([json-schema.org][5]) | Python `jsonschema` + `referencing.Registry` loads schemas from local files, validates without network ([python-jsonschema][6]) | Standardized, no server; v1/2026 spec adds backward/forward-compat guarantees ([json-schema.org][5]) | Increasing — datapackage.json (Frictionless), CITATION.cff, RO-Crate all use $schema URIs |
| **Frictionless Data Package** | `version` (SemVer) on the package + `$schema` on resource/table-schema; explicit Migration Guide from v1 → Framework ([datapackage.org][7]) | Tooling validates package against table-schema; Python `frictionless` lib | `frictionless` Python (active) | High in social-sci/epi/clinical research ([Frictionless][8]) |
| **W3C Verifiable Credentials `@context`** | Each credential lists a JSON-LD `@context` URI; verifier resolves contexts in order; new context versions get new URIs | JSON-LD framing + signature over canonicalized context | VC libs (didkit, etc.); requires JSON-LD processor | Niche outside SSI; over-engineered for non-credential data |
| **Pydantic v2 versioned models** | Discriminated unions on `schema_version`; `@model_validator(mode='before')` runs upcaster ([Pydantic][9]) | Pure Python validation at read; serializes back to latest model | Pydantic v2 + bump-pydantic (codegen aid) | Widely adopted as the Python validation default; scientific tools (LinkML, OME-NGFF) increasingly target it |
| **Iceberg / Avro / Proto for a JSONL corpus** | (Not applicable — added for rejection) | (See "What I'd reject") | Heavy | None — wrong tool class |

## Recommendation + concrete migration template

### Directory layout (in-corpus)

```
scientific-corpus/
  data/                              # append-only JSONL
    sources/2026-05-11/source.jsonl  # records carry $schema URI + schema_version
    annotations/...
  schemas/
    v1/
      annotation.schema.json         # $id: https://corpus.local/schemas/v1/annotation
      source_record.schema.json
    v2/
      annotation.schema.json         # NEW shape; $id: .../v2/annotation
      source_record.schema.json
    migrations/
      v1_to_v2/
        annotation_upcast.py         # Pydantic upcaster, NO file rewrite
        README.md                    # Why v2, what changed, irreversible bits
        rebuild.py                   # rebuild DuckDB index post-cutover
  models/
    annotation.py                    # latest Pydantic model + Annotated discriminated union
```

### Versioning rules (SchemaVer adapted)

- **ADDITION** (`1-0-N`): new optional field. Old readers ignore; old data validates against new schema. No upcaster needed; bump `schema_version` only on new writes.
- **REVISION** (`1-N-0`): change to existing field that breaks SOME historical data (tighter validation, new enum value made required). Requires upcaster registered.
- **MODEL** (`N-0-0`): breaking shape change. New `schemas/v{N}/` directory. Upcaster mandatory. DuckDB index rebuilt from upcaster output.

### Pydantic upcaster pattern (the migration template)

```python
# models/annotation.py
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, Discriminator, model_validator

class AnnotationV1(BaseModel):
    schema_version: Literal["1-0-0", "1-0-1"]
    claim: str
    confidence: float           # 0..1

class AnnotationV2(BaseModel):
    schema_version: Literal["2-0-0"]
    claim: str
    confidence: float
    provenance: dict            # new mandatory field
    grade: Literal["A","B","C","D"] | None = None

    @model_validator(mode="before")
    @classmethod
    def upcast_from_v1(cls, data):
        if isinstance(data, dict) and data.get("schema_version", "").startswith("1-"):
            data = {**data,
                    "schema_version": "2-0-0",
                    "provenance": {"upcast_from": data["schema_version"]},
                    "grade": None}
        return data

Annotation = Annotated[
    Union[AnnotationV1, AnnotationV2],
    Discriminator("schema_version"),
]
```

This is the entire migration story:
1. JSONL files are never rewritten (append-only invariant preserved).
2. Readers always load through `Annotation` — Pydantic discriminates on `schema_version`, upcaster runs.
3. DuckDB index ingests the upcast view; rebuild on `MODEL` bumps.
4. A per-repo MCP on schema v1 keeps working — it reads its own `AnnotationV1` shape. When you want it on v2, point it at the same model module and the upcaster handles the rest. **Adapter pattern, not hard-cutover.**

### Side-by-side `$schema` URIs

Each JSONL record keeps `"$schema": "https://corpus.local/schemas/v2/annotation"`. The `referencing.Registry` resolves URIs to local files in `schemas/` ([python-jsonschema][6]) — zero network, fully offline. Validation is identity-checked by URI, not name.

### Migration scripts: in-corpus, not out-of-band

Iceberg keeps migration operations *in the catalog manifest* — they travel with the data ([Apache Iceberg][2]). Avro/Confluent keeps them in the *registry* (an external service). Alembic puts them in a `versions/` directory inside the repo ([Alembic][10]). For a single-user JSONL corpus, the Alembic convention wins:

- `schemas/migrations/v{N}_to_v{N+1}/` directories with the upcaster + README + rebuild script.
- A `MIGRATION_LOG.md` at repo root, append-only, one entry per MODEL bump with date, rationale, irreversibility notes.
- The upcasters are tested. The rebuild script is idempotent.

### Per-repo MCP at v1 while corpus is at v2

**Adapter, not cutover.** The downstream MCP imports the corpus models package. As long as `AnnotationV1` stays in the discriminated union, the v1 MCP reads v1 records natively and never sees v2 records (they validate as `AnnotationV2`, which the MCP's downstream code ignores or fails fast on). When the MCP catches up, it widens its handler to `Annotation` and gets v1 + v2 for free. This is what discriminated unions are for. Hard-cutover is only acceptable when the v1 shape is genuinely irrecoverable.

### "Schema-evolution-as-a-service" library

Don't adopt a Python library claiming to "do schema evolution for you" — the ones that exist are Confluent-Registry clients, not local-corpus tools. The right stack is:
- **`jsonschema` + `referencing`** for $schema URI resolution and validation ([python-jsonschema][6])
- **Pydantic v2** for discriminated-union upcasters ([Pydantic][9])
- **`check-jsonschema`** as a pre-commit hook (optional)
- **`frictionless`** if you ever publish the corpus as a Data Package (defer)

Roll your own upcaster *registry* (a 30-line module mapping version strings → upcaster fns). That is the only custom piece, and it's deliberately small.

## What I'd reject and why

- **Avro + Schema Registry for a single-user JSONL corpus.** Registry is a network service. Compatibility checks are useful but Pydantic discriminated unions give you the same guarantee in pure Python with less moving parts. The whole point of JSONL is "human readable, grep-able" — Avro's binary framing destroys that. Adopt Avro only if/when you're streaming to Kafka or hitting GB/s write rates. You're not.
- **Protocol Buffers.** Same critique — binary on disk, codegen step, field-number bookkeeping. For wire formats between services, sure. For a 10-year-lived scientific archive whose primary value is "still readable in 10 years by `cat | jq`", proto3 is the wrong tradeoff.
- **Apache Iceberg directly.** You're not running Spark. The data volume doesn't justify a metastore. Adopt the *ideas* (additive-first, name-renames are metadata not data ops, schema lives next to data) without the implementation. If volumes ever justify Iceberg, DuckDB has an Iceberg reader and you can migrate the *index*, not the corpus.
- **W3C Verifiable Credentials `@context`.** JSON-LD's framing and canonicalization rules are excellent for cryptographically signed credentials. They are dead weight for non-credential scientific records. The `@context` versioning idea (URIs, not version numbers) is already covered by `$schema`.
- **SemVer for schemas.** SchemaVer (MODEL-REVISION-ADDITION) is the right abstraction because "patch" doesn't exist for schemas — there's nothing to fix without changing meaning ([Snowplow][1]). Migrate the existing `1.0.0` → `1-0-0` in a single sweep.
- **Field IDs (Iceberg-style) for JSON.** They solve the rename-without-rewrite problem. For JSONL you have no rewrite anyway (append-only), and renames are rare. The overhead of carrying numeric IDs in every record is not worth it.
- **Out-of-band migration scripts.** Migrations belong next to the schemas they migrate. Hidden migration tooling is the #1 cause of "schema drift that nobody can reproduce 3 years later."

## Sources

- [Snowplow — Introducing SchemaVer for semantic versioning of schemas][1]
- [Apache Iceberg — Schema Evolution docs][2]
- [Confluent — Schema Evolution and Compatibility][3]
- [Protocol Buffers — Language Guide (proto3)][4]
- [JSON Schema — Dialect and vocabulary declaration / v1/2026 in development][5]
- [python-jsonschema — JSON (Schema) Referencing / local file registries][6]
- [Frictionless Data — Data Package Standard changelog (v2 / `$schema`)][7]
- [Frictionless Data Package specification][8]
- [Pydantic — Discriminated Unions / Validators][9]
- [Alembic — Tutorial (versions/ directory convention)][10]


<!-- knowledge-index
generated: 2026-05-11T07:44:57Z
hash: e7c36093067d


end-knowledge-index -->

[1]: https://snowplow.io/blog/introducing-schemaver-for-semantic-versioning-of-schemas
[2]: https://iceberg.apache.org/docs/latest/evolution/
[3]: https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html
[4]: https://protobuf.dev/programming-guides/proto3/
[5]: https://json-schema.org/understanding-json-schema/reference/schema
[6]: https://python-jsonschema.readthedocs.io/en/stable/referencing/
[7]: https://datapackage.org/overview/changelog/
[8]: https://specs.frictionlessdata.io/
[9]: https://docs.pydantic.dev/latest/concepts/unions/
[10]: https://alembic.sqlalchemy.org/en/latest/tutorial.html