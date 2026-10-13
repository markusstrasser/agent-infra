---
title: Recent search/branching policies over long-running frontier agents (2026-08-13 → 2026-10-13)
date: 2026-10-13
tags: [agent-search, branching, fork, parallel-vs-sequential, plateau, harness-evolution, loop]
status: complete
---

**Verdict:** In this window, the best-controlled frontier evidence says the search topology over agent runs matters less than two things around it: selection (picking the winner without an oracle) and when the run changes direction after a stall. With GLM 5.2 and Kimi K3 under matched wall clock, Chain, Greedy, UCB1 and Best-of-N tree search were statistically tied, and one long session beat all of them on medal rate. Three parallel sessions raised the oracle ceiling, but the self-select gap ate the gain (2609.40303). Native sub-agent concurrency in Codex, Claude Code and Kimi Code moved resolution from −11.9 to +2.3 pp at 1.41–3.31× tokens (2610.10263). Forking from a restored mid-trajectory state beat 5 independent restarts by 8–15 points at equal or lower tokens with GPT-5.6 Sol and Opus 4.8 in 3 of 4 cells (2610.04889). A matched-budget Go-Explore run on a cheap Claude Haiku inverted this (68% vs 24%) unless the progress lived outside the repo (2610.13841). The strongest positive mechanism is a stall-triggered structural change: MILO's orchestrator, which fires after 3 flat rounds, was the largest ablation step (+5.6 RR@5, Opus 4.8, TB2.1), and AIDE² independently discovered "every 5 steps fork the global best under a different strategy arm". Our wakeup-cadence `stale_count` escalation already encodes this lever (HAD-LEVER). The one token-matched continuation control in the set, MIRA (2610.02525), recovered most of a "better policy" gain by letting baselines spend the same tokens. Treat any unmatched-token policy claim, including several below, as upper bounds.

Depth: Standard · Window verified per paper via arXiv API `published` dates · No commit (per dispatch).

## Ranked table

Read depth: **FT** = method and results read in the extracted full text; **PT** = abstract plus the named sections; **AB** = abstract only. Grade = hindsight vs local priors from a `grep -rliE` probe over `agent-infra/research`, `~/.claude/rules`, `hutter/research`, `skills/{doe,eval,brainstorm}` (rg returned nothing in this shell, a tool failure rather than an absence, so the probe used grep; `~/Projects/arc-agi*` does not exist at that path, so arc-agi was not graded).

| # | arXiv · title · date | Model(s) | Mechanism | Key number vs equal-compute baseline | Cost / tokens | Seeds | Read | Grade (local file) |
|---|---|---|---|---|---|---|---|---|
| 1 | 2609.40303 How Much of a Harness Does a Strong Agent Need for Autonomous MLE? · 09-30 | GLM 5.2, Kimi K3, DeepSeek V4 Pro/Flash (Gemma 4 31B weak control) | Ladder of harness interventions in one codebase; tree-search policies vs single long session vs +parallel/+delegation; vs 4 OSS harnesses | Search policies tied (UCB1 − BoN +2.71 pp, CI −1.44..+6.60); single session vs BoN +5.09 pp pct, +11.9 pp medal; +3 parallel 52.4% vs 55.7% medal (oracle up, self-select gap eats it); BoN self-select gap 6.83 pp | $12.12/run single session vs $1.95 AiScientist (cache-read dominated) | 3–4/task (24h), 6–10 (6h) | FT | HAD-PARTS: `2026-10-13-idea-basins-fork-flush-related-work.md` has parallel-vs-single (Elo-per-token, opposite sign); the **selection-gap** finding is NOVEL |
| 2 | 2610.04889 ForkPilot · 10-04 | GPT-5.6 Sol, Opus 4.8 (xhigh) in production host; Kimi K3, DeepSeek V4 Flash, Qwen 4–27B | Restore earlier env state and fork; learned when/how-much-to-fork controller priced as reward − λ·tokens | Frontier: RTS beats BoN-5 by 8–15 pts at ≤ equal tokens in 3/4 cells; ForkPilot −2.8..−4.2 pts vs RTS at 0.59–0.78× raw tokens (one cell +3.6) | Raw/uncached token ratios reported; −22..−41% raw | frontier table single numbers, no CI | FT | HAD-PARTS: idea-basins memo (F&F fork); learned fork controller NOVEL |
| 3 | 2609.38349 MILO · 09-29 | Opus 4.8, gpt-oss-120b; GPT-5.5 judge | 3 islands of whole-harness lineage trees; rejected mutations kept; stall counter (P=3) triggers orchestrator diagnose → graft/speciate/reassign | Same 3 seeds + 72 h for all 6 search baselines: TB2.1 +12.0 RR@5 vs best prior +4.5; ablation: +orchestrator is the largest step (80.5 → 86.1); weakest seed produced the best harness after grafts | Evolved harness 0.74× tokens; search-time tokens not reported | k=5/3 rollouts, clustered CIs | FT | **HAD-LEVER**: `~/.claude/rules/wakeup-cadence.md` (`stale_count ≥2 → change a frame`); islands HAD-PARTS `2026-06-19-evolutionary-autoresearch-frameworks.md` (AdaEvolve) |
| 4 | 2609.26457 AIDE² (RSI of research agents) · 09-22 | Opus 4.7 outer, Gemini 3 Flash inner | 8-day RSI run discovered UCB1 over 5 strategy arms + fork global best every 5 steps under a new arm | Grade 0.703 → 0.778 vs human-built 0.749; matches/exceeds human baseline on 4 held-out benchmarks; reward hacking 55% → 32% | Budget covers tokens + execution; not tabulated | ALE 10/task, MLE 3, FML 3 | FT | HAD-PARTS: evolutionary memo (UCB1-over-models, BaSE); stall fork = idea-basins F&F |
| 5 | 2610.10263 Dynamic Concurrency in Long-Horizon Coding · 10-07 | Codex GPT-5.4, Claude Code Opus 5, Kimi Code K3 | Native sub-agent spawning on vs off, 354 tasks | −11.9..+2.3 pp resolution; Claude Code −24.0 pp SWE-V, +14.3 pp LoopsBench; faster in only 12.6% | 1.41–3.31× tokens; $20,780 total | 1 run per cell | PT | HAD-PARTS: `2026-05-27-multi-agent-coordination-4w.md` |
| 6 | 2610.02525 MIRA · 10-01 | GPT-5.5 (+Qwen3.6-27B) | Meta-reasoner writes work orders; each runs in a fresh Codex loop | IMOProofBench Adv 67.1% → 100% (3 trials) at equal runtime; **token-matched continuation recovers most of the gap**; inertia 0.958/0.862/0.772 | Output tokens matched in control | 3 trials | PT (§6.1 FT) | HAD-PARTS: idea-basins memo (SLA fresh context); token-matched control NOVEL |
| 7 | 2609.17846 PrimeScientist · 09-15 | GPT-5 (Codex CLI) | Plan tree + budget-aware MCTS allocator | Same 1.5M tokens: FIRE-Bench 0.774 vs 0.702 AutoResearch with 13.3 vs 27 attempts; fewer attempts on 23/24 tasks; AutoLab gain concentrated in 1 task | 1.5M-token budget incl. planning | n=1 per config | PT | HAD-PARTS: evolutionary memo (BaSE depth↔breadth bandit) |
| 8 | 2610.02361 SEDIMA · 10-01 | GPT-5.4, DeepSeek V4 Pro, Gemini 3 Pro | Cross-run clustered insight memory conditioning mutations | +5.5% AlgoTune, +6.6% ALE-Bench LITE at 100 evaluated candidates; 29.5–34.2% fewer iterations | Matched on candidates, not tokens | 3 | PT | HAD-PARTS: evolutionary memo (ShinkaEvolve meta-scratchpad) |
| 9 | 2609.37834 Mixture of Self-Improving Branches · 09-29 | Sonnet 4.5, Gemini 3 Flash; Opus 4.6 proposer | 2 branches with evolving dev subsets + proposal policies, router | TB2.0 44.8 → 50.0 (58 tasks); math Gemini 46 → 62; NOT equal compute | 1.21–1.71× Meta-Harness solving tokens | none | PT | NOVEL (branch-specific evolving objective) |

Below the bar but decision-relevant: **2610.13841** (Daytona Go-Explore snapshots, Claude Haiku, pre-registered 5 tasks × 5 seeds at 1M tokens: retry 17/25 vs snapshot branching 6/25; branching helps only when state lives outside the repo; NOVEL). Excluded: 2609.38648 StateFork (gpt-4.1-mini), 2610.12086 EvoAlloc (Qwen3.6-35B-A3B), 2609.33875 CRR (14B training), 2610.09088 RippleCP (12-task pilot).

## What transfers

- **/loop + wakeup-cadence escalation.** MILO is measured support for the existing rule: a stall counter that triggers a structural change, not more of the same, was the biggest single component (+5.6 RR@5). AIDE² found the same thing on its own, but its unit is "fork the incumbent under a different strategy", not "restart". The concrete delta for `wakeup-cadence.md`: when `stale_count ≥2`, the frame change should keep the incumbent artifact and switch the strategy arm, not reset. MILO adds one more: retry from the weakest lineage, since grafting it produced the best result. Rejected mutations should stay as negative evidence (MILO lineage memory), which matches the append-only ledgers.
- **Parallel lanes in /loop and subagent fan-out.** 2609.40303 and 2610.10263 agree. At frontier capability, parallel sessions mostly raise the oracle ceiling, and the gain is lost unless selection is reliable; uncontrolled concurrency costs 1.4–3.3× tokens for roughly zero net resolution. Fan out only where a trusted verifier picks the winner, and log self-select vs oracle when we can (this is the sibling memo's "only where a trusted verifier selects" rule, with numbers).
- **eval skill.** Two protocol items to add. (1) Report the self-select vs oracle gap for any multi-candidate arm (2609.40303 makes it the binding loss). (2) Any "better search policy" claim needs a token-matched continuation control: MIRA's control recovered most of its gap. Several ranked papers (Mixture of Branches, SEDIMA, PrimeScientist n=1) fail one of these, so the eval checklist would catch them. Both items fit the existing token-cost rule.
- **doe skill.** Search-policy comparisons need paired-by-task CIs and 3+ seeds; 2609.40303's protocol (bootstrap over seeds within task, paired differences) is the template, and its null result for four policies shows that small policy effects are below typical noise.
- **brainstorm skill.** AIDE²'s strategy-arm bandit (conservative / aggressive_rewrite / ensemble / specialist / robust_simple) and MIRA's inertia metric are cheap diversity controls: label each idea with its strategy and measure how often consecutive steps stay in one direction. This is an untested transfer from optimization loops to ideation.
- **arc-agi.** Forking from restored states (ForkPilot RTS > BoN-5 on frontier models) fits ARC-AGI-3 games, where state is cheap to restore and progress is not in a diff. The Daytona negative says the gain depends on restore cost and on a signal for picking the state, which the existing graph-explorer work already handles. Ungraded locally (repo path not found), so check `arc-agi3-*` memory entries before acting.

## Per-paper detail

### Triage (turn ~8): candidates in window, model check by rg over full PDF text
Also excluded as sibling-covered in `2026-10-13-idea-basins-fork-flush-related-work.md`: 2606.22953, 2609.00077, 2608.13417, 2603.26499, 2608.19703 (Loreley), 2609.38445 (AIM), 2607.26587, 2610.13058 (ReTRAIL; also small-model RL).

| id | date | models (rg) | status |
|---|---|---|---|
| 2609.40303 harness-minimal MLE | 09-30 | GLM 5.2, Kimi K3, DeepSeek V4 Pro/Flash | read |
| 2610.10263 dynamic concurrency | 10-07 | Codex GPT-5.4, Claude Code Opus 5, Kimi K3 | read |
| 2610.04889 ForkPilot | 10-04 | GPT-5.6 Sol, Opus 4.8, Kimi K3 (+Qwen small) | read |
| 2609.26457 AIDE² | 09-22 | Gemini 3 Flash, GPT-5.6 Sol | read |
| 2609.38349 MILO | 09-29 | Opus 4.8, GPT-5.5, gpt-oss-120b | read |
| 2609.37834 Mixture of Self-Improving Branches | 09-29 | Sonnet 4.5, Opus 4.6, Gemini 3 Flash | read |
| 2609.38648 StateFork | 09-29 | (no model string found) | check |
| 2610.13841 Go-Explore Daytona snapshots | 10-09 | Claude Haiku only? | check |
| 2609.17846 PrimeScientist | 09-15 | GPT-5, GPT-5-mini | check |
| 2608.23848 ExTS | 08-24 | Qwen3-8B + Claude Sonnet 4.5/Opus 4.6? | check |
| 2609.01294 HypoSearch | 09-01 | Kimi K2.5, Qwen3.5-122B, DeepSeek V3.2 | check |
| 2610.02361 SEDIMA | 10-01 | Gemini 3 Pro, DeepSeek V4 Pro, GPT-5.4 | check (memory, borderline scope) |
| 2609.01481 Harness-of-Harness | 09-01 | GPT-5.5, DeepSeek V4 Pro, MiniMax M3 | check (loop design, borderline) |
| 2610.12086 EvoAlloc | 10-08 | Qwen3.6-35B-A3B | EXCLUDED (<70B) |
| 2610.09088 RippleCP | 10-06 | GPT-5.4 xhigh | pilot 12 tasks; checkpoint economics, abstract-level |
| 2609.33875 CRR | 09-27 | 14B policy training | EXCLUDED (<70B, training) |
| 2608.22191 Risa | 08-23 | open MoE (gpt-oss family) | EXCLUDED-ish (needs router traces; open-weight only) |


## Search record

- Memory/priors checked first: `evolutionary-autoresearch-2026-frontier.md` (researcher memory), sibling memo `2026-10-13-idea-basins-fork-flush-related-work.md` (its covered IDs excluded here: 2606.22953, 2609.00077, 2608.13417, 2603.26499, 2608.19703, 2609.38445, 2607.26587, 2610.13058, plus the dispatch's exclusion list).
- Exa `web_search_advanced` (arxiv.org, published 2026-08-13..2026-10-13), 6 queries: tree search over coding-agent trajectories; parallel vs sequential compute for SWE agents; evolutionary populations/plateau/restart; workspace snapshot forking/Go-Explore (no domain filter); DGM-successor populations; restart-vs-continue and depth/breadth. Results >100KB were saved to files and parsed with a jq-free python lister.
- arXiv API `id_list` for abstracts and `published` dates (2 batches, 25 ids); PDFs via arxiv.org/pdf + pdftotext for 17 papers; model check by regex over full text.
- Not done (turn cap): arXiv cs.AI/cs.LG/cs.SE listing-page sweep and `search_papers`; scite stance counts (no scite tool exposed in this session, so the literature-direction claims in the Verdict have no stance coverage); arc-agi local grading (repo path not found); Gödel Forest, ActiveSaddler, RAAC, HypoSearch, HoH read only at abstract level.
- Tool note: `rg` returned no output for every pattern in this shell, including patterns known to match; grep -r found them. Grades rely on the grep probe.
