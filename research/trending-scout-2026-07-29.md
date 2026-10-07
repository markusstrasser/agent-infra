---
title: Trending Scout — 2026-07-29
date: 2026-07-29
tags: [trending-scout, vendor, freshness]
status: complete
window: 2026-07-09 → 2026-07-29
---

# Trending Scout — 2026-07-29

**Window:** 2026-07-09 → 2026-07-29 (~20 days; freshness DUE cleared)  
**Sources:** `vendor-versions.py` (this run), OpenAI GPT-5.6 GA notes, prior memos (07-09 scout + Opus 5 routing commits), codex-cli local `--version`  
**Findings:** mostly **version bumps + confirmations** of mid-July model suite GAs; no new adopt-grade harness primitive beyond what we already wired.

---

## Headline

Since 07-09: **Claude Code 2.1.205 → 2.1.220**, **Codex CLI 0.143 → ~0.144–0.146**, Agent SDK py **0.2.114 → 0.2.128** / ts **0.3.205 → 0.3.220**. Model side: **Claude Opus 5** is our default Claude (already adopted 07-24/25); **GPT-5.6 Sol/Terra/Luna** GA was 07-09 (already in routing). Local lag: Gemini CLI npm 0.53 vs local 0.49; Modal 1.5.3 vs local 1.4.2; Kimi CLI pypi 1.49 vs local 0.29.

## Version table (now vs last scout)

| Tool | 2026-07-09 scout | 2026-07-29 |
|------|------------------|------------|
| Claude Code | 2.1.205 | **2.1.220** |
| Claude Agent SDK py/ts | 0.2.114 / 0.3.205 | **0.2.128 / 0.3.220** |
| Codex CLI (npm) | 0.143.0 | **0.146.0** (local **0.144.6**) |
| Anthropic Python SDK | (prior) | 0.120.2 |
| MCP Python / TS | — | **2.0.0** / 1.30.0 |
| Gemini CLI (npm / local) | 0.50 / 0.49 | **0.53 / 0.49** (local lag) |
| Modal (pypi / local) | 1.5.1 / 1.4.2 | **1.5.3 / 1.4.2** (local lag) |
| OpenAI Python SDK | — | 2.50.0 |

## New / confirm findings

### 1. GPT-5.6 family GA (Sol / Terra / Luna) — 2026-07-09
| Field | Content |
|---|---|
| Source | openai.com/index/gpt-5-6/, help center model release notes |
| What | Sol flagship, Terra mid, Luna cheap; Codex + ChatGPT Work product merge narrative mid-July |
| Why relevant | Already our Default Routing table (Sol/Terra/Luna). Codex subscription path live for this RSI package cosign. |
| Verdict | **Already adopted** — no new wire. Local codex 0.144.6 is fine; optional bump to 0.146. |

### 2. Claude Opus 5 as primary Claude
| Field | Content |
|---|---|
| Source | agent-infra commits 29b67d2 / research/2026-07-24-claude-opus-5-release.md |
| What | Opus 5 replaces 4.8 as default Claude; Fable stays metered opt-in |
| Why relevant | Already in model-guide + llmx routes |
| Verdict | **Already adopted** |

### 3. Claude Code 2.1.205→2.1.220 patch train
| Field | Content |
|---|---|
| Source | vendor-versions local = 2.1.220; binary-extract freshness ok |
| What | Patch train past the 07-09 scout's 2.1.205 endpoint |
| Why relevant | Hook/background-agent contracts from 198–205 still the load-bearing delta; patch train likely incremental |
| Verdict | **Watch** — no forced re-extract unless doctor/hooks-smoke regresses (they pass post SessionStart fix) |

### 4. Local tool lag (not adopt)
| Tool | Lag | Action |
|------|-----|--------|
| Gemini CLI | 0.49 local vs 0.53 npm | Optional `npm i -g` when needed |
| Modal | 1.4.2 local vs 1.5.3 pypi | Genomics/Modal work only — **out of scope this package** |
| Kimi CLI | 0.29 local vs 1.49 pypi | Opt-in open-weight lane; bump if used |

## Deferred / already tracked
- Grok 4.5 named niche — unchanged
- Fable 5 metered — unchanged
- CC background-subagent Notification consumer — still Evaluate from 07-09

## Search log
- `vendor-versions.py` 2026-07-29 20:50 UTC
- Web: OpenAI GPT-5.6 GA / Codex product notes
- Prior: `research/trending-scout-2026-07-09.md`
