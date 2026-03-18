# Substrate Alignment Audit

Scope: `/Users/alien/Projects/meta/substrate/schema.sql`, `/Users/alien/Projects/meta/substrate/core.py`, `/Users/alien/Projects/meta/substrate/mcp_server.py`, plus `/Users/alien/Projects/meta/substrate/cli.py` because the task requires verifying CLI reachability.

Method: I treated `KnowledgeDB` non-underscore methods as the public core API, excluding dunder methods. `close()` counts as reachable because the CLI uses `with KnowledgeDB(...) as db` at `substrate/cli.py:49`, which dispatches `__exit__()` and then `close()` at `substrate/core.py:44`.

## Findings

### UNREACHABLE_TABLE

1. `derivations`, `derivation_inputs`, and `derivation_outputs` have no MCP or CLI write path.
   - The schema defines these tables at `substrate/schema.sql:47`, `substrate/schema.sql:55`, and `substrate/schema.sql:62`.
   - The only core writer is `KnowledgeDB.register_derivation()` at `substrate/core.py:159`, which inserts into `derivations` at `substrate/core.py:170`, clears child rows at `substrate/core.py:175` and `substrate/core.py:176`, and reinserts child links at `substrate/core.py:180` and `substrate/core.py:185`.
   - `mcp_server.py` exposes tools that call `register_assertion`, `dependents`, `register_evidence`, `register_artifact`, `add_relation`, `mark_stale`, `get`, `stale_objects`, `stats`, and `recent_changes` at `substrate/mcp_server.py:67`, `substrate/mcp_server.py:69`, `substrate/mcp_server.py:91`, `substrate/mcp_server.py:112`, `substrate/mcp_server.py:132`, `substrate/mcp_server.py:149`, `substrate/mcp_server.py:154`, `substrate/mcp_server.py:177`, `substrate/mcp_server.py:200`, and `substrate/mcp_server.py:213`. None invoke `register_derivation()`.
   - The CLI only dispatches `stats`, `stale_objects`, `recent_changes`, `get`, `dependents`, and `mark_stale` at `substrate/cli.py:50`, `substrate/cli.py:55`, `substrate/cli.py:62`, `substrate/cli.py:69`, `substrate/cli.py:77`, and `substrate/cli.py:84`.
   - The only in-repo callers are tests at `substrate/stress_test.py:118` and `substrate/stress_test.py:154`.

2. `cross_project_refs` has no MCP or CLI write path, and no public read API.
   - The schema defines the table at `substrate/schema.sql:98`.
   - The only core writer is `KnowledgeDB.add_cross_project_ref()` at `substrate/core.py:146`, which inserts into `cross_project_refs` at `substrate/core.py:150`.
   - No MCP tool calls it; the MCP surface only invokes the methods cited at `substrate/mcp_server.py:67`, `substrate/mcp_server.py:69`, `substrate/mcp_server.py:91`, `substrate/mcp_server.py:112`, `substrate/mcp_server.py:132`, `substrate/mcp_server.py:149`, `substrate/mcp_server.py:154`, `substrate/mcp_server.py:177`, `substrate/mcp_server.py:200`, and `substrate/mcp_server.py:213`.
   - No CLI command calls it; the CLI dispatch set is at `substrate/cli.py:50`, `substrate/cli.py:55`, `substrate/cli.py:62`, `substrate/cli.py:69`, `substrate/cli.py:77`, and `substrate/cli.py:84`.
   - The only in-repo callers are tests at `substrate/stress_test.py:230` and `substrate/stress_test.py:243`.
   - `core.py` has no corresponding public reader for `cross_project_refs`; no non-private method selects from that table.

### UNREACHABLE_METHOD

1. `KnowledgeDB.register_derivation()` is unreachable from the operational surfaces.
   - Defined at `substrate/core.py:159`.
   - Not called by any MCP tool or CLI command; the full operational call set is the one cited above from `substrate/mcp_server.py:67`, `69`, `91`, `112`, `132`, `149`, `154`, `177`, `200`, `213` and `substrate/cli.py:50`, `55`, `62`, `69`, `77`, `84`.
   - Only called by tests at `substrate/stress_test.py:118` and `substrate/stress_test.py:154`.

2. `KnowledgeDB.add_cross_project_ref()` is unreachable from the operational surfaces.
   - Defined at `substrate/core.py:146`.
   - Not called by any MCP tool or CLI command; see the same operational call inventory above.
   - Only called by tests at `substrate/stress_test.py:230` and `substrate/stress_test.py:243`.

### EXPOSED_BUT_BROKEN

None. Every MCP tool calls an existing `KnowledgeDB` method:

| MCP tool | Core call(s) | Status |
| --- | --- | --- |
| `register_assertion` | `register_assertion()` at `substrate/mcp_server.py:67`, `dependents()` at `substrate/mcp_server.py:69` | OK |
| `register_evidence` | `register_evidence()` at `substrate/mcp_server.py:91` | OK |
| `register_artifact` | `register_artifact()` at `substrate/mcp_server.py:112` | OK |
| `add_dependency` | `add_relation()` at `substrate/mcp_server.py:132` | OK |
| `mark_stale` | `mark_stale()` at `substrate/mcp_server.py:149`, `get()` at `substrate/mcp_server.py:154` | OK |
| `query_dependents` | `dependents()` at `substrate/mcp_server.py:166` | OK |
| `query_stale` | `stale_objects()` at `substrate/mcp_server.py:177` | OK |
| `query_object` | `get()` at `substrate/mcp_server.py:192` | OK |
| `substrate_stats` | `stats()` at `substrate/mcp_server.py:200` | OK |
| `recent_changes` | `recent_changes()` at `substrate/mcp_server.py:213` | OK |

### SCHEMA_DRIFT

None found. The SQL emitted by `core.py` uses column names that exist in `schema.sql`, and every table referenced by `core.py` is declared in the schema. The gaps are reachability and exposure, not mismatched column definitions.

## Table Coverage Matrix

| Table | Core write path | Core read path | MCP exposure | Result |
| --- | --- | --- | --- | --- |
| `assertions` | `register_assertion()` at `substrate/core.py:49` | `get()` at `substrate/core.py:259`, `stale_objects()` at `substrate/core.py:301`, `stats()` at `substrate/core.py:314` | `register_assertion`, `mark_stale`, `query_object`, `query_stale`, `substrate_stats` | OK |
| `evidence` | `register_evidence()` at `substrate/core.py:74` | `get()` at `substrate/core.py:259`, `stale_objects()` at `substrate/core.py:301`, `stats()` at `substrate/core.py:314` | `register_evidence`, `mark_stale`, `query_object`, `query_stale`, `substrate_stats` | OK |
| `artifacts` | `register_artifact()` at `substrate/core.py:99` | `get()` at `substrate/core.py:259`, `stale_objects()` at `substrate/core.py:301`, `stats()` at `substrate/core.py:314` | `register_artifact`, `mark_stale`, `query_object`, `query_stale`, `substrate_stats` | OK |
| `derivations` | `register_derivation()` at `substrate/core.py:159` | `stats()` at `substrate/core.py:314` | None | UNREACHABLE_TABLE |
| `derivation_inputs` | `register_derivation()` at `substrate/core.py:175` and `substrate/core.py:180` | `mark_stale()` at `substrate/core.py:240`, `dependents()` at `substrate/core.py:286` | None | UNREACHABLE_TABLE |
| `derivation_outputs` | `register_derivation()` at `substrate/core.py:176` and `substrate/core.py:185` | `mark_stale()` at `substrate/core.py:246`, `dependents()` at `substrate/core.py:292` | None | UNREACHABLE_TABLE |
| `relations` | `add_relation()` at `substrate/core.py:125` | `mark_stale()` at `substrate/core.py:233`, `dependents()` at `substrate/core.py:276`, `stats()` at `substrate/core.py:314` | `add_dependency`, `query_dependents`, `mark_stale`, `substrate_stats` | OK |
| `changelog` | `_log()` at `substrate/core.py:346` via `register_assertion()` at `substrate/core.py:64` and `substrate/core.py:71`, `register_evidence()` at `substrate/core.py:89` and `substrate/core.py:96`, `register_artifact()` at `substrate/core.py:113` and `substrate/core.py:120`, `register_derivation()` at `substrate/core.py:188`, `mark_stale()` at `substrate/core.py:225` | `recent_changes()` at `substrate/core.py:330`, `stats()` at `substrate/core.py:325` | `recent_changes`, `substrate_stats` | OK |
| `cross_project_refs` | `add_cross_project_ref()` at `substrate/core.py:146` | None | None | UNREACHABLE_TABLE |

## Core Public Method Reachability

| Core method | Caller(s) in MCP/CLI | Result |
| --- | --- | --- |
| `close()` | Indirect via CLI context manager: `with KnowledgeDB(args.db) as db` at `substrate/cli.py:49`, then `__exit__()` calls `close()` at `substrate/core.py:44` | OK |
| `register_assertion()` | `substrate/mcp_server.py:67` | OK |
| `register_evidence()` | `substrate/mcp_server.py:91` | OK |
| `register_artifact()` | `substrate/mcp_server.py:112` | OK |
| `add_relation()` | `substrate/mcp_server.py:132` | OK |
| `add_cross_project_ref()` | None in MCP/CLI; test-only at `substrate/stress_test.py:230` and `substrate/stress_test.py:243` | UNREACHABLE_METHOD |
| `register_derivation()` | None in MCP/CLI; test-only at `substrate/stress_test.py:118` and `substrate/stress_test.py:154` | UNREACHABLE_METHOD |
| `mark_stale()` | `substrate/mcp_server.py:149`, `substrate/cli.py:85` | OK |
| `get()` | `substrate/mcp_server.py:154`, `substrate/mcp_server.py:192`, `substrate/cli.py:70` | OK |
| `dependents()` | `substrate/mcp_server.py:69`, `substrate/mcp_server.py:166`, `substrate/cli.py:78` | OK |
| `stale_objects()` | `substrate/mcp_server.py:177`, `substrate/cli.py:56` | OK |
| `stats()` | `substrate/mcp_server.py:200`, `substrate/cli.py:51` | OK |
| `recent_changes()` | `substrate/mcp_server.py:213`, `substrate/cli.py:63` | OK |
