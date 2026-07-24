---
title: Claude Opus 5 — release facts, benchmarks, routing
date: 2026-07-24
tags: [models, anthropic, opus-5, routing]
status: active
---

# Claude Opus 5 — Release + Integration Memo

**Released:** 2026-07-24  
**Model ID:** `claude-opus-5`  
**Price:** $5 / $25 per MTok (identical to Opus 4.8); Fast mode ~2.5× speed at 2× price  
**Context:** 1M tokens (default = max); max output 128k (300k batch beta)  
**Role in fleet:** **replaces Opus 4.8 as primary Claude default**

## Positioning

Anthropic bills Opus 5 as near-Fable intelligence at half Fable's price — the new default on Claude Max and the strongest model on Claude Pro. Fable 5 ($10/$50) remains the Mythos-class metered top; Mythos 5 still leads pure cyber exploitation.

## Vendor capability claims (not independent)

Launch post emphasizes effort×cost Pareto charts. Directional claims:

| Bench / signal | Claim |
|---|---|
| Frontier-Bench v0.1 | SOTA; >2× Opus 4.8 reward @ lower $/task |
| CursorBench 3.2 | Within 0.5% of Fable 5 peak @ max effort, ½ $/task |
| ARC-AGI 3 | ~3× next-best |
| Zapier AutomationBench | ~1.5× next-best at same $/task |
| OSWorld 2.0 | Best cost curve; beats Fable best at ~⅓ cost |
| GDPval-AA / HLE / DeepSearchQA | Launch charts: best / most efficient |
| Life sciences (internal) | Beats 4.8 all rows; +10.2pp org chem; +7.7pp protein variant |
| Alignment audit | Misalignment score 2.3 — lowest of recent Claude |
| OSS-Fuzz cyber | Near Mythos at *find*; far behind at *exploit* |

**Do not invent AA numbers.** Last independent Claude calibration (AA-Omniscience non-hallucination) is still Opus 4.8 at 64%. Opus 5 remeasure is open.

## Safeguards / fallbacks

- Cyber classifiers: block binary vuln scanning, pentest, exploit gen; ~85% fewer interventions than Fable. Flagged Claude.ai/Code/Cowork requests fall back to **Opus 4.8** by default.
- Biology: Fable bio blocks now route to **Opus 5** (was 4.8).
- API: automatic fallbacks beta; mid-conversation tool changes without cache bust.

## Prompting deltas (load-bearing for harness)

1. Longer default user-facing verbosity — prompt for concision; effort ≠ reply length.
2. Stronger self-verification — **remove** redundant "final verify / double-check" scaffolding (over-verification).
3. Scope expansion — constrain narrow tasks explicitly.
4. More subagent-eager — cap spawn counts; no subagent self-verify loops.
5. Thinking-off only at effort ≤ high; prefer thinking-on + lower effort.
6. Re-sweep effort defaults — low/medium quality holds better than on 4.8; coding start still `xhigh`.

## Integration done this session

| Layer | Change |
|---|---|
| **llmx** | `LITE_ALLOWED` + provider defaults → `claude-opus-5`; keep 4.8 on allowlist; PRICING/CONTEXT; probe default |
| **model-guide** | Primary Claude = Opus 5; digest + BENCHMARKS vendor section + CHANGELOG |
| **critique / llm_dispatch** | `claude_review` profile + preflight probe → Opus 5 |
| **execute / llmx-guide / claude-api / cursor-agent** | Examples + defaults |
| **anim-workbench** | Outer-loop RSI model → `claude-opus-5` |
| **agent-infra** | CLAUDE.md routing examples, detector, usage pricing, harness defaults |
| **global** | `~/.claude/rules/llmx-routing.md` allowlist text; `opus-low` agent def copy |

**Not flipped:** interactive `~/.claude/settings.json` still may pin Fable (operator session model — separate call).

## Open

- [ ] Live self-report probe: key-stripped `claude -p --model claude-opus-5` (API key must be unset — metered path 403/credit).
- [ ] AA remeasure (Intelligence Index, Omniscience non-hallucination).
- [ ] Effort-tier re-sweep (anim style) under Opus 5 low vs medium vs max.
- [ ] Whether interactive default should move Max/Pro product default (Opus 5) vs keep Fable pin.

## Sources

- https://www.anthropic.com/news/claude-opus-5
- https://platform.claude.com/docs/en/about-claude/models
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- https://platform.claude.com/docs/en/about-claude/pricing
