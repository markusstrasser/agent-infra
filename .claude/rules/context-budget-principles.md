---
title: Context Budget Principles
date: 2026-04-05
---

# Context Budget Principles

<!-- Gov-ID: rule:context-budget-principles
goal: keep agent-readable files token-efficient
verifier: evals/graders/governance/context_budget.py
blast_radius: local
-->

Markdown organization rules for agent-readable files. Derived from measured data
and the Gloaguen et al. AGENTS.md study (wiki summaries: -0.5-3% success, +20% cost).

## 1. File Names ARE the Index

Agents scan with `ls` before reading. Names must be self-describing.

Pattern: `{topic}-{subtopic}.md`
Bad: `opus-46-action-plan.md` (opaque qualifier)
Good: `opus-46-skill-routing-adoption.md` (scannable intent)

## 2. When to Index vs Filesystem

| Condition | Use |
|-----------|-----|
| Overlapping topics need routing ("consult X not Y") | Index |
| Descriptive file names + agent has grep | Filesystem alone |
| Summarizing file contents | Never (that's a wiki article) |

Indexes route; they don't summarize. If the agent needs to read the file anyway,
the index entry wasted tokens.

## 3. Fat vs Thin Index

- **Thin** (pipe-delimited, 2-col, 8-12 word triggers): default for path-scoped
  indexes with many entries. Example: `research-index.md`.
- **Fat** (3-col markdown table): only for always-loaded routing of <30
  critical-path files.
- **No index**: directories with <20 descriptively-named files.

## 4. Auto-Load vs Discoverable

| Load behavior | Content type | Examples |
|---------------|-------------|----------|
| Auto-load (no path scope) | Behavioral rules, tool gotchas, conventions | `invariants.md`, `native-patterns.md` |
| Path-scoped | Domain indexes, checklists | `research-index.md`, `doc-format.md` |
| Discoverable (not in rules/) | Research memos, reference data | `research/*.md` |

Never auto-load verbose descriptions of things the agent can inspect directly.

## 5. Table Format

- **2-column**: pipe-delimited (37% token savings over markdown tables, measured).
- **3+ columns**: markdown table (alignment matters for readability).
- **Index tables**: always pipe-delimited regardless of column count.

## 6. Layering Convention

| Layer | Contains | Dedup owner |
|-------|----------|-------------|
| Global `CLAUDE.md` | Universal behavioral rules | Human |
| Project `CLAUDE.md` | Domain identity, architecture, constitution | Human |
| Global `rules/` | Operational gotchas (env, routing, git) | Human |
| Project `rules/` | Domain-specific indexes, checklists | Agent (governed) |

Verified clean as of 2026-04-05 — no cross-layer duplication.

## 7. Skills-Index Budget (2026-06-12)

Codex context-budgets its skills index to ~8,000 chars (developers.openai.com/codex skills
docs); treat that as the cross-vendor ceiling for the SUM of all skill `description:` fields.
Measured 2026-06-12: 5,393 chars across `~/.claude/skills` (67% of budget). No lint until it
binds (measure-before-enforcing). Re-measure when adding skills:
`for f in ~/.claude/skills/*/SKILL.md; do grep -m1 'description:' $f; done | wc -c`

## 8. Measured Baselines

2026-07-13 (global-layer re-slim after 6 months of accretion — the global non-scoped set had
crept 23.6K→~68K chars: CLAUDE.md 40.3K, wakeup-cadence 19.4K. Cut CLAUDE.md 40.3K→31.4K
(narratives → decision/memo anchors), wakeup-cadence 19.4K→9.2K, folded
context-budget-orchestration.md into subagent_usage, relocated remote-ssh-ops.md to
genomics+hutter, compressed eval-token-costs. Global non-scoped set 68K→49.4K chars.
Per-repo canary drop: agent-infra 40.3K→34.4K tok · intel 38.7K→32.9K · genomics 37.5K→31.9K ·
phenome 36.2K→30.3K. All 4 still slightly OVER the 30K ceiling — the residual is project
CLAUDE.md (human-owned constitution) + project rules, not the global layer.):

| Component (agent-infra session) | Chars | ≈Tokens |
|---|---|---|
| Global CLAUDE.md + non-scoped global rules | 49.4K | 12.4K |
| Project CLAUDE.md + non-scoped project rules | ~37K | ~9.4K |
| MEMORY.md index | 5.6K | 1.4K |
| **Total always-loaded** | **~92K** | **~34.4K** |

2026-06-13 (post context-rot slim — global CLAUDE.md 8.1K→3.9K tok, vetoed-decisions
11.8K→4.4K chars, MEMORY.md 10.3K→5.6K chars, 3 rules path-scoped, 1 deleted):

| Component (agent-infra session) | Chars | ≈Tokens |
|---|---|---|
| Global CLAUDE.md + non-scoped global rules | 23.6K | 5.9K |
| Project CLAUDE.md + non-scoped project rules | 37.4K | 9.4K |
| MEMORY.md index | 5.6K | 1.4K |
| **Total always-loaded** | **66.6K** | **~16.7K** |

Measure: sum `wc -c` over CLAUDE.md + rules without `paths:` frontmatter + MEMORY.md.
Every subagent spawn pays this too — budget new always-loaded content against it.
Historical (2026-04-05): Agent-Infra 18.7K / Selve 21K / Genomics 32.9K tokens always-loaded.

Context-rot grounding (Chroma 2025, pre-frontier but mechanism-robust): performance
degrades non-uniformly with input length; topically-close-but-stale text (distractors)
hurts MORE than irrelevant bulk. So prune for staleness first, size second — a wrong
one-liner is worse than a long correct one.
