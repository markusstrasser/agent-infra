---
date: 2026-04-24
status: concluded
topic: skills / context-budget / life-sci
recommendation: keep-separate
---

# Life-Sci Skills Consolidation — Keep Separate

Context: 2% skills budget exceeded in Claude Code sessions. Description trims
(committed 798eae3 in ~/Projects/skills) recovered ~850 tokens. Question: do
`bio-verify`, `life-science-research`, `data-acquisition`, `census-data`,
`dataset-register` also warrant consolidation?

## Verdict: keep all five separate

The nuance cost is higher than the context gain. Mode-based consolidation
(`observe`, `critique`, `analyze`) works when modes are *operational variants
of the same verb*. Here the verbs differ: **audit** (bio-verify) vs **route**
(life-science-research) vs **download** (data-acquisition) vs **query** (census-data)
vs **catalog** (dataset-register).

## What would be lost

| Skill | Nuance at risk if merged |
|-------|--------------------------|
| bio-verify | 14 claim-type × 11-domain routing matrix, CPIC-vs-gnomAD MCP dispatch rules, 17-item known-issues catalog, re-verification step |
| life-science-research | Router-first discipline, entity-conflict resolution before retrieval, 9 evidence lanes with source-specific recipes (not generic API lists) |
| data-acquisition | Probe-before-pull (HEAD, size check), Wayback Machine fallback, codebook-alongside-data convention, topic-local staging paths |
| census-data | Variable codes (B05002_013E, B19013_001E), sample codes (us2022a/b), QWI geography nesting rules, IPUMS polling loop |
| dataset-register | Card format, dedup rule, cross-topic shared schema |

## Only plausible merge (rejected)

`data-acquisition + census-data → data-sources`. Both pull external data.
Rejected because census-data's tight API specificity (variable codes,
polling loops) is not a generic data-ops concern; merging flattens it.

## Also rejected

- **bio-verify + life-science-research → biomed** — collapses
  router→dispatch→synthesize into a single invocation; different verbs.
- **data-acquisition + dataset-register → dataset-ops** — register is
  post-acquisition metadata; different invocation context (one is
  "fetch new data", one is "formalize what's staged").

## Further trim options (no merge)

If budget still tight after the description trim:
- Remove "ordered by verification priority" intro table from bio-verify body.
- Remove "lessons from Codex" preamble from life-science-research body.
- Shorten evidence sections in data-acquisition.

These recover ~100 tokens in descriptions/front-matter if retained in body
summaries. Note: body text is *not* in the 2% budget — only frontmatter
`description` is. So body trims only help if they leak into descriptions.

## Revisions
None.

<!-- knowledge-index
generated: 2026-04-24T20:45:24Z
hash: a0c9b95812d5

status: concluded
table_claims: 4

end-knowledge-index -->
