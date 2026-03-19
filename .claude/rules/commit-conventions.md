# Meta Commit Conventions

Supplements the global commit message format with meta-specific rules.

## Evidence Trailers

`Evidence:`, `Affects:` trailers required for commits touching:
- Classification/curation logic changes
- Governance files (CLAUDE.md, MEMORY.md, hooks, improvement-log)

## Concept Shift Bodies

Commits touching `research/`, `decisions/`, or index-referenced docs must have a non-empty body naming the concept affected and what changed directionally. `git log --format='%s%n%b' -- decisions/` should read as a concept evolution timeline.

## Cross-Project Provenance

`Source:` trailer for cross-project provenance. When a commit implements a finding/decision from another repo, add `Source: repo@sha` (e.g., `Source: intel@f9dfcc9`). Greppable breadcrumb so agents can trace motivation across repos.
