---
title: Context Budget Principles
date: 2026-04-05
---

# Context Budget Principles

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

## 7. Measured Baselines (2026-04-05)

| Project | Always-loaded | Max (all rules triggered) |
|---------|--------------|--------------------------|
| Meta | 18.7K tokens | 29.5K tokens |
| Selve | 21K | 33.6K |
| Genomics | 32.9K | 37.7K |

Prompt caching reduces ongoing cost of static prefixes. Budget new always-loaded
content against these baselines — each 1K token addition is permanent.
