---
id: 2026-06-18-lifecycle-graph-spine
concept: lifecycle-graph-spine
repo: agent-infra
decision_date: 2026-06-18
recorded_date: 2026-06-18
provenance: contemporaneous
status: accepted
initial_leaning: "Generalize gov.py build_projection into a :memory: view + a guessed 8-edge closed vocab + dual-authored trailers/frontmatter edges. REVERSED by the cross-model gate on three repo-grounded facts."
relations:
  - type: relates_to
    target: 2026-06-07-state-externalization-lens
  - type: relates_to
    target: 2026-06-07-verifier-conditional-autonomy
---

# 2026-06-18: Harness RSI-lifecycle graph — a rederivable view + a single vocab, agentlogs-native, never a store

## Context

Four stores expressed the same lifecycle relations four ways (decision `relations:`,
improvement-log `[~]/[>]`, predictions loose commit refs, vetoes prose links) and none
was queryable. Goal: unify the relation AUTHORING + make the decision↔commit↔finding
lineage navigable (for bundling-for-review), **without** merging the scientific corpus
(operator cut: lifecycle ≠ evidence relations) and **without** a new persistent store
(the finding-triage-DB veto is live).

## Alternatives considered

1. **View-only over files + guessed closed vocab + generalize `build_projection`** (initial leaning).
2. **Git-trailer-native edges** for everything (`Decides:/Implements:/Refutes:/Supersedes:`).
3. **First-class id + frontmatter relations everywhere** + referential lint (heaviest migration).
4. **Canonical relation vocab file only** (provenance_tags pattern) — kills drift, no query surface.
5. **Persistent typed node/edge store** — REJECTED, veto-adjacent (finding-triage-DB).

## Counterevidence sought

The cross-model gate (repo-grounded Opus + cold GPT-5.5 + author probes; a parallel
peer panel of composer-2.5 ×3 converged independently) was run to FALSIFY the initial
leaning. It reversed three asserted facts, each verified at source:
- **"generalize `build_projection`"** — FALSE: it is a single-table `:memory:` stub
  `.close()`d immediately (gov.py:343-357), not a join. The native home for derived
  edges is **agentlogs.db's git cache** (`git_commits.body` + the `queries/*.sql`
  named-query pattern), which already exists.
- **"≥90% {slug,SHA} join"** — FALSE, measured 25%: the `grep '20..-..-..-[a-z]'`
  count conflated every date-prefixed token (research memos, session labels) with a
  decision-id. The improvement-log→decision edge is genuinely sparse.
- **"8-edge closed set"** — FALSE: 14 distinct relation strings are live. The closed
  set must be DERIVED from the data, not guessed; `superseded_by` is the INVERSE of
  `supersedes` (folding it without swapping subject/target is a silent direction bug).

## Decision

A lifecycle graph that is **a view + a vocabulary, never an authoritative store**:

1. **Canonical relation vocab, single-sourced** — `scripts/lifecycle_relations.json`
   (10 canonical edges + a fold-map normalizing the 9 drift singletons; `relates_to`
   marked non-traversable — a generic association, not a lifecycle edge; folds carry an
   `invert` flag so inverses are direction-swapped, not relabeled). A drift-test asserts
   every used string ∈ canonical∪fold (no silent drift). All enforcers LOAD it.
2. **Agentlogs-native projection** — `src/agentlogs/lifecycle.py build_edges` materializes
   a rederivable `lifecycle_edges` table (DELETE-then-INSERT, `:memory:`-discipline, no
   new authoritative store) over decisions/ ∪ research/ ∪ predictions; queried via the
   named query `lifecycle_neighbors.sql` (`:node` param). `just graph <id>` = a thin
   wrapper over `agentlogs query`. Reuses the proven reconstruct-on-demand pattern.
3. **Edge-KIND split** — design-time relations (decision→decision) live in mutable
   decision frontmatter; ship-time `implements` edges (commit→decision) are recovered from
   commit bodies (B1) — a historical fact belongs on the commit, not in frontmatter. No
   edge authored in two places.
4. **B1 / B2 ladder** — B1 (commit-body parse → 117 implements-edges, agentlogs-local,
   ungated) SHIPPED; B2 (forward-authoring: a CLAUDE.md convention, then a gated
   `prepare-commit-msg` scaffold) stays spec-only behind measured demand + hard-limit-#4
   sign-off (`decisions-pending/2026-06-18-phaseB-implements-trailer.md`).

Rejected: persistent store (5, veto-adjacent); `build_projection` rebuild (stub, not a
join); dual-authored trailers+frontmatter (drift); guessed vocab (contradicts live data);
the ≥90%-join success criterion (falsified — keyed instead on clean frontmatter/trailer
joins, sparse log edge accepted); a standalone `just graph` 3rd query layer (folded into
agentlogs); merging the corpus (operator cut).

## Evidence

`.claude/reviews/2026-06-18-lifecycle-graph-spine-critique.md` (panel verdict + verified
reversals). Shipped + independently re-verified: Phase A `ee2955a`/`647b9b1`, Phase C
agentlogs-native `aa49e4b`, Phase B1 `627ca9c`. `lifecycle-reindex`: 349 nodes,
168 traversable / 7 weak / 9 dangling edges, 0 vocab gaps; `just graph
<decision>` lists implementing commits + design relations; 7/7 tests pass.

## Revisit if

- The `relates_to` weak-bucket or the sparse log→decision edge proves to block a real
  review-bundling use → revisit the node/edge model (not the store decision).
- B2-lite adherence is measured and the explicit `implements` trailer adds material
  signal over B1's prose-mention parsing → promote per the spec's gate.

## Supersedes

None. Consolidates the gitignored working plan
(`.claude/plans/2026-06-18-harness-lifecycle-graph-spine.md`) into the durable record;
distinct from the scientific corpus (`2026-05-26-cross-attestation-substrate-v2`) — no
shared edge vocabulary across the two domains.
