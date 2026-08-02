---
id: evidence-bound-code-relations
concept: canonical static code relationship substrate
repo: agent-infra
decision_date: 2026-08-02
recorded_date: 2026-08-02
provenance: contemporaneous
status: accepted
initial_leaning: adopt Graphify if its graph added reachability we did not have
relations: []
---

# Evidence-bound code relations

## Context

The Graphify pilot showed that a typed source graph and reverse-impact query are
useful, but its repository model stopped at language-level imports and calls. On
this repository it missed a load-bearing operational chain:

`ops/launchd/com.agent-infra.pulse-tick.plist` -> `scripts/pulse-tick.sh` ->
`scripts/pulse.py`, plus the independent `scripts/pulse_tick.py` ->
`scripts/pulse.py` invocation.

The repository already computes overlapping fragments of this graph in
`repo-imports.py`, `repo-outline.py`, `structure_debt_rank.py`,
`orphan_check.py`, and `infra_usage_check.py`. Their different identities,
resolution rules, and evidence grades can silently disagree. `codebase-map.py`
is a live consumer of one fragment, so this is an integration problem rather
than a reason to add another pull-only graph command.

## Alternatives considered

1. **Adopt Graphify wholesale.** Rejected: its MCP, hooks, persisted artifacts,
   and external dependency surface duplicate local infrastructure while its
   extractor missed the operational chain.
2. **Wrap Graphify behind local commands.** Rejected: this preserves the same
   representation ceiling behind another runtime boundary.
3. **Improve each current extractor independently.** Rejected: each improvement
   can still drift across callers, orphan checks, hub counts, and cycle checks.
4. **Build one in-repo relation substrate and migrate every live consumer.**
   Selected: one inspectable representation can cover source and operational
   edges without a service or persistent derived store.
5. **Keep ad hoc AST and `rg` probes only.** Rejected as the canonical path:
   these remain useful deciding checks, but cannot consistently drive maps,
   reverse impact, cycles, adoption, and orphan calculations.

## Counterevidence sought

- Recent usage logs were checked for a standalone `repo-outline` workflow; only
  the continuously generated repository summaries had meaningful use. A new
  disconnected CLI would therefore repeat the current fragmentation.
- The five claimed duplicate extractors and their callers were read directly;
  each performs its own import, call, path-invocation, or caller inference.
- The launchd, shell, Just, and Python sources in the pulse chain were read at
  their actual invocation lines. This rules out treating Graphify's miss as a
  naming-only issue.
- A premise review independently checked all five claims and found no falsified
  premise before implementation.

## Decision

Create a stdlib-only `code_relations` module and migrate all live consumers to
it. A relation carries stable endpoint identities, relation type, source path,
source line, source snippet, and one of `EXTRACTED`, `RESOLVED`, or
`AMBIGUOUS`. Stable identities use repository-relative paths plus qualified
symbols, recipe names, or launchd labels; basename-only resolution is forbidden.

The substrate covers Python imports and calls, subprocess entrypoints, shell
invocations, Just recipes, and launchd `ProgramArguments`. It provides reverse
impact and integrity diagnostics. Ambiguity and malformed files remain visible
as diagnostics or ambiguous edges while extraction continues for other files.

Generated maps remain derived. The graph is rebuilt from repository source at
the point of use; no persistent database, MCP server, hook fleet, semantic-doc
index, or generated graph artifact is introduced.

## Evidence

- Graphify v0.9.32 pilot on this repository: 501 files, 5,359 nodes, and 11,514
  edges in 6.44 seconds; useful import impact, but no pulse operational impact.
- Live consumer trace: `codebase-map.py` imports `repo-imports.py`; four other
  tools separately infer overlapping relationships.
- Operational trace: the pulse launchd plist names `pulse-tick.sh`; the shell
  wrapper executes `pulse.py`; the Just recipe and `pulse_tick.py` also execute
  `pulse.py`.

## Revisit if

- A polyglot repository needs semantic resolution that the bounded local
  extractors cannot provide and Graphify (or another mature dependency) passes
  the operational-chain held-out cases.
- Building the live graph exceeds the latency budget of its actual consumers.
- A second process needs durable cross-repository graph transactions rather
  than source-derived, per-invocation analysis.

## Supersedes

The relation-inference portions of `repo-imports.py` and the independent static
relationship logic in the migrated consumers. It does not supersede the typed
agent-lifecycle graph in `src/agentlogs/lifecycle.py`, whose nodes and evidence
contract describe a different domain.
