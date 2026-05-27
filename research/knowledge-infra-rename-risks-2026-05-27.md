# Knowledge Infrastructure Rename Risks — Iatrogenic Failure Modes

**Date:** 2026-05-27
**Scope:** Six architectural moves on corpus knowledge substrate (annotations table rename, JSONL field rename, legacy fallback deletion, PROV-O naming verification, JSONL replay rebuild, table-rename precedents).
**Confidence legend:** [CONFIRMED] = documented in primary source / standard. [STRONG] = multiple independent sources agree. [SPECULATION] = informed inference, no direct citation.

## Executive Summary (200 words)

Five of the six moves carry real iatrogenic risk; one (#4 PROV-O) is a naming claim that needs revision. **The single biggest landmine is move #2:** renaming `output_uri → generated_uri` will mutate `annotation_id` for every replayed event because the URI participates in the stable tuple. Every annotation re-emitted post-rename produces a duplicate row with a new ID. The fix is field aliases at the deserialization boundary (Avro/Protobuf precedent) — change the wire/code name but keep the canonical hash input string `"output_uri"`. **Move #1 has a DuckDB-specific blocker:** views and tables cannot share a name in the same schema, and DuckDB has no triggers (no INSTEAD OF support) — the "view named `annotations` that filters current state" pattern as described is structurally impossible in DuckDB. Use a different name (`annotations_current`) and migrate the readers. **Move #3 (deleting legacy fallback) is safe ONLY if you simultaneously add a schema-version preflight that fails loud with the bad file's path** — bare BinderException is uninformative. **Move #4: revise the naming claim** — PROV vocabulary doesn't bless `generated_uri`; idiomatic options are `entity_uri` (the generated entity's IRI) or keep `output_uri`. **Moves #5, #6 (replay, precedents) carry standard gotchas, well-documented.**

Recommendation: **defer rename of `output_uri` to a separate phase after stable-tuple decoupling** (introduce a `hash_input_alias_map` so the canonical hashed string is decoupled from the in-code field name). Adopt expand-contract for the table rename. Do not delete fallback paths without a version-stamped preflight.

---

## Move 1: Rename `annotations` → `annotations_log` + CREATE VIEW `annotations`

### Hard blocker (DuckDB-specific)

[CONFIRMED — DuckDB docs] **"The name of a view must be distinct from the name of any other view or table in the same schema."** ([CREATE VIEW Statement – DuckDB](https://duckdb.org/docs/lts/sql/statements/create_view)). You cannot create a view named `annotations` while a table of any name occupies that slot if it's in the same schema — but since the table is being renamed to `annotations_log`, the slot is freed, so this constraint is satisfied. The blocker is downstream.

[CONFIRMED — DuckDB discussion #12562] **DuckDB does not support triggers.** "It is normal for DuckDB not to have triggers, as none of the columnar databases have triggers. The data in the columns is stored by compression, which makes it very difficult to support triggers." ([Triggers · duckdb/duckdb · Discussion #12562](https://github.com/duckdb/duckdb/discussions/12562))

**Consequence:** No `INSTEAD OF INSERT` trigger can route writes from the view back to `annotations_log`. **Any code path `INSERT INTO annotations (...)` will fail at runtime** with a "cannot insert into view" error.

### What breaks immediately

| Surface | Behavior post-rename |
|---|---|
| `INSERT INTO annotations VALUES (...)` | **Hard error** — DuckDB rejects writes to views |
| `SELECT * FROM annotations WHERE ...` | Works (view query) |
| `PRAGMA table_info('annotations')` | [SPECULATION] Likely returns view columns; some tooling may inspect view definition instead. Verify before relying on it. |
| `CREATE OR REPLACE TABLE annotations ...` | Fails — DuckDB issue [#12191](https://github.com/duckdb/duckdb/issues/12191) shows `CREATE OR REPLACE` errors when downstream views reference the target |
| ORM introspection (sqlmodel, sqlalchemy) | [SPECULATION] May misclassify as table; UPDATE attempts will fail |
| Existing index on `annotations(idempotency_key)` | Index belongs to `annotations_log` after rename; queries through the view will still use it (DuckDB's optimizer pushes through view definitions). |

### Safer path

1. **Don't reuse the name.** Name the view `annotations_current` or `v_annotations`. Update readers explicitly.
2. **Or:** keep the physical table named `annotations` and add a separate `annotations_archive` for soft-deleted rows. The view-over-rename pattern is borrowed from Postgres where INSTEAD OF triggers make it transparent; DuckDB cannot replicate this.
3. **Migrate readers in a separate commit.** Find all `SELECT ... FROM annotations` callers via grep, rewrite to explicit `annotations_current` or `annotations_log` per their intent (current state vs full history). The implicit "view captures current state" magic costs you the ability to grep for "who reads history vs who reads current."

**Source-grade:** [CONFIRMED] — DuckDB docs + GitHub discussion are primary sources.

---

## Move 2: Rename `output_uri → generated_uri` (participates in idempotency_key)

### The landmine — annotation_id mutation

If `output_uri` is in the `annotation_stable_tuple` (per `corpus_core/identity.py`), then renaming this field at the **canonicalization layer** changes the hash input string. The hash function sees `("output_uri", "https://...")` today and `("generated_uri", "https://...")` post-rename. Different bytes → different hash → different `annotation_id`.

**Effect on rebuild from JSONL:**
- Old JSONL records carry `output_uri: <URI>`; new code writes `generated_uri: <URI>`
- If the canonical tuple's KEY name (not just the in-code variable name) changes → **every old record replayed produces a NEW annotation_id** that does not match the row already in DuckDB
- Result: duplicate rows, broken FKs from anything that references the old ID, drift between graph.duckdb and JSONL ground truth

### The standard pattern: aliases (decouple wire name from canonical key)

[CONFIRMED — multiple sources] Both Avro and Protobuf solved this exact problem:

- **Avro:** the `aliases` attribute on a renamed field — readers using the old schema continue to resolve. ([DZone: Avro/Protobuf Strategies That Don't Break Consumers](https://dzone.com/articles/schema-evolution-avro-protobuf-event-driven))
- **Protobuf:** field numbers are the stable wire identifier; **names can be renamed freely** because the wire format never carries them. ([Markaicode: ProtoBuf vs Avro](https://markaicode.com/protobuf-vs-avro-schema-evolution/))
- **Anti-pattern (explicit):** "'Rename' by deleting + adding breaks consumers and corrupts analytics."

### Translation to your situation (no Avro/Protobuf runtime)

You need an **explicit canonical-tuple alias map**. The fix:

```python
# corpus_core/identity.py
CANONICAL_FIELD_NAMES = {
    # in-code name → canonical hash-input name (NEVER changes)
    "generated_uri": "output_uri",   # alias added 2026-05-27
    "generated_hash": "output_hash",
}

def annotation_stable_tuple(record: dict) -> tuple:
    return tuple(
        (CANONICAL_FIELD_NAMES.get(k, k), record[k])
        for k in sorted(record)
        if k in STABLE_FIELDS
    )
```

This is the same idea as Avro aliases: the **on-disk / on-wire / in-hash name is frozen** even when the in-code identifier evolves. `annotation_id` stability is preserved.

**Verify before committing:** write a test that loads 100 historical JSONL records, computes `annotation_id` with both old and new code, and asserts equality.

**Source-grade:** [CONFIRMED] — schema-evolution literature is unanimous on this pattern.

### Secondary risk: JSONL re-deserialization

If you also rename the JSONL field name on disk (not just in-code), every old `.jsonl` file in the corpus archive has `"output_uri": "..."` lines that a new strict reader will reject or null-out. Your reader needs `output_uri` → `generated_uri` translation **at load time**, with the canonical hash still using the frozen name.

[STRONG] — direct extrapolation from Avro schema evolution.

---

## Move 3: Delete legacy-schema fallback paths

### The failure mode

```python
# Current
try:
    cur.execute("SELECT new_col_1, new_col_2 FROM annotations")
except duckdb.BinderException:
    cur.execute("SELECT old_col_1, old_col_2 FROM annotations")  # ← deleted

# After "no compat shims"
cur.execute("SELECT new_col_1, new_col_2 FROM annotations")
# → BinderException: column "new_col_1" not found
```

**Iatrogenic risk:** the rogue DB exists in environments you don't see — CI fixtures, archived backups, a developer's stale checkout, a third-party who pulled the repo last month. The error surface is `duckdb.BinderException: Referenced column "new_col_1" not found` — **no hint that this is a schema-version problem**. The on-call engineer sees a generic SQL error, doesn't know to look for old fixtures.

### Safer pattern — fail loud + informative

Add a one-shot schema version check at gateway init:

```python
SCHEMA_VERSION = 4
SCHEMA_VERSION_INTRODUCED = {
    4: {"required_columns": {"annotations": {"new_col_1", "new_col_2"}}},
}

def assert_schema_version(con, db_path):
    cols = {r[1] for r in con.execute("PRAGMA table_info('annotations')").fetchall()}
    required = SCHEMA_VERSION_INTRODUCED[SCHEMA_VERSION]["required_columns"]["annotations"]
    missing = required - cols
    if missing:
        raise SchemaVersionError(
            f"Database at {db_path} is on schema < v{SCHEMA_VERSION} "
            f"(missing columns: {missing}). "
            f"Rebuild from JSONL via `just rebuild-corpus` or migrate via "
            f"`scripts/migrate_schema.py --to v{SCHEMA_VERSION}`."
        )
```

This satisfies "no compat shims" (you removed the fallback execution path) while preserving operability when the rogue DB appears.

**Source-grade:** [STRONG] — pattern is standard in migration tools (Alembic, Flyway, Liquibase all do version-stamp preflight). Specific naming is [SPECULATION] from inference.

### Confirmed adjacent pattern

[CONFIRMED — Shopify Engineering] Shopify's [Safely Adding NOT NULL Columns](https://shopify.engineering/add-not-null-colums-to-database) post documents that schema changes are routed through the Large Hadron Migrator (LHM) which builds a shadow table + triggers + batch copy + atomic rename. The relevant takeaway: **production teams never delete the old path until they've shadow-validated**. "No compat shims" should mean "no behavioral compat shims," not "no version preflight."

---

## Move 4: PROV-O field naming — REVISE THE CLAIM

### What you claimed

`output_uri → generated_uri` matches PROV.

### What PROV-O actually says

[CONFIRMED — W3C PROV-O REC](https://www.w3.org/TR/prov-o/)] PROV-O property names are **relations between Entity and Activity**, not field names for "the URI of a generated thing":

| PROV term | Type | What it relates |
|---|---|---|
| `prov:wasGeneratedBy` | object property | Entity → Activity that generated it |
| `prov:generated` | object property | Activity → Entity it generated (inverse of above) |
| `prov:generatedAtTime` | data property | Entity → xsd:dateTime |
| `prov:qualifiedGeneration` | object property | Entity → Generation (n-ary qualifier) |
| `prov:Entity` | class | the thing |

[CONFIRMED] **There is no PROV-O term `prov:generatedUri` or property whose label means "URI of the generated entity."** In PROV-O, the entity itself **is** identified by its URI (the IRI of the `prov:Entity` instance). When you want to say "this artifact's URI is X," you say `:thing a prov:Entity` and `:thing` IS the URI.

### Idiomatic mapping for your domain

If your field is "URI of the thing this annotation generated," the closest PROV-aligned naming is:

| Your field intent | Better name (PROV-aligned) |
|---|---|
| URI of the generated entity | `entity_uri` or `generated_entity_uri` |
| Hash of the generated entity | `entity_hash` or `generated_entity_hash` |
| Activity that did the generation | `activity_id` (with `prov:wasGeneratedBy` semantics implicit) |

**Recommendation:**
- If you want PROV alignment, use **`entity_uri` / `entity_hash`** (the URI/hash of the `prov:Entity`).
- `generated_uri` is fine as a domain name but **don't claim it's PROV-O standard** — it isn't.
- If you keep `output_uri`, that's also fine; it's a plain-English domain name with no PROV pretense.

**Worst option:** rename to `generated_uri` AND claim PROV-O compliance — invented name with false provenance authority.

**Source-grade:** [CONFIRMED] — W3C PROV-O REC + ontology cross-reference both checked.

---

## Move 5: Replay-from-event-log gotchas

[STRONG] from event-sourcing literature ([Tianpan: Agent State as Event Stream](https://tianpan.co/blog/2026-04-10-agent-state-event-stream-immutable-event-sourcing), [OneUptime: Event Replay Strategies](https://oneuptime.com/blog/post/2026-01-30-event-replay-strategies/view)).

Known failure modes when you nuke graph.duckdb and rebuild from JSONL:

| Gotcha | How it manifests | Mitigation |
|---|---|---|
| **Ordering** | If files are read in filename order but events span multiple files with `recorded_at` interleaved, downstream order-sensitive state diverges | Sort by `(recorded_at, event_id)`; if `recorded_at` has ms precision and events collide, `event_id` is tiebreaker |
| **recorded_at reinterpretation** | Rebuild assigns `replayed_at` (now) instead of preserving original `recorded_at` | Make replay write `recorded_at` from the event, not the wall clock |
| **Idempotency-by-rebuild** | If annotation_id is stable AND insert uses ON CONFLICT DO NOTHING, rebuild is safe. Otherwise duplicates. | Verify INSERT pathway uses idempotency_key UNIQUE constraint + ON CONFLICT |
| **Unicode/encoding drift** | Old JSONL written by Python 3.9 with `ensure_ascii=False`, new code reads with strict utf-8: usually fine, but BOM-prefixed lines from Windows-written archives crash `json.loads` | Strip BOM in reader: `line.lstrip('﻿')` |
| **Malformed row tolerance** | One corrupt line → entire rebuild aborts | Per-line try/except with `malformed_lines.jsonl` quarantine; log line number + file |
| **Schema drift across years** | A 2024 record lacks `embedding_model_version`; new code requires it | Default-fill at deserialize; record `schema_version_observed` in audit table |
| **Field-order in stable tuple** | If `annotation_stable_tuple` iterates `record.items()` instead of `sorted(record.items())`, dict insertion order changes between Python versions → different hash | Always sort keys before hashing |
| **Floating-point in keys** | If any float (timestamp, score) is in the canonical tuple, repr differences across platforms → different hash | Round to fixed precision OR exclude floats from tuple |

**Source-grade:** [STRONG] — standard event-sourcing gotchas, well-documented across multiple sources.

---

## Move 6: "Rename a primary surface" — real precedents

### Stripe — Online migrations at scale

[CONFIRMED — [Stripe Blog](https://stripe.com/blog/online-migrations)] Stripe's playbook for migrating Subscriptions had **4 phases:**
1. Dual-write: new code writes both old and new schemas
2. Backfill: bulk-copy historical data into new schema
3. Dual-read with comparison: use GitHub's **Scientist** library to run both code paths in production, alert on divergence
4. Cut over reads, then remove old writes, then drop old schema

**Wish-I'd-done-differently signal:** Stripe explicitly built Scientist to catch behavioral drift between old/new paths — implying the failure mode they experienced was **"we cut over thinking the paths were equivalent and discovered subtle differences in production."**

**Application to your case:** before deleting fallback paths (Move #3), run dual-execution for a window and assert result equivalence. For corpus annotations, this means: after writing via new gateway, verify the resulting annotation_id matches what the old code would have produced. If you skip this, you find out via duplicate rows weeks later.

### Shopify — Large Hadron Migrator (LHM) / NOT NULL safety

[CONFIRMED — [Shopify Engineering](https://shopify.engineering/add-not-null-colums-to-database)] Shopify's pattern: shadow table + triggers + batch copy + atomic rename. The post-mortem-flavored finding was that **adding a NOT NULL column directly took locks long enough to cause outages even on "small" tables** because of write contention. Their fix: never alter in place; always shadow + swap.

**Application:** for the `annotations` rename, the safe operation is `ALTER TABLE annotations RENAME TO annotations_log` (an atomic catalog operation in DuckDB, no row movement). This is cheap. The expensive/risky part is the **reader migration**, not the rename itself.

### GitHub — gh-ost

[CONFIRMED — pattern documented across multiple sources] GitHub's `gh-ost` does triggerless shadow-table migrations via binlog. The relevant lesson for you isn't the binlog mechanism (DuckDB doesn't have one) but the principle: **separate the schema mutation from the cutover**, so you can abort late without rolling back data.

### Synthesized "wish-I'd-done-differently" list

1. **Renamed without dual-write window** → discovered behavioral differences in production
2. **Renamed canonical hash inputs together with the surface name** → idempotency broke silently
3. **Removed legacy fallback at the same time as introducing new schema** → couldn't roll back when bugs appeared
4. **Trusted "should be equivalent" without runtime comparison** → Scientist-style diff would have caught it

**Source-grade:** [CONFIRMED] for individual blog posts; synthesis is [STRONG] inference.

---

## Concrete recommendations

| Move | Verdict | Action |
|---|---|---|
| 1. Rename annotations + view | **Change the design** — view can't share table name + DuckDB has no triggers for INSTEAD OF routing. Use `annotations_current` view + explicit reader migration. | New design |
| 2. Rename output_uri | **Defer** until canonical-tuple alias map is in place. Without it, you re-id every replayed annotation. | Add `CANONICAL_FIELD_NAMES` first |
| 3. Delete fallback paths | **Safe with preflight.** Add schema-version assert with informative error. Don't ship a bare BinderException to the next on-call. | Add `assert_schema_version` |
| 4. PROV-O naming | **Revise claim.** `generated_uri` isn't a PROV term. Use `entity_uri` if you want PROV alignment, or keep `output_uri` plain. | Don't invent provenance authority |
| 5. JSONL replay | **Well-understood gotchas** — sort by `(recorded_at, event_id)`, preserve recorded_at, quarantine malformed lines, sorted-key tuple hashing | Apply checklist |
| 6. Precedents | **Dual-write + Scientist-style comparison** before cutover. The rename itself is cheap; the reader migration is where it bites. | Plan reader migration as separate phase |

---

## Sources

- [CREATE VIEW Statement – DuckDB](https://duckdb.org/docs/lts/sql/statements/create_view) — view name uniqueness constraint
- [DuckDB Triggers Discussion #12562](https://github.com/duckdb/duckdb/discussions/12562) — confirmed no trigger support
- [DuckDB Issue #12191](https://github.com/duckdb/duckdb/issues/12191) — CREATE OR REPLACE fails with downstream views
- [PROV-O: The PROV Ontology — W3C REC](https://www.w3.org/TR/prov-o/) — primary source for naming verification
- [The PROV Namespace — W3C](https://www.w3.org/ns/prov/) — namespace authority
- [DZone: Avro/Protobuf Schema Evolution Strategies](https://dzone.com/articles/schema-evolution-avro-protobuf-event-driven) — aliases pattern
- [Markaicode: ProtoBuf vs Avro Schema Evolution](https://markaicode.com/protobuf-vs-avro-schema-evolution/) — field-number stability
- [Expand and Contract Pattern — dev.to](https://dev.to/jp_fontenele4321/the-expand-and-contract-pattern-for-zero-downtime-migrations-445m)
- [Tim Wellhausen: Expand and Contract canonical paper](https://www.tim-wellhausen.de/papers/ExpandAndContract/ExpandAndContract.html)
- [Stripe: Online migrations at scale](https://stripe.com/blog/online-migrations) — Scientist library, 4-phase migration
- [Shopify: Safely Adding NOT NULL Columns](https://shopify.engineering/add-not-null-colums-to-database) — LHM shadow table pattern
- [Tianpan: Agent State as Event Stream](https://tianpan.co/blog/2026-04-10-agent-state-event-stream-immutable-event-sourcing) — event replay gotchas
- [OneUptime: Event Replay Strategies](https://oneuptime.com/blog/post/2026-01-30-event-replay-strategies/view) — deterministic replay

<!-- knowledge-index
generated: 2026-05-27T11:01:08Z
hash: 625a5a410ac5

table_claims: 2

end-knowledge-index -->
