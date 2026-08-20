---
id: 2026-08-20-agentlogs-source-record-provenance
concept: agentlogs-provenance-identity
repo: agent-infra
decision_date: 2026-08-20
recorded_date: 2026-08-20
provenance: contemporaneous
status: accepted
initial_leaning: prune orphaned per-import references more frequently
relations:
  - type: relates_to
    target: 2026-06-07-state-externalization-lens
---

# 2026-08-20: Key transcript provenance by source record

## Context

The live 19.7 GB `agentlogs.db` held 16.7 GB in `record_refs` and its unique
index. The database had about 999k events but an inferred 76.8M reference rows;
at most 1.46M distinct references were reachable from events, tool calls, and
file touches. Active append-only transcripts were imported hundreds of times
(maximum observed: 1,274). Event ingest skipped old sequence numbers, while
reference ingest inserted every raw line again under a fresh `import_id`.

The required invariant is: one raw source record has one durable locator,
regardless of how many times the growing source file is observed.

## Alternatives considered

1. **Shorter retention** — bounds the symptom by deleting history. Rejected:
   it discards the operator-input and correction corpus while leaving the
   amplification mechanism intact inside the retained window.
2. **More frequent orphan cleanup** — delete unreferenced rows after ingest.
   Rejected as the primary fix: the writer would still create O(full transcript)
   garbage on every append, and import-level cleanup misses imports containing
   one new event plus thousands of old references.
3. **Delete and rewrite each source on every append** — preserves per-import
   identity. Rejected: correct but restores the O(N) churn that the append
   high-water path was created to eliminate.
4. **Insert references only for newly written events** — small change, but tool
   calls can transition from started to completed across imports, and the same
   raw record could still acquire multiple identities.
5. **Canonical `(source_id, raw_record_key)` identity** — chosen. Remove
   `import_id` from `record_refs`; imports describe parse attempts, while source
   records describe durable raw locations. Upsert metadata without changing the
   reference id, and retain only keys consumed by structured rows.
6. **Eliminate `record_refs` and copy source offsets into every consumer** —
   rejected because it duplicates locator fields and removes the single join
   used to reconstruct raw evidence.
7. **Tail-only incremental parsing** — compatible future optimization, but not
   required for the storage invariant. It reduces parse CPU; canonical identity
   is still required when a source is force-reparsed or rewritten.

## Counterevidence sought

The leading alternative was frequent orphan cleanup. It would have been enough
if duplicate rows lived only in imports with zero events. The live writer and
prune query disproved that: every append import can contain one new event, so
the import-level predicate retains all old-line references in that import.
Direct pointer counts also showed that no more than 1.46M distinct references
were reachable, against roughly 76.8M stored rows.

## Decision

`record_refs` is keyed by `(source_id, raw_record_key)`. It no longer carries
`import_id`. Events, tool calls, and file touches retain their own `import_id`
for parse-attempt provenance and point to the canonical source record. Ingest
only materializes records named by one of those structured consumers.

The v9→v10 data migration is explicit rather than connect-time: a non-empty v9
database must be cloned, repaired under the single-writer lock, verified, and
atomically swapped. Fresh databases apply v10 normally. This prevents an
ordinary read command from silently launching a multi-hour rewrite.

## Evidence

- `dbstat`: `record_refs` 12,315.6 MiB; its autoindex 4,431.8 MiB.
- 998,979 events; inferred 76,764,755 references (76.8 per event).
- Reachable distinct ids: events 957,835; tool starts 243,048; tool ends
  229,807; file touches 23,465 (union upper bound 1,454,155).
- Long-source import counts: 1,274 / 1,091 / 900 for Claude and 403 / 302 for
  Codex.
- User-message text was 105.8 MiB; transcript text was not the size driver.

## Revisit if

- A vendor rewrites source-record keys in place rather than appending with
  stable keys; the adapter must then declare rewrite semantics and force a
  source-scoped canonical-record refresh.
- Raw-source reconstruction requires retaining unconsumed metadata records;
  add an explicit consumer rather than reverting to all-lines-per-import.

## Supersedes

No prior decision record. It replaces the implicit v1 schema choice that made
`import_id` part of source-record identity.

