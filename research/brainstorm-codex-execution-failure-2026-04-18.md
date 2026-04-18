---
title: "Brainstorm Skill Codex Failure — Research Delta + Diagnosis"
date: 2026-04-18
tags: [brainstorm, codex, gpt-5, divergent-thinking, skill-execution]
status: active
---

# Brainstorm Skill Codex Failure — Research Delta + Diagnosis

**Date:** 2026-04-18
**Tier:** Standard | **Trigger:** /observe found 8/8 codex sessions bypassed the brainstorm skill (genomics, automated loop)
**Ground truth:** Extends `divergent-convergent-thinking-llms.md` (2026-03-05) — most mechanisms unchanged.

## TL;DR

The 8/8 codex/GPT-5.4 brainstorm bypass is **not a creativity problem**, it is a **harness-execution problem**. Codex with its 9-MCP execution-first stance treats SKILL.md as advisory background and defaults to `rg`/`sed`/`wc` filesystem analysis. New literature this week (HAIExplore v2, April 6) names this pattern explicitly: "chatbot-based interfaces that prioritize execution cause premature convergence and design fixation." Fix: harden the skill with a Mode Discipline gate that forbids search-tool patterns during ideation phases and requires ≥5 in-conversation candidate ideas before any tool call.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | 8/8 codex sessions ignored brainstorm skill, ran `rg`/`sed` loops to find missing implementations and appended a single survivor | Genomics observe digest 2026-04-18, sessions 019d9ff9 + 7 siblings, identical pathology | HIGH | `artifacts/observe/2026-04-18-1237-genomics/` | VERIFIED |
| 2 | All 8 violated Constitution Rule 6 (≥5 alternatives for design tasks) — converged immediately to "single survivor" | Same digest, quotes from each session | HIGH | Same | VERIFIED |
| 3 | Execution-first chat/agent interfaces cause premature convergence and design fixation | HAIExplore v2 abstract (April 6, 2026) | HIGH | arxiv 2512.18388v2 | [SOURCE: arxiv] |
| 4 | LLM agents exhibit functionalist creativity (observable novelty) but lack ontological creativity (genuine process-level exploration) | Franceschelli & Musolesi review | MEDIUM | arxiv 2604.13242 (April 13, 2026) | VERIFIED-ABSTRACT |
| 5 | RLHF + execution-tuning push frontier models toward statistically average / convergent outputs | Artificial Hivemind, CREATIVEDC | HIGH | arxiv 2512.23601 (covered in March memo) | [TRAINING-DATA, prior memo] |
| 6 | Two-phase scaffolding (explicit divergent → explicit convergent) is the validated fix; +51.5% novelty, +72% distinct outputs at K=100 | CREATIVEDC | HIGH | arxiv 2512.23601 | VERIFIED in prior memo |
| 7 | Temperature alone does not fix divergence (surface diversity ≠ semantic novelty) | Multiple papers, prior memo | HIGH | Prior memo | [PRIOR] |
| 8 | No new published technique in last 7 days specifically addresses reasoning-tuned model over-convergence on ideation | Exa + Perplexity recency search 2026-04-11..18 | MEDIUM | search log | UNSOURCED — null result |

## What Changed In The Last 7 Days

**One directly relevant new paper:**

- **HAIExplore v2** (arxiv 2512.18388v2, 2026-04-06) — "Exploration vs. Fixation: Scaffolding Divergent and Convergent Thinking for Human-AI Co-Creation." Explicitly identifies the failure mode that hit our skill: *"popular chatbot-based interfaces often prioritize execution, generating fully rendered artifacts right away. This issue can lead to premature convergence and design fixation, where users are being anchored to initial outputs."* This is a perfect description of codex's behavior — given a brainstorm skill, it executes (greps the codebase, sed-trims a survivor) instead of exploring.

**One adjacent new paper:**

- **Franceschelli & Musolesi** (arxiv 2604.13242, 2026-04-13) — "On the Creativity of AI Agents." Distinguishes *functionalist* creativity (output looks novel) from *ontological* creativity (process is genuinely exploratory). Argues current LLM agents have the former but not the latter. Implication: even when the skill works, expect functionalist outputs — convergent under the hood.

**Null findings:**

- No new arxiv papers in the 7-day window propose a technique specifically for forcing reasoning-tuned models (GPT-5, o-series, codex) to brainstorm rather than execute.
- No model-vendor blog posts or release notes in the window discuss this failure mode.
- All other technique papers retrieved are from late 2025 / early 2026 and already covered in the March 5 memo.

## Diagnosis

The failure is **not** "GPT-5.4 can't think divergently." It is:

1. **The codex harness has high tool affinity.** 9 MCP servers loaded, no disable flag, ~37K token overhead pre-loaded. The model's prior is "reach for tools."
2. **SKILL.md is loaded as markdown text.** It is advisory in the harness's eyes. There is no architectural enforcement that the model must follow Step 1 before Step 2.
3. **The skill's perturbation rounds dispatch to llmx in background.** Codex then reads the (still-being-written) output file repeatedly while the dispatch is in-flight (`domain-forcing.md` read 11 times consecutively in one session), interpreting partial content as further task instructions, which it then executes via shell.
4. **No in-conversation generation requirement.** The current skill goes from "Step 1: define design space" to "Step 2: generate N ideas (or dispatch)" — the dispatch path lets the agent skip in-conversation generation entirely. Codex takes that path, then loses the thread.
5. **The model's training prior dominates.** When SKILL.md says "denial cascade," codex recognizes the words but defaults to its more-rewarded behavior: execute, find, filter, ship.

This matches the literature: instructions alone are 0% reliable for behavior change (SlopCodeBench 2026-03 finding already in our Constitution). Architecture beats instructions.

## Fix (planned, separate commit)

Three changes to `~/Projects/skills/brainstorm/SKILL.md`, ranked by leverage:

1. **Mode Discipline gate** at the top of the skill: explicitly forbid `rg`/`grep`/`sed`/`wc`/`find`/`sleep && check` and any caller-code analysis during ideation phases. Require ≥5 in-conversation candidate ideas (as plain text) BEFORE any tool call other than packet building. This is architectural — the gate makes it impossible to silently skip Step 2 in favor of execution.

2. **Append-no-poll dispatch contract**: when external dispatch runs, instruct the agent that the result file is NOT to be read until completion is signalled. Polling is forbidden. (Catches the 11x file-read loop.)

3. **Known Issues** entry documenting the 2026-04-18 incident, with session IDs and root cause. Append-only.

**Deliberately not doing:**

- Routing brainstorm exclusively to claude-code. Cleaner architecturally, but the failure mode (instructions ignored under tool-affinity pressure) will recur for any future skill that loses to harness defaults. Better to harden the skill itself so the gate is portable across harnesses.
- Stop-hook validation that artifacts contain ≥5 alternatives. This is a useful belt-and-suspenders addition but should land as a separate, measured change. Hook-first risks bundling. Per Constitution: isolate harness changes.

## What's Uncertain

- Whether the Mode Discipline gate will hold under codex's tool-affinity pressure. Architecture beats instructions empirically; a top-of-skill imperative is still instruction. The real test is the next observe pass after deployment.
- Whether the upstream caller (whatever automation invoked brainstorm 8x on codex) is the right escalation — possibly a propose-work or pipeline_stages.py loop that should be inspected separately.
- HAIExplore v2 is HCI-flavored; their proposed UI scaffolds (visual mode-switching) don't translate directly to a CLI agent. The cited mechanism (execution-first → fixation) does.

## Search Log

| Tool | Query | Window | Hits | Useful |
|------|-------|--------|------|--------|
| Local grep | `divergent\|brainstorm\|creativ\|ideation` | research/ | 27 files | 2 (March memo + Mar 6 reasoning-scaffolding) |
| Read | brainstorm SKILL.md, skill.json | now | n/a | full context |
| Read | improvement-log brainstorm entries | all-time | 5 | confirmed prior 2026-03-26 dedup fix; new 2026-04-18 entry |
| Exa research-paper | LLM divergent thinking creativity benchmark prompting 2026 + 3 add'l queries | 2026-04-11..18 arxiv | 12 | 1 directly relevant (HAIExplore v2), 1 adjacent (Franceschelli) |
| Exa | GPT-5 fails brainstorming generates filtering | 2026-03-15..04-18 | 10 | 0 relevant — null result |
| Perplexity | Last 7 days frontier-LLM creativity / ideation / GPT-5 over-convergence | week | n/a | confirmed null — no new technique published this week |

## Prior Memos Referenced

- `divergent-convergent-thinking-llms.md` (2026-03-05) — Artificial Hivemind, CREATIVEDC, denial prompting, NEOGAUGE, multi-agent debate, hallucination-creativity tradeoff
- `reasoning-scaffolding-divergent.md` (2026-03-06) — Think² metacognition, FunSearch (LLM-as-mutator + deterministic evaluator), AI Scientist v2 patterns

<!-- knowledge-index
generated: 2026-04-18T19:53:51Z
hash: a8da978d1ab9

title: Brainstorm Skill Codex Failure — Research Delta + Diagnosis
status: active
tags: brainstorm, codex, gpt-5, divergent-thinking, skill-execution
sources: 1
  TRAINING-DATA: , prior memo
table_claims: 8

end-knowledge-index -->
