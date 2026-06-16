---
title: "Trending Scout — 2026-06-15 (2-day diff)"
date: 2026-06-15
tags: [trending-scout, cursor, claude-code, vendor-updates]
status: complete
window: 2026-06-13 → 2026-06-15
prior: research/trending-scout-2026-06-13.md
---

# Trending Scout — 2026-06-15

**Window:** 2026-06-13 → 2026-06-15
**Sources:** vendor-sweep cache (`docs/vendor/`), WebFetch (CC changelog, Cursor changelog), web search, git log
**Findings:** 2 infra-relevant (Cursor `/review`, RHO paper), 1 deadline flag (Gemini CLI Jun 18), 0 CC version delta, landscape otherwise stable

---

## Headline

**Quiet vendor window.** Claude Code unchanged at **2.1.177** (released Jun 13). The signal is on the **Cursor** side: Bugbot `/review` pre-push landed Jun 10 (IDE only; CLI coming soon) — directly relevant to our Composer CLI + risky-diff-review shadow work. One new harness paper (RHO) worth reading before the next reflect/improve design pass.

---

## New Findings (ranked by value − maintenance)

### 1. Cursor `/review` — pre-push Bugbot + Security Review (Jun 10)

| Field | Content |
|-------|---------|
| Source | [cursor.com/changelog](https://cursor.com/changelog) Jun 10 2026 |
| What it does | `/review`, `/review-bugbot`, `/review-security` run Bugbot/Security Review **before push**. Syncs with GitHub/GitLab Bugbot — same diff already reviewed locally → PR Bugbot skips. Incremental mode: review only what's new since last review. |
| Why relevant | We wired Composer 2.5 headless for `/critique` + `/code-review` (2026-06-14). Cursor's native pre-push review is the vendor-native path to the same job. **CLI support explicitly "coming soon"** — our `agent` CLI integration should watch for this rather than building a parallel pre-push layer. |
| Integration path | **Watch → probe when CLI lands.** Compare against `risky-diff-review` SHADOW (promote/cut ~Jun 21). If `/review` hits CLI with good diff-in/diff-out, it may supersede a custom git-history shadow hook. |
| Current overlap | `research/2026-06-14-cursor-cli-composer-integration.md`, improvement-log risky-diff-review SHADOW, `/code-review` skill. |
| Maintenance | Low if vendor-native; high if we build parallel. |
| Verdict | **Watch** — do not build; re-check when Cursor changelog says CLI `/review` shipped |

### 2. RHO — Retrospective Harness Optimization (arXiv:2606.05922)

| Field | Content |
|-------|---------|
| Source | [arxiv.org/abs/2606.05922](https://arxiv.org/abs/2606.05922) (Jun 2026) |
| What it does | Self-supervised harness optimization from **past trajectories only** — no labeled validation set. Selects a diverse coreset of hard tasks, re-solves in parallel, agent self-validates + self-prefers among candidate harness edits. SWE-Bench Pro 59%→78% in one round (author-reported). Code: github.com/wbopan/retro-harness |
| Why relevant | Our reflect deep-pass + improvement-log drain assumes human disposition for `[ ]` items. RHO is the "no ground-truth labels, use trajectory self-preference" variant — closer to what `/observe` + `/improve harvest` could automate if we had a held-out task slice. Pairs with PACE (accept-gate) and Self-Harness (regression-gate) from the Jun 12 sweep. |
| Integration path | **Read before next reflect-eval (Jun 17 one-shot).** Compare RHO's self-preference gate vs our gov.py invariants + human ratification. Not adopt-grade without reproducing on our task slice. |
| Current overlap | Self-Harness (2606.09498, trending-scout-2026-06-13), PACE (2606.08106, RSI gap sweep). |
| Verdict | **Extract pattern** — read + decisions/ memo if the self-preference gate is better than our current promote/cut heuristic |

---

## Version Bumps

| Tool | Previous (Jun 13 memo) | Current | Notable |
|------|------------------------|---------|---------|
| Claude Code | 2.1.177 | **2.1.177** | unchanged — latest GitHub release Jun 13 |
| Cursor agent CLI | 2026.06.15 build | same family | `agent --version` = 2026.06.15-03-48-54 |
| codex-cli | rust-v0.139.0 | **rust-v0.139.0** | unchanged |
| anthropic-sdk / openai-sdk / google-genai / mcp / modal / fastmcp | (Jun 13 snapshot) | 0.109.1 / 2.41.1 / 2.8.0 / 1.27.2 / 1.5.0 / 3.4.2 | unchanged per `docs/vendor/*-pypi.json` |

---

## Already Known / Filtered

- **CC hook path `if:` (2.1.176)** — already `[ ]` in improvement-log (2026-06-13); no re-route.
- **Nested subagents 5 levels (2.1.172)** — Watch from Jun 13; no change.
- **Self-Harness (2606.09498)** — covered Jun 13; no new data.
- **Cursor SDK Jun 4 batch** (customTools, autoReview, JSONL stores, nested subagents) — we integrated `agent` CLI Jun 14; SDK path is separate, no new delta.
- **Gemini CLI full shutdown Jun 18** — flagged Jun 13; **3 days out**. Live paths use llmx paid API; only residue is `code-review-scout.py` gemini-cli provider option (dead since May 31 free-tier retirement).

---

## Search Log

- **vendor-sweep cache** — CC 2.1.177, codex 0.139.0, PyPI pins unchanged (Jun 15).
- **WebFetch** code.claude.com/changelog — no entries beyond 2.1.176 feature set; 2.1.177 release body empty on GitHub.
- **WebFetch** cursor.com/changelog — Bugbot `/review` Jun 10 (primary new finding).
- **Web search** arxiv harness self-improvement Jun 2026 — surfaced RHO (2606.05922), not in prior memos.
- **Exa** — not run (prior run recovered mid-session Jun 13; vendor half sufficient for this quiet window).
