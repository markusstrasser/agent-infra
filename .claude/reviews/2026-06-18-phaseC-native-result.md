# Phase C Native Port — agentlogs-native lifecycle graph

STATUS: COMPLETE — all 5 functional gates PASS; committed.

Ported `scripts/lifecycle_graph.py` (the ORACLE) → `src/agentlogs/lifecycle.py` (agentlogs.db
named-query home). Oracle semantics preserved verbatim: node collection over decisions/ ∪ research/
∪ predictions, edge extraction from decision frontmatter `relations:`, `normalize_type`
(fold→canonical; invert ⇒ subject/target SWAP; canonical `traversable:false` ⇒ weak). Storage HOME
changed from standalone in-process `:memory:` projection to a rederivable `lifecycle_edges` table in
the live agentlogs.db, queried via `queries/lifecycle_neighbors.sql`.

## Files
- A `src/agentlogs/lifecycle.py` — `build_edges(con, repo_root)` + oracle-ported helpers
- M `src/agentlogs/cli.py` — `lifecycle-reindex` subcommand
- A `src/agentlogs/queries/lifecycle_neighbors.sql` — `:node` named query
- M `justfile` — `graph` recipe rebuild-then-query (replaces standalone module)
- D `scripts/lifecycle_graph.py` — standalone module deleted
- D `scripts/tests/test_lifecycle_graph.py` — its test deleted
- A `tests/agentlogs/test_lifecycle.py` — 3 ported correctness tests
- KEPT `scripts/lifecycle_relations.json` + `scripts/tests/test_lifecycle_relations.py` (Phase A)

## Two non-trivial deltas from a naive port (load-bearing)
1. **Repo-root resolution.** agentlogs ships NON-editable inside the agent-infra wheel — the installed
   `__file__` is under site-packages and CANNOT locate the source repo (decisions/, vocab live in the
   working tree). Naive `Path(__file__).parents[2]` resolved to `.venv/lib/python3.13/` and crashed
   FileNotFoundError. Fixed: `default_repo_root()` uses `git rev-parse --show-toplevel` from cwd, the
   same convention provenance.py:66 already uses. Overridable via `--repo-root` (tests pass a tmp repo).
2. **Writer-lock contention.** The live launchd `agentlogs index` job holds the WAL writer lock through
   long bulk-import transactions that EXCEED connect()'s 30s busy_timeout (observed: gate 4 hit
   `database is locked` once). `build_edges` now wraps DELETE+INSERT in `BEGIN IMMEDIATE` with a bounded
   6-attempt linear backoff (~10.5s) that waits the indexer out instead of failing the recipe. Verified:
   gate 4 re-ran to RC=0 WITH the indexer process live.

## MECHANICAL GATES (verbatim)

### GATE 1 — query --list shows lifecycle_neighbors  [PASS]
```
$ uv run agentlogs query | grep lifecycle_neighbors
  lifecycle_neighbors  params: node
```

### GATE 2 — lifecycle-reindex builds, prints counts, 0 unknown vocab  [PASS]
```
$ uv run agentlogs lifecycle-reindex
lifecycle-reindex (agentlogs-native; lifecycle_edges rebuilt)
  nodes: 349 total — decisions=54 research=272 predictions=23
  edges: 58 total — traversable=51 weak=7 dangling=9
  unknown relation strings (vocab gaps): 0
```
(Matches the deleted oracle's baseline exactly: 349 nodes 54/272/23, 51 traversable / 7 weak / 9 dangling, 0 unknown.)

### GATE 3 — neighbors include branches_from TRAVERSABLE + 4 relates_to WEAK  [PASS]
```
$ uv run agentlogs query lifecycle_neighbors --param node=2026-06-18-planning-lifecycle-contract
type           direction  other                                                   traversable  dangling  raw_type       source
-------------  ---------  ------------------------------------------------------  -----------  --------  -------------  -----------------
branches_from  out        2026-06-07-verifier-conditional-autonomy                1            0         branches_from  decision-relation
relates_to     out        2026-06-16-feature-work-loop-binding-measurement-first  0            0         relates_to     decision-relation
relates_to     out        2026-06-16-rsi-unified-control-surface                  0            0         relates_to     decision-relation
relates_to     out        2026-06-16-shared-checkout-isolation-by-default         0            0         relates_to     decision-relation
relates_to     out        2026-06-18-unified-loop-infra-scaffold-cookbook         0            0         relates_to     decision-relation
```
branches_from -> verifier-conditional-autonomy is TRAVERSABLE (1); all 4 relates_to are WEAK (0). As required.

### GATE 4 — just graph (rebuild+query path), RC=0 under live indexer  [PASS]
```
$ just graph 2026-06-18-planning-lifecycle-contract
uv run agentlogs lifecycle-reindex >/dev/null && uv run agentlogs query lifecycle_neighbors --param node=2026-06-18-planning-lifecycle-contract
type           direction  other                                                   traversable  dangling  raw_type       source
-------------  ---------  ------------------------------------------------------  -----------  --------  -------------  -----------------
branches_from  out        2026-06-07-verifier-conditional-autonomy                1            0         branches_from  decision-relation
relates_to     out        2026-06-16-feature-work-loop-binding-measurement-first  0            0         relates_to     decision-relation
relates_to     out        2026-06-16-rsi-unified-control-surface                  0            0         relates_to     decision-relation
relates_to     out        2026-06-16-shared-checkout-isolation-by-default         0            0         relates_to     decision-relation
relates_to     out        2026-06-18-unified-loop-infra-scaffold-cookbook         0            0         relates_to     decision-relation
RC=0
```

### GATE 5 — tests pass  [PASS]
```
$ uv run python3 -m pytest tests/agentlogs/test_lifecycle.py scripts/tests/test_lifecycle_relations.py -q
....                                                                     [100%]
4 passed in 3.08s
```
(3 ported lifecycle tests: invert-swap, relates_to-never-traversable, resolver-spans-decisions+research; + Phase A vocab drift-test.)

## Vocab coverage
0 unknown relation strings — every `type:` in the decision corpus maps to canonical or fold. No vocab gap.

## GATE 6 — staged set EXACTLY as required  [PASS]
```
$ git diff --cached --name-status
M	justfile
D	scripts/lifecycle_graph.py
D	scripts/tests/test_lifecycle_graph.py
M	src/agentlogs/cli.py
A	src/agentlogs/lifecycle.py
A	src/agentlogs/queries/lifecycle_neighbors.sql
A	tests/agentlogs/test_lifecycle.py
```
No peer files. uv.lock NOT staged — its dirty change is a PEER'S (adds a `pyyaml` dep under
`extra == 'memo'` to another package's metadata, unrelated to agentlogs/lifecycle); my
`uv sync --reinstall-package agent-infra` only rebuilt the wheel in-place and did not alter the
lockfile.

## COMMIT
`aa49e4b` [gov] Port lifecycle graph to agentlogs-native v_lifecycle_neighbors — Phase C
(7 files, 540 insertions / 475 deletions; Session-ID auto-appended; Evidence trailer present).

