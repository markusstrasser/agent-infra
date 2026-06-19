---
title: "RSI GitHub/OSS Delta — Trending Self-Improving Agent Repos (May–June 2026)"
date: 2026-06-19
axis: "trending GitHub / OSS repos for self-improving agents (last 1-2 months)"
status: COMPLETE
skip_known: [DGM, AutoAgent, DSPy, GEPA, Hermes, Karpathy-autoresearch, AI-Scientist-v1, AI-Scientist-v2, AdaEvolve]
leverage_axes:
  a: harness-level RSI loop (hooks/rules/skills + session-correction mining)
  b: verifier-gated program-search testgrounds (hutter, anim-workbench)
  c: eval/fitness design
---

# RSI GitHub/OSS Delta

Findings appended incrementally as searches complete. Ground every claim in a repo URL.

## RANKED SUMMARY (adoptability × leverage)

All metrics GitHub-API-verified 2026-06-19; AHE leaderboard verify_claim confidence 1.

1. **AHE / NexAU (arXiv:2604.25850)** — `CloudEngineHub/agentic-harness-engineering`, MIT. **Top mechanism steal for axis (a).** 7 git-tracked harness components + trace→sourced-report "Agent Debugger" + **predicted-impact-then-falsify per edit**. Verified #3 on Terminal-Bench 2.0 @84.7%, 69.7→77.0% on GPT-5.4, transfers w/o re-evolution. Repo is fork-farmed (low organic adoption) → **pattern-extract, don't adopt**. The per-edit predict-then-falsify loop + 7-component taxonomy are free upgrades to our act-drain.
2. **DataArcTech/Bayesian-Agent (arXiv:2606.08348)** — 47★, MIT, **pip-installable, stdlib-only**, Claude Code adapter. **Best adopt-as-DEP candidate.** Bayesian posterior over per-skill success conditioned on failure-mode/cost buckets → promote/rewrite/retire skills by evidence not frequency = the principled form of our promote/cut rule. Modest benches; bus factor unverified.
3. **gepa-ai/gepa** — 5222★, MIT, very active. Known-set, but the NEW **`optimize_anything` API** (May 2026) extends reflective text-evolution to arbitrary artifacts (configs/rubrics/skill-docs). Most mature reflective-mutation **dep** when we want LLM-reflector (not random) mutation. Axis (b)/(c).
4. **scaling-group/eve (arXiv:2605.09018)** — 27★, Apache-2.0, wraps Claude Code/Codex. Distinctive steal = **Elo-from-pairwise-races as fitness** (robust when absolute scorers are noisy/non-stationary — our hutter/anim testgrounds). Research artifact → pattern-extract. Axis (c).
5. **microsoft/SkillOpt (arXiv:2605.23904)** — 8320★, `pip install skillopt`. **ALREADY PROBED 2026-05-31** ([[skillopt-vs-autobrowse-veto]]) — validated opportunistic prompt-search for verifiable-oracle skills, NOT standing infra. Listed for completeness; no re-research.

NOT re-researched (already covered): `NousResearch/hermes-agent-self-evolution` (today's Hermes memos; it's itself a DSPy+GEPA consumer). Noted-only: **JJAgent 87.1% TB2** (multi-model routing scaffold, no confirmed repo). All single-author/0-2★/paper-day-fork repos = demo-ware (list at bottom).

**Cross-cutting signal:** the mid-2026 frontier on axis (a) is **harness/scaffold evolution on a frozen model with a clear verifier** (Terminal-Bench/SWE-bench) — AHE, EvE, JJAgent, SkillOpt all confirm gains come from the harness, not the model. This is exactly agent-infra's thesis (constitution P1 + Harness-1). The two mechanisms we lack and should steal: **(i) per-edit predicted-impact-then-falsify (AHE), (ii) evidence-posterior skill promote/retire (Bayesian-Agent).**

## Ground-truth metrics (GitHub API, 2026-06-19 — principal check, not Exa metadata)

| Repo | Stars | Created | Last push | Lang | License | Verdict |
|---|---|---|---|---|---|---|
| microsoft/SkillOpt | 8320 | 2026-05-08 | 2026-06-17 | Python | MIT | **REAL, NEW, high-leverage** — read |
| gepa-ai/gepa | 5222 | 2025-08-05 | 2026-06-18 | Jupyter | MIT | known-set; `optimize_anything` is the NEW delta |
| NousResearch/hermes-agent-self-evolution | 4183 | 2026-03-09 | 2026-06-17 | Python | none | ALREADY COVERED (2 Hermes memos today) — cross-ref only |
| CloudEngineHub/agentic-harness-engineering (AHE) | 0 | 2026-05-20 | 2026-06-15 | Python | MIT | paper-artifact, axis (a) bullseye — investigate |
| gepa-ai/optimize-anything-artifact | 1 | 2026-05-19 | 2026-05-22 | HTML | MIT | paper page only, not adoptable |
| sduyangmin/Skill-Master, gepa-ai/terrarium, *-artifact forks | 0-2 | — | — | — | — | demo/fork noise — skip |

Star-farm note: the *-artifact and personal-fork repos (skillforge, OmniAgent, Self-becoming, gbase, SkillFlow) all surfaced with 0-2 stars / no language / thin history → demo-ware, not adoptable.

## VETTED FINDINGS

### 1. AHE — Agentic Harness Engineering (NexAU-AHE) — TOP NEW FIND for axis (a)
- Repo: https://github.com/CloudEngineHub/agentic-harness-engineering (also qianzy96, rezar1, logos-42, s16173760 forks — all 2026-05-20, a paper-release-day **fork-farm**; original org low organic stars). Paper: arXiv:2604.25850 (html v2 live).
- Mechanism: decomposes a coding-agent harness into **7 git-tracked file-level components** (system prompts, tool descriptions, tool implementations, middleware, **skills, sub-agents, long-term memory**) via "NexAU"; an **"Agent Debugger"** condenses ~10M-token raw traces into layered SOURCED reports (links back to originating trace data); an **Evolve Agent** proposes **evidence-backed edits with a PREDICTED impact, then the next iteration FALSIFIES the prediction**. Loop = `evaluate → analyze → improve` ×10, base model frozen, edits confined to `workspace/`.
- Verifier: **Terminal-Bench 2.0** (pass/fail in `verifier/reward.txt`), E2B sandboxes.
- Results (VERIFIED via verify_claim, confidence 1, snorkel.ai leaderboard): TB2 pass@1 **69.7→77.0% on GPT-5.4**; **#3 on TB2 leaderboard @ 84.7% on GPT-5.5**; beats hand-written Codex (71.9%), ACE, TF-GRPO; **transfers without re-evolution** to SWE-bench-verified + 4 other base models.
- Adoptability: MIT, runnable framework w/ scripts + E2B sandbox config — but it's a **paper artifact** (fork-farmed, low organic users, bus-factor unknown). **PATTERN-EXTRACT, not adopt-as-dep.**
- Leverage **(a) bullseye**: this is agent-infra's RSI loop with TWO mechanisms we lack —
  (i) **predicted-impact-then-falsify per edit** (our act-drain applies fixes but doesn't pre-register a predicted metric flip and auto-falsify it next iter — this is a free upgrade to the loop, and it's literally our constitution's pre-registered-test discipline applied per-edit);
  (ii) **trace→sourced-report "Agent Debugger"** condensing 10M-token traces with provenance links (our blindspot miner clusters signals; AHE's sourced-report-with-links is a more auditable version of the same — compare to our embed-once layer).
  The **7-component git-tracked decomposition** maps 1:1 onto our hooks/rules/skills/sub-agents/memory split — validates the architecture and gives a clean component taxonomy.

### 2. microsoft/SkillOpt — ALREADY RESEARCHED + PROBED (do NOT re-research)
- Repo: https://github.com/microsoft/SkillOpt (8320★, MIT, `pip install skillopt`). Paper arXiv:2605.23904.
- Status: **fully covered in my memory `skillopt-vs-autobrowse-veto.md`** — cloned, probed 2026-05-31 on two datasets (toy + 80-case AVeriTeC). Verdict HOLDS: validated **opportunistic prompt-search trick for verifiable-oracle skills, NOT standing infra**. On a scored claim-verification skill it beat the hand-tuned grader (0.846 vs 0.769, N=26 within noise; +6 over seed solid). Contamination probe clean.
- Mechanism (recap): rollout → reflect (bounded add/delete/replace edits to one `best_skill.md`) → accept only on **held-out validation improvement**; rejected-edit buffer = negative feedback. Reported +19.1pt **inside Claude Code** on GPT-5.5; 52/52 cells best-or-tied.
- Leverage **(b)/(c)**: it's `pip install`-able and genuinely adoptable AS A DEP for any agent-infra skill that has a **deterministic oracle** (the flip-to-institutionalize bar is in memory: ≥3 verifiable skills, ≥500 held-out cases, ≥5-8pp repeated gains, survives a model swap). Cross-ref [[skillopt-vs-autobrowse-veto]].
- NEW since the May probe? Repo still active (pushed 2026-06-17) but no new mechanism surfaced — the v0.1.0 PyPI + 6-benchmark harness is what we already evaluated.

### 3. gepa-ai/gepa — known-set, but `optimize_anything` is the NEW delta
- Repo: https://github.com/gepa-ai/gepa (5222★, MIT, pushed 2026-06-18 — very active). Known-set (SKIP base), but the May-2026 **`optimize_anything` API** generalizes GEPA's reflective text-evolution beyond DSPy prompt-modules to **arbitrary text artifacts** (the `optimize-anything-artifact` 1★ repo is just the paper page; the real landing is in gepa core + dspy issue #9575 requesting the API).
- Leverage **(b)/(c)**: GEPA-as-a-library is the most mature reflective-evolution dep on offer; `optimize_anything` is the hook for evolving non-prompt text (configs, rubrics, skill docs) with the same reflective-mutation engine. Adoptable as a dep where we want reflective (not random) mutation with an LLM reflector.

### 4. NousResearch/hermes-agent-self-evolution — ALREADY COVERED TODAY (cross-ref only)
- Repo: https://github.com/NousResearch/hermes-agent-self-evolution (4183★, pushed 2026-06-17, no license). "Evolutionary self-improvement... optimize skills, prompts, and code using **DSPy + GEPA**."
- Status: deep-dived in TODAY's sibling memos `research/2026-06-19-hermes-deep-dive-local.md` + `research/2026-06-19-hermes-self-evolution-pattern.md`. Not re-researched here. Note: it is itself a **DSPy+GEPA consumer**, which reinforces that GEPA (item 3) is the upstream dep worth tracking, not Hermes' wrapper.

### 5. JJAgent — NEW competitive scaffold result (axis a/c context)
- Surfaced via verify_claim citation (stackfutures.com): **JJAgent hits 87.1% on Terminal-Bench 2.0** via **multi-model routing scaffold** — now leads every single-lab agent. No confirmed canonical repo yet (verify before citing as adoptable). Relevance: data point that **scaffold/routing optimization** (not model swap) is where TB2 gains are coming from in mid-2026 — same thesis as AHE. Note only; find repo if pursued.

### 6. DataArcTech/Bayesian-Agent — BEST ADOPTABLE DEP for axis (a)/(c)
- Repo: https://github.com/DataArcTech/Bayesian-Agent (47★, MIT, pushed 2026-06-16, active). Paper arXiv:2606.08348.
- Mechanism: maintains a **Bayesian Evidence Model per Skill/SOP** — a posterior over success-probability conditioned on **discrete features** (task context, failure mode, token/turn/latency buckets) via a categorical likelihood. After each **verified** trajectory the posterior updates; skills are **ranked / rewritten / retired by posterior, not raw frequency counting**.
- Cross-harness: standardized **JSON trajectory schema**; GenericAgent, mini-swe-agent, **Claude Code** integrate via optional adapters (no vendoring).
- Adoptability: **pip-installable standalone, Python 3.9+, stdlib-only (no runtime deps), CLI + Python API.** Lowest-friction dependency in the whole set. Bus factor unverified (single org, 47★).
- Results: SOP-Bench 95→100%, RealFin 62.5→70% (deepseek-v4-flash, bayesian_full). Modest benches.
- Leverage **(a)/(c) — direct**: this is the *principled* version of our act-drain promote/retire decision. We currently promote/demote fixes on recurrence-count + manual judgment; Bayesian-Agent gives a **posterior-over-skill-success conditioned on failure-mode/cost buckets** — exactly the "promote/cut on evidence, not on a self-imposed date" rule, formalized. The stdlib-only + JSON-trajectory-schema + Claude-Code-adapter design makes it a candidate to **adopt as a dep** for skill/SOP scoring (vs pattern-extract). Evaluate against our existing blindspot→act-drain before adopting.

### 7. scaling-group/eve — co-evolving agent ENSEMBLES via Elo (axis b/c mechanism)
- Repo: https://github.com/scaling-group/eve (27★, Apache-2.0, pushed 2026-06-18). Paper arXiv:2605.09018. (NOT the same as "Vercel Eve" in `research/2026-06-17-vercel-eve-harness-steals.md` — different project, same name.)
- Mechanism: two co-evolving populations — a **solver population** (code repo components) + an **agent population** (coding agents w/ cumulative logs + **Elo scores**). Fitness = **pairwise tournament races** on identical reference sets → win-loss matrix → Elo update; high-Elo agents sampled forward, guidance embedded back into the population.
- Integration: wraps **Codex + Claude Code via CLI** (interactive tmux OR headless JSON-stream subprocess), isolated workspaces, runs on the user's own subscriber quota — same model as our subagent dispatch.
- Adoptability: research artifact (Hydra CLI `uv run python -m scaling_evolve.algorithms.eve.runner`), NOT pip-dep. **Pattern-extract.**
- Results: ICON scientific case study — discovered a positional-encoding mechanism cutting generalization error **>80%** vs hand-designed baseline.
- Leverage **(c) — the distinctive steal = Elo-from-pairwise-races as fitness** (relative, not absolute scoring) for our verifier-gated testgrounds (hutter/anim). When an absolute scorer is noisy/non-stationary (cf. the arxiv-sibling's Red-Queen finding 2606.10389), pairwise tournament + Elo is a robust selection signal. Also a clean **ensemble** layer over the Claude-Code/Codex subagents we already drive.

## Candidates (raw, pre-vetting) — demo-ware / skipped

Star-farm / demo-ware (0-2★, thin history, paper-day clones — all SKIP): sduyangmin/Skill-Master (2★), gepa-ai/terrarium (0★), gepa-ai/optimize-anything-artifact (1★ paper page), dwickyfp/skillforge, YeQing17-2026/OmniAgent, benlongmao/Self-becoming, garyqlin/gbase, beita6969/SkillFlow, redbuzzzzz/ouroboros, openyfai/VYN, breakneo/hermes-agent-self-evolution (personal fork of Nous), thememium/dspy-auto-gepa, Epistates/gepars, Noxus-AI/pydantic-ai-gepa, modaic-ai/gepa-viz, and the ~6 paper-day forks of agentic-harness-engineering.
