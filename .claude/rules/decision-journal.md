# Decision Journal Format

One file per decision in `decisions/`, format: `YYYY-MM-DD-slug.md`. Template in `decisions/.template.md`.
Records use YAML frontmatter for machine-readable metadata (concept grouping, typed relations, provenance).

**Convention for research memos:** When updating a memo with revised understanding, add a dated `## Revisions` entry at the bottom. Only for claim/interpretation/confidence changes — not wording/organization. The git diff shows what changed; the revision note says *why*.

**Cross-repo convention:** Cross-repo decisions live canonically in one repo (usually meta for infrastructure). Affected repos get a one-line stub: `See [repo]/decisions/YYYY-MM-DD-slug.md`.

**Commit bodies for concept shifts:** Commits touching `research/` or `decisions/` should have a non-empty body naming the concept affected and what changed directionally.
