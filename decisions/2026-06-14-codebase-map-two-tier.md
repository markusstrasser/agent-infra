---
id: 2026-06-14-codebase-map-two-tier
concept: agent-context-budget
repo: agent-infra
decision_date: 2026-06-14
recorded_date: 2026-06-14
provenance: contemporaneous
status: accepted
initial_leaning: keep the single auto-loaded per-file map; maybe trim descriptions
relations:
  - type: depends_on
    target: 2026-06-13-llm-optimal-repo-representation
---

# 2026-06-14: Codebase map → two-tier (auto-loaded index + on-demand detail)

## Context
`codebase-map.py` generated one `.claude/rules/codebase-map.md` per repo — a
per-file one-liner + import-edge listing — path-scoped to source dirs so it
**auto-loads the whole map** the moment an agent touches any file in scope.
Measured auto-load cost: genomics 139KB / **~34.8K tok**, intel ~20.4K tok,
phenome ~8.1K tok, agent-infra ~3.1K tok. A genomics agent editing one script
paid ~35K tokens of file-listing before its first thought — on top of the
~39K always-loaded the drift-sentinel already flagged over-ceiling.

Prompted by: "is this anti-agentic or good insurance, and could a hierarchical
index save context?"

## Alternatives considered
1. **Keep flat auto-load, trim per-file descriptions** — cheap, but still scales
   with file count and keeps injecting summaries of inspectable files. Rejected:
   doesn't fix the scaling problem (genomics has 1128 files).
2. **MCP / tool for code-nav** — query on demand. Rejected: `repo-tools` MCP was
   already retired (0 uses / 4287 runs) and PageRank symbol-nav vetoed
   ("Read+Grep faster for 20-50 file repos"). Re-litigating a live veto.
3. **Two-tier: tiny auto-loaded index + on-demand detail** ← chosen. Index =
   per-group file count + hub files (import fan-in) + pointer. Detail = full
   per-file listing in `.claude/maps/` (NOT auto-loaded), Read on demand.
4. **Drop the map entirely, rely on ls/Grep** — loses the import-edge spine
   (`config.py ← 30 files`), which `ls` can't give. Rejected: that signal is the
   map's real value-add over native search.

## Counterevidence sought
Looked for evidence the auto-loaded per-file map *changes agent behavior for the
better* (would justify the token cost). Found none: no runtime consumer
(`orient.py` only names it, `generate-indexes.py` writes it, `orphan_check.py`
excludes it) — consumption is involuntary auto-injection. Conversely, this repo's
own `context-budget-principles.md` ("never auto-load verbose descriptions of
things the agent can inspect directly; indexes route, they don't summarize") and
the Gloaguen et al. AGENTS.md study it cites (wiki-summaries: −0.5–3% success,
**+20% cost**) both say the flat map is net-negative at scale. The per-file
one-liner IS the wiki-summary anti-pattern; the import-edge spine is the part
worth keeping. Verdict: machinery = good insurance; flat auto-load of big maps =
mild anti-pattern. Split resolves it.

## Decision
Two-tier output from `codebase-map.py`:
- **Tier 1** `.claude/rules/codebase-map.md` (auto-loaded, path-scoped): routing
  index — per directory group, file count + hub files (`← imported-by-N`, top 6)
  + detail pointer. Flat ~1-2K tokens **regardless of repo size**.
- **Tier 2** `.claude/maps/codebase.<group>.md` (NOT auto-loaded; gitignored,
  regenerable): full per-file listing + edges for one group. Agents Read only the
  area they need.

Measured auto-load cut: genomics 98% (34.8K→0.7K tok), intel 95%, phenome 89%,
agent-infra 93%. Detail is preserved 1:1, just deferred to on-demand.

## Evidence
- Sizes + cut measured 2026-06-14 (probe inline in session; `/tmp/measure_map.py`
  dry-run for intel/phenome/genomics without writing).
- `.claude/rules/context-budget-principles.md` §4 (auto-load vs discoverable).
- `research/2026-06-13-llm-optimal-repo-representation.md`, `wiki-vs-flat-for-agents.md`.
- Idempotency + validator (`generate-indexes.check_codebase_map`) re-verified;
  fixed a pre-existing validator false-positive (naive `rglob` counted the
  `scripts/corpus` sub-venv's 2722 files; now counts via the generator's gather).

## Revisit if
- An agent demonstrably needs per-file descriptions auto-surfaced per-area (would
  argue for per-subdir path-scoped detail instead of fully on-demand). No evidence
  of this today.
- A repo's flat top-level dir (genomics `scripts/` has 972 direct files) makes even
  the on-demand detail file unwieldy — that's a structural (subpackage) fix in that
  repo, not a map-generator change.

## Supersedes
Flat single-file `codebase-map.md` (in-place format change; file was already
gitignored/regenerable, so no migration).
