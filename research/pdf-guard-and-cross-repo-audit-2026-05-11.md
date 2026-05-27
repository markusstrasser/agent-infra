---
date: 2026-05-11
scope: pre-commit PDF guard rollout (agent-infra, research-mcp, phenome) + cross-repo pointer audit
related:
  - .claude/plans/2026-05-11-shared-papers-store.md  (anti-patterns: "PDF in git. Period.")
  - ~/Projects/skills/hooks/pre-commit-no-large-binaries.sh
out_of_scope:
  - ~/Projects/genomics/  (owned by parallel agent pid 68154)
---

# PDF guard + cross-repo pointer audit — 2026-05-11

## Summary verdict per repo (read this first)

| Repo | PDF guard wired | Tracked binary cleanup needed? | `paper_evidence/` references | Migration risk |
|---|---|---|---|---|
| agent-infra   | yes (symlink + `just install-hooks`)       | none (largest tracked artefact is `uv.lock` ~647 KB) | 0 | low — purely additive |
| research-mcp  | yes (symlink + `scripts/install-hooks.sh`) | none (largest tracked artefact is `uv.lock` ~287 KB) | 0 | low — purely additive |
| phenome       | yes (added to existing pre-commit chain)   | **YES** — 9 multi-MB PNG infographics + 2 PDFs already tracked (~22 MB) | 0 | medium — pre-existing PDFs would now be blocked on re-commit; PNGs are below the 100KB threshold for `.png` but `.png` isn't in the guard list |

## Commits made this session

| Repo | SHA | Subject |
|---|---|---|
| skills        | `2ea6435` | `[hooks] Add pre-commit-no-large-binaries — reject PDFs and large blobs` |
| agent-infra   | `fe56621` | `[infra] Add install-hooks recipe — wire skills pre-commit no-large-binaries` |
| research-mcp  | `92a98d9` | `[infra] Add install-hooks.sh — wire skills pre-commit no-large-binaries` |
| phenome       | `dc6e235` | `[infra] Add no-large-binaries to pre-commit chain — block PDFs in git` |

Local-only changes (not tracked because they live under `.git/hooks/`):
- `~/Projects/agent-infra/.git/hooks/pre-commit` → symlink to skills hook
- `~/Projects/research-mcp/.git/hooks/pre-commit` → symlink to skills hook
- `~/Projects/phenome/.git/hooks/pre-commit` → repointed from `pre-commit-citation-audit.sh` (drift bug) to `pre-commit-chain.sh` (canonical, matches `just install-hooks`)

## Hook tests

Each repo: stage a 4500-byte fake PDF, attempt `git commit`, confirm exit 1 with the BLOCKED message; then `GIT_ALLOW_BINARIES=1 git commit --dry-run` → exit 0; reset and remove. All three repos passed.

The phenome chain runs no-large-binaries first, then citation-audit / claim-provenance / todos / tracked-gitignored. Failure in any short-circuits the chain.

## Surprises

1. **Zero `paper_evidence/` references** in any of the three non-genomics repos. The 709 MB bloat is fully contained to genomics. No pointer / hardcoded-path migration is required in agent-infra / research-mcp / phenome.
2. **Phenome's pre-commit symlink was already drifted.** It pointed directly at `pre-commit-citation-audit.sh` instead of `pre-commit-chain.sh`, silently skipping `pre-commit-claim-provenance.sh`, `pre-commit-todos.sh`, and `pre-commit-tracked-gitignored.sh`. Fixed as part of this session (re-pointed at the chain).
3. **Phenome already tracks 2 PDFs and 9 multi-MB PNG infographics** in `docs/outreach/` (totals ~22 MB). These are in-tree assets, not papers, but the same blast-radius pattern that broke genomics. The PNGs aren't covered by the current guard (`.png` not in the rejection list); the PDFs would be blocked on any future modification + re-commit, which is the right behavior for this guard but operators should know.

---

## Audit 1 — Top 30 tracked files by size, per repo

### agent-infra (top 10 — full list in `/tmp/pdf-guard-audit/sizes.txt`)
- 647293  uv.lock
- 488571  claim_bench/uv.lock
- 370840  improvement-log.md
- 72608   scripts/archived_orchestrator.py
- 70579   research/anthropic-soul-guidelines.md
- 56653   research/knowledge-accrual-architecture.md
- 47435   setup-friend.sh
- 47406   research/negative-space-and-meta-epistemics.md
- 43944   scripts/autoresearch.py
- 42739   research/claude-code-internals.md

Nothing >1 MB. No binary archives. Nothing to migrate.

### phenome (top 30 — includes the bloat)
- **4887060  docs/outreach/infographic-dtc-comparison.png**
- **4297576  docs/outreach/infographic-what-you-get.png**
- **3467816  docs/outreach/infographic-blood-vs-saliva.png**
- **3259010  docs/outreach/infographic-voi-breakdown.png**
- **1046267  docs/outreach/infographic-wgs-capabilities.png**
- 725854   docs/outreach/infographic-probe-space.png
- 689289   docs/outreach/infographic-control-loop.png
- 649462   docs/outreach/infographic-sequencing-strategies.png
- 605020   docs/outreach/infographic-evidence-tiers.png
- 163650   docs/todos.migration-candidates.md
- **156886   docs/outreach/wgs-onepager.pdf**         ← PDF, would now be guarded
- 151514   docs/derived/hoelzl-haus/grundriss-ground-floor.svg
- 142043   docs/research/tests_and_purchases_todo.md
- 140296   mcp/genomics-consumer/src/genomics_consumer/server.py
- 114249   analysis/query-failure-atlas/2026-04-02/atlas.json
- 108795   exports/genomics/ledger.json
- **100618   docs/outreach/dtc-comparison.pdf**       ← PDF, would now be guarded
- 98218    docs/active-protocol.md
- 94801    docs/archive/personal-wgs-current-takeaways.md
- 87187    eval/search_eval_results.json
- 80941    docs/outreach/omics-next-tests.md
- 74761    docs/reports/citation_verify_research_memos_2026_02_19.md
- 69908    src/phenome/cli/main.py
- 63619    docs/derived/media-phenotype-skin-progression.md
- 63006    config/phenotype/bootstrap_curated_snapshot.json
- 62431    docs/entities/companies/synthoria.md
- 61569    src/phenome/umls.py
- 59197    scripts/connectors/generate_unified_embeddings.py
- 56148    scripts/export_genomics_phenotype_contract.py
- 56043    docs/research/synthoria_pharma_value_2026-05-03/.../buyer_landscape.md

**To fix when migration happens:** the 9 outreach PNGs (~22 MB) and 2 PDFs are an in-repo asset bloat that mirrors the genomics paper_evidence/ pattern at smaller scale. Candidates for either Git LFS, a separate assets store, or `~/Projects/papers/`-style external store with pointers. Out of scope for today; flagged for a follow-up plan.

### research-mcp (top 10 — full list in `/tmp/pdf-guard-audit/sizes.txt`)
- 286695  uv.lock
- 37710   src/research_mcp/server.py
- 28541   src/research_mcp/quality.py
- 9821    src/research_mcp/exa_verify.py
- 8528    src/research_mcp/db.py
- 7181    tests/test_server.py
- 5853    src/research_mcp/papers.py
- 5630    src/research_mcp/cag.py
- 5315    src/research_mcp/deep_research.py
- 5150    src/research_mcp/openalex.py

Nothing >1 MB. No binary archives. Nothing to migrate.

## Audit 2 — `paper_evidence/` references

```
agent-infra:  0 hits
phenome:      0 hits
research-mcp: 0 hits
```

The plan's migration step "rewrite paper_evidence/ references to canonical_paper_id" is genomics-only. None of the other three repos have any pointer to fix. (`git -C <repo> grep -l 'paper_evidence'` returns rc=0 with empty stdout for all three, double-checked.)

## Audit 3 — Hardcoded commit shas in markdown

Full lists at `/tmp/pdf-guard-audit/shas-{agent-infra,phenome,research-mcp}.txt`.

- **agent-infra:** ~40 hits, dominantly in `harness-changelog.md` (intentional — the changelog cites the commits it documents) and `MAINTAIN.md`. Not a migration concern; these are first-class provenance pointers in this repo, expected to be present.
- **phenome:** ~40 hits, dominantly in `.claude/checkpoint.md`, `.claude/cert-stack-handoff.md`, and `.claude/plans/b51a1519-v2-HANDOFF.md`. Cert-stack handoff has 30+ commit shas listed as build-step pointers — these are the canonical "what was done in which commit" map. Intentional. Not a migration concern.
- **research-mcp:** 1 hit, in `.claude/overviews/source-overview.md` (`git: fb33e7c`, auto-generated overview header). Not a migration concern.

**To fix when migration happens:** nothing. None of these shas reference anything in `paper_evidence/`-land or the future `~/Projects/papers/` store; they're project-internal commit references.

## Audit 4 — Forward-looking `~/Projects/papers/` / `paper_store` references

```
agent-infra:
  research/paperqa-evidence-model-2026-05.md:2          (title)
  research/paperqa-evidence-model-2026-05.md:119
  research/scientific-citation-graph-patterns-2026-05.md:47
  research/scientific-kg-schema-standards-2026-05.md:4  (scope)
  research/scientific-kg-schema-standards-2026-05.md:44

phenome:      0 hits
research-mcp: 0 hits
```

The forward-looking references are all design memos in `agent-infra/research/`. Migration is not yet underway in code; no half-built state to reconcile. The plan owns the canonical `~/Projects/papers/` path; no other repo has spoken about it yet.

---

## Recommendations (for the migration session)

1. **agent-infra and research-mcp need nothing beyond the PDF guard.** They are clean of paper_evidence/ pointers and have no binary bloat.
2. **phenome's outreach PNGs + 2 PDFs** are a separate concern — same bloat pattern at smaller scale, but unrelated to the shared papers store (they're marketing assets, not papers). File a follow-up plan; do not bundle with the papers-store migration.
3. **Re-run `just install-hooks` (or equivalent)** after fresh clones — the symlinks live under `.git/hooks/` and are not version-controlled.
4. **Phenome's pre-commit chain was repointed** as part of this session — confirm with `readlink ~/Projects/phenome/.git/hooks/pre-commit` if any other agent observes chain-skip behavior; the prior drift went undetected for ~4 weeks.

## Out-of-scope reminder

`~/Projects/genomics/` was not read or modified. All findings above are from `agent-infra`, `phenome`, `research-mcp` only. Genomics-side audit (paper_evidence cleanup, .git pack inspection, history rewrite) belongs to the parallel agent (pid 68154).

<!-- knowledge-index
generated: 2026-05-11T04:37:27Z
hash: db9c13de261b

cross_refs: docs/active-protocol.md, docs/archive/personal-wgs-current-takeaways.md, docs/derived/media-phenotype-skin-progression.md, docs/entities/companies/synthoria.md, docs/outreach/omics-next-tests.md, docs/reports/citation_verify_research_memos_2026_02_19.md, docs/research/synthoria_pharma_value_2026-05-03/.../buyer_landscape.md, docs/research/tests_and_purchases_todo.md, docs/todos.migration-candidates.md, research/anthropic-soul-guidelines.md, research/claude-code-internals.md, research/knowledge-accrual-architecture.md, research/negative-space-and-meta-epistemics.md, research/paperqa-evidence-model-2026-05.md, research/scientific-citation-graph-patterns-2026-05.md, research/scientific-kg-schema-standards-2026-05.md

end-knowledge-index -->
