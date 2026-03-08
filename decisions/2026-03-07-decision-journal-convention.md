# 2026-03-07: Establish decision journal convention across publishable repos

## Context
Repos intended for publication (research, genomics, arc-agi) need traceable concept evolution — not just code diffs, but *why* ideas branched, merged, or were pruned. Git commit messages capture what changed; plan files (gitignored, ephemeral) captured the reasoning but were deleted after 14 days. The concept-level provenance was recoverable from git archaeology but not structured for later visualization or writeup.

## Alternatives considered
1. **Structured YAML/JSON decision records** — machine-parseable, but prose is better for reasoning and quotability in articles.
2. **Inline revision sections in research memos only** — captures pivots within existing files, but misses cross-cutting decisions and doesn't create discrete nodes for a concept graph.
3. **Decision journal (prose .md files) + revision sections in memos** — discrete files for forks, linked from revised memos. Human-readable, git-tracked, visualizable.
4. **Wiki/external tool** — out-of-band, breaks the git-as-learning-ledger principle.

## Decision
Option 3: `decisions/` directory with prose .md files per decision, plus `## Revisions` convention in research memos that link back to decisions. Global commit rule: non-empty body required for commits touching research/decisions directories.

## Evidence
- Git log already shows concept evolution but requires archaeology to reconstruct.
- Plan files (`.claude/plans/`) are gitignored and expire — reasoning is lost.
- Constitutional principle 12: "The git log is the learning." Decision files make the concept-level learning explicit.
- Publication use case: visualizing a branching tree of concepts requires explicit nodes (files) and edges (cross-references).

## Revisit if
The volume of decision files becomes noisy (>50 per repo) — may need categorization or pruning convention. Or if a better structured format emerges from actual usage patterns.
