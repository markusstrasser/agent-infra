---
title: RSI / autoresearch SoTA sweep (Jun 2026) — cross-axis synthesis & what to integrate
date: 2026-06-19
tags: [rsi, autoresearch, evals, testgrounds, harness-optimization, decision-record]
status: active
---

# RSI / autoresearch SoTA — what to integrate

Decision record synthesizing a 4-axis + epoch-2 research sweep (arXiv · evolutionary
frameworks · GitHub/OSS · lab/practitioner blogposts) into a ranked "what to integrate"
for our three RSI surfaces: **(a)** the harness-level loop (blindspot→act-drain),
**(b)** verifier-gated program-search testgrounds (hutter/anim), **(c)** eval/fitness design.

Source axis-memos (read for detail + caveats):
[[2026-06-19-rsi-sota-arxiv-delta]] · [[2026-06-19-evolutionary-autoresearch-frameworks]] ·
[[2026-06-19-rsi-github-oss-delta]] · [[2026-06-19-rsi-labs-blogposts-delta]] ·
behavioral-eval thread: [[2026-06-19-behavioral-eval-feasibility]].
Cost: $5.35 (steer-mine, separate) + 4 researcher dispatches + 1 epoch-2. Window: May–Jun 2026.

## Meta-finding: the field converged on OUR architecture — integrate bolt-on mechanisms, not a rebuild

The dominant mid-2026 pattern (lab-official AND practitioner-replicated) is our exact loop:
traces → human+model feedback → evals → **eval-gate as the autonomy dial** → agent proposes
harness *diffs* → approve-until-gate-trusted. Independent confirmations:
- OpenAI cookbook "Agent Improvement Loop" flywheel = *verbatim* our verifier-conditioned autonomy.
- OpenAI production tax-agents: 25%→86% correct over 6 wks **while difficulty rose** (existence proof).
- Prosus "Beyond Prompt Optimization": multi-objective incl **token cost** = our `eval-token-costs` rule.
- AHE / SkillOpt / eve / JJAgent: gains come from the **harness on a frozen model** = constitution P1 + Harness-1.

Nothing here says rebuild. The value is specific machinery — and a **measured failure mode of our loop.**

## The through-line: ACCRETION ("policy maze") is our measured failure mode

Triple-confirmed by independent sources:
- **A2H (arXiv:2606.01770):** a monolithic, densely-updated harness *degrades* → keep a harness-**tree** + route per task.
- **Henry Pan, 1,288-iteration replication (blog, 5-26):** rule-accumulation **"policy maze," +55% LOC for ZERO gain.**
- **Our own loop:** blindspot→act-drain accretes rules/hooks monotonically; `gov-shrink` is the *reactive* counter.

→ The top steal (#1) is the **preventive** form: a change that doesn't move its pre-registered metric never gets admitted.

## What to integrate (ranked by leverage × confidence; confidence = independent triangulation)

| # | Steal | Target | Surfaced by (independent) | Maturity / effort | Autonomy |
|---|-------|--------|---------------------------|-------------------|----------|
| **1** | **Predict-then-falsify per harness edit** — pre-register the metric a change should move; accept only if the trace shows the intended mechanism fired; else auto-revert/flag | **(a) loop / act-drain** | AHE(gh, arXiv:2604.25850) + Prosus(labs) + Henry-Pan(labs) — **triple** | mechanism verified (AHE #3 TB2 84.7%); AHE repo fork-farmed → **pattern-extract** | **autonomous** (agent-infra-local) |
| **2** | **Embedding novelty-rejection** — cosine-dedup candidates *before* the slow eval (ablation: the cheap embedding gate is the whole win; skip the LLM-judge 2nd stage) | **(b) hutter/anim** | ShinkaEvolve (arXiv:2509.19349, ~1K★, ICLR poster) | mature; **LOW** — we already own `emb pairs @0.80` | needs go (hutter repo) |
| **3** | **Evidence-posterior promote/retire** — Bayesian per-skill success over failure-mode/token-cost buckets → lifecycle by evidence not frequency/date | **(a) skill/rule lifecycle** | DataArcTech/Bayesian-Agent (arXiv:2606.08348, 47★, pip, stdlib-only, CC adapter) | **adopt-as-DEP** candidate; bus factor unverified | dep-eval (gated) |
| **4** | **Non-stationary fitness / rising bar** — champions re-enter pool + weakness-pressure hard-case mining (FAMOU); Elo-from-pairwise-**races** as fitness, robust to noisy/non-stationary absolute scorers (eve) | **(b) testgrounds + (c) behavioral-eval** | FAMOU(arXiv:2606.10389, verified) + eve(gh, arXiv:2605.09018) + tax-agents(labs) | design effort; pattern-extract | autonomous (design) |
| **5** | **Behavioral over-caution testground** — agent-loop replay of reconstructed correction-scenarios, act-vs-ask graded by tool-call telemetry; #1 is its gate, #4 its rising bar, EFC its case-quality weight | **(c) eval / RSI** | this session ([[2026-06-19-behavioral-eval-feasibility]]); 29 cases, feasibility proven | high (new harness) | operator-go |

Lower-tier testground tuning (cheap, queue): BaSE Thompson depth/breadth bandit (arXiv:2605.29268,
pre-frontier base → mechanism transfers), UCB-mutator routing over our llmx ensemble, weighted-parent
sampling, meta-scratchpad (all ShinkaEvolve/BaSE).

## Correction-QUALITY spine (EFC, epoch-2) — load-bearing for (a)+(c)

**EFC (arXiv:2605.29682, "Scaling Laws for Agent Harnesses via Effective Feedback Compute"):** raw
tokens/tool-calls predict failure at **R²=0.33/0.42**; feedback-**quality** coords (Oracle/Estimated
EFC) hit **R²=0.94**. Quality = *informative + valid + non-redundant + retained*. Implications:
- act-drain should **quality-gate** corrections before minting rules (low-quality → don't admit) — composes with #1.
- the behavioral eval should **weight cases by feedback quality** using EFC's 4 scorable axes.
- (Caveat: base model unnamed → frontier unverified; abstract-level, no code. Mechanism plausible, rates uncertain.)

## Bounds & anti-reward-hacking (epoch-2) — validates existing guards

- **2601.05280** "Limits of Self-Improving…Singularity Is Not Near Without Symbolic Model Synthesis":
  pure-LLM RSI is bounded → our **program-search testgrounds are the right shape** (symbolic synthesis).
- **RHO/self-preference (2606.05922) + Exploration Hacking (2604.28182):** the reward-hacking failure
  modes our **verifier-gating + #1** guard against. Do NOT adopt self-preference/self-judge fitness
  (collides with standing DGM self-judge-Goodhart caution; GAE's online-GRPO-mutator-finetune likewise → watch, don't build).

## Convergent validation (do NOT rebuild)
Our act-drain/blindspot loop, verifier-conditioned autonomy, eval-token-cost discipline, and
program-search grounds are all independently re-derived by the 2026 frontier. SkillOpt + Hermes were
already in-corpus (caught by inventory before re-spend). OpenEvolve (6,549★) = mature AlphaEvolve impl
= what we already model; useful as a reference scaffold, not novel.

## Recommended sequence
1. **#1 predict-then-falsify gate on act-drain** — autonomous, fixes the measured #1 risk (accretion), triple-sourced. Quality-gate (EFC) folds in here.
2. **#2 embedding novelty-rejection into hutter** — cheap, we own the infra (needs go: hutter repo).
3. **#3 Bayesian-Agent** — dep-eval (pip; check bus factor).
4. **#4 non-stationary fitness** for hutter/anim, composing into **#5 the behavioral testground.**

## Confidence grading (AI-relayed; subagent caveats carried forward)
HIGH (verified body/repo + triangulated): #1 mechanism, #2, #4-FAMOU, accretion through-line, convergent-validation.
MED (single-source or asserted): #3 (47★, bus factor), EFC rates (abstract-only), A2H "beats 5 baselines" (asserted, no numbers).
DIRECTIONAL (pre-frontier — mechanism transfers, absolute %s not): BaSE, ReasoningBank, bounds papers (title/preview-level).
