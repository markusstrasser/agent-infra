---
title: Trending Scout — 2026-08-01 (3d delta since 07-29)
date: 2026-08-01
---

# Trending Scout — 2026-08-01

Window: 2026-07-29 → 2026-08-01. Thin delta pass (freshness DUE). Prior: `trending-scout-2026-07-29.md`.

## Vendor / model

| Item | Notes | Action |
|------|-------|--------|
| **GPT-5.6 Luna/Terra price cut (2026-07-30)** | Luna $0.20/$1.20 (−80%), Terra $2/$12 (−20%), Sol unchanged. Landed in llmx@`2f7abfc`, skills model-guide@`2afccf6`. agent-infra `usage-check.py` vendored map was stale → drift-test red 2026-08-01; synced this package. | **Adopted** (sync) |
| **DeepSeek V4 Flash on openrouter** | llmx PRICING: `deepseek/deepseek-v4-flash` + `-0731` @ $0.14/$0.28 (verified 2026-08-01). | Optional cheap lane — not Default Routing |
| **Claude Code** | Still 2.1.220 (binary-extract freshness ok) | No bump |
| **Opus 5** | Primary Claude; subscription route stable | No change |

## Agent surface

- No new Claude Code major release in window.
- Agent-tool opus pins: skills already notes 2026-07-29 re-measure (honored); Fable still unmeasured.

## Not promoted

- DeepSeek as default cheap lane (subscription Luna still $0)
- Re-litigating Fable subscription status

