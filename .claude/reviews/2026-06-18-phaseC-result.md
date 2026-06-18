PHASE C — RSI-lifecycle graph spine — COMPLETE

## Files created/modified (manifest)
- CREATED  scripts/lifecycle_graph.py            — rederivable graph (no disk store)
- CREATED  scripts/tests/test_lifecycle_graph.py — 3 correctness tests
- MODIFIED justfile                              — `graph` recipe in [group('orientation')]
(NOT touched: scripts/lifecycle_relations.json [Phase A, LOADED only], gov.py, any peer file,
 shared hooks, commit-check-parse.py. .claude/rules/codebase-map.md auto-refreshed by a peer
 hook to 169 files — generated artifact, not mine, left as-is.)

## Architecture as built
- NODES from 3 sources (resolver spans all three): decisions/*.md (frontmatter `id:`, fallback
  stem) · research/*.md (stem) · predictions.jsonl (`id`). 349 nodes total.
- EDGES from decision frontmatter `relations:` blocks (line-based parser mirroring Phase A's
  `_relation_types`, extended to capture `target:`). Each edge normalized THROUGH the Phase-A
  vocab: fold->canonical, invert SWAPS subject/target, traversable:false -> separate weak bucket.
- Unresolved targets -> `dangling` (recorded, never crashes). Sparse log join ACCEPTED — not gated.
- Predictions contribute best-effort `commit` provenance edges (weak bucket).
- Ephemeral `:memory:` sqlite projection built+discarded each call (gov.py:build_projection
  discipline) — proves the node/edge join works; nothing on disk.

## GATE OUTPUTS (verbatim)

### GATE 1 — `uv run python3 scripts/lifecycle_graph.py --build`  (EXIT=0)
```
lifecycle-graph (rederivable; no disk store)
  nodes: 349 total — decisions=54 research=272 predictions=23
  edges: traversable=51 weak/non-traversable=7 dangling=9
  unknown relation strings (vocab gaps): 0
```
PASS — builds clean, per-source node counts + traversable/weak/dangling edge counts printed.

### GATE 2 — `just graph 2026-06-18-planning-lifecycle-contract`  (EXIT=0)
```
# node: 2026-06-18-planning-lifecycle-contract  (source: decision)

## traversable (lifecycle) edges
  branches_from  -> 2026-06-07-verifier-conditional-autonomy

## weak / non-traversable (relates_to + provenance) edges
# excluded from bundling/traversal — association only
  relates_to     -> 2026-06-18-unified-loop-infra-scaffold-cookbook
  relates_to     -> 2026-06-16-rsi-unified-control-surface
  relates_to     -> 2026-06-16-feature-work-loop-binding-measurement-first
  relates_to     -> 2026-06-16-shared-checkout-isolation-by-default
```
PASS — `branches_from -> 2026-06-07-verifier-conditional-autonomy` is in the TRAVERSABLE
section; all 4 `relates_to` targets appear ONLY in the weak section.

### GATE 3 — `pytest scripts/tests/test_lifecycle_graph.py`  (exit=0)
```
scripts/tests/test_lifecycle_graph.py::test_superseded_by_inverts_to_supersedes PASSED [ 33%]
scripts/tests/test_lifecycle_graph.py::test_relates_to_absent_from_traversable PASSED [ 66%]
scripts/tests/test_lifecycle_graph.py::test_resolver_spans_decisions_and_research PASSED [100%]
3 passed in 0.24s
```
PASS — (a) `superseded_by A->B` normalizes to `supersedes B->A`; (b) `relates_to` absent from
traversable set; (c) resolver resolves a decisions/ slug AND a research/ stem.

EXTRA real-data proof of the invert swap (not synthetic): the only live `superseded_by` is in
decisions/2026-05-11-cross-attestation-substrate.md (`superseded_by -> v2`); the graph emits the
swapped traversable edge `{subject: v2, type: supersedes, target: v1}` — direction correct.

### GATE 4 — staged-set isolation
`git diff --cached --name-only` after `git add scripts/lifecycle_graph.py
scripts/tests/test_lifecycle_graph.py justfile`:
```
justfile
scripts/lifecycle_graph.py
scripts/tests/test_lifecycle_graph.py
```
PASS — EXACTLY the 3 paths staged; no peer files, no auto-refreshed codebase-map.

## Commit
SHA `98208e5` — `[gov] Add just graph <id> lifecycle neighborhood view — Phase C`.
Multi-agent safety hook required `--only <files>` (17 concurrent claude procs); re-ran with
`git commit --only <3 paths>`. `git show --stat HEAD`: 3 files changed, 477 insertions, only
mine. Session-ID trailer auto-appended by the prepare-commit-msg git hook.

## Vocab coverage
All 13 relation strings actually used across decisions/ are covered (0 unknown vocab gaps in
Gate 1). No relation string the vocab does NOT cover.
