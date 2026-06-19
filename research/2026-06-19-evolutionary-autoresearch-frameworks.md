---
title: Evolutionary Program-Search & Autoresearch Frameworks — 2026 SoTA for verifier-gated testgrounds
date: 2026-06-19
status: COMPLETE
axis: evolutionary program-search & autoresearch frameworks (AlphaEvolve lineage + 2026 successors)
testgrounds: hutter (lossless compression, bit-exact verifier), anim-workbench (animation evolver)
prior_coverage:
  - hutter/proposals-pending/2026-06-09-evolver-architecture-research.md (AlphaEvolve 2506.13131 read; FunSearch/ELM/DGM/LMX)
  - research/2026-04-02 AI-Scientist-v2 (2504.08066)
  - research/karpathy-autoresearch-*
scope_note: SKIP unless NEW version/result since ~May 2026. Already covered AI-Scientist v1/v2, DGM, Karpathy, AlphaEvolve base.
---

# Evolutionary Program-Search & Autoresearch — 2026 successors

Goal: steal mechanisms for verifier-gated LLM-mutator evolutionary loops (hutter compression, anim).

## Prior art baseline (from memory — do NOT re-research)
- **AlphaEvolve** (arXiv:2506.13131, DeepMind, read in full): diff-edits in EVOLVE-BLOCK fences; evaluator grounds the LLM (no model-as-judge); DB = MAP-Elites × island. asyncio = throughput not correctness → tolerates ~100hr/eval serial → single-machine-legal. Table 1: FunSearch millions-of-samples → AlphaEvolve thousands; jump bought by SOTA-LLM + rich multi-parent context + diffs.
- **FunSearch** (Nature): m-islands, wipe-worst-half every 4h reseed from survivor, signature-cluster, Boltzmann + favor-shorter.
- **ELM** (Lehman/Stanley): QD vs greedy MIXED evidence; "Objectives Are All You Need" (2311.02283) counterpoint.
- **DGM** (2505.22954, Clune): objective-hacking faked own benchmark = canonical self-judge-Goodhart proof.
- **LMX crossover** measured > single-parent (our record's mechanism).

## NEW findings (this pass) — appended incrementally below

### 1. ShinkaEvolve (Sakana AI) — arXiv:2509.19349, ICLR 2026 poster — THE headline steal
Repo: github.com/SakanaAI/ShinkaEvolve (~1K stars, Python, REAL — full `shinka/core/sampler.py`, async-evolution docs, circle-packing/AIME/ALE-bench/MoE examples). Sakana, R.T. Lange et al. Apache-licensed lineage. MATURE & runnable.

Headline result: **new SOTA circle-packing (26 circles, sum-radii 2.636) in ~150 evaluations vs AlphaEvolve's ~5,000+ → >30× more sample-efficient.** This is THE result for our slow-verifier testgrounds (hutter eval ≈ minutes-to-hours; sample efficiency is the binding constraint, not throughput).

NOVEL mechanisms (vs AlphaEvolve base, which we already have):
1. **Weighted parent sampling = performance × novelty** (NOVEL, highest-leverage). `w_i = s_i·h_i` where `s_i = σ(λ·(F−α₀))` (sigmoid-scaled fitness) and `h_i = 1/(1+N(P_i))` (N = #offspring already drawn from that parent → fewer-children parents favored). Alternative offered: power-law `p_i ∝ r_i^(−α)` (α=0 uniform, α→∞ hill-climb). Ablation: weighted sampling beats BOTH random search and hill-climbing. This replaces our current (1+1)/greedy parent pick with a tunable explore-exploit dial keyed on offspring-count.
2. **Embedding-based novelty rejection** (NOVEL, kills wasted slow evals — directly relevant to hutter). Two-stage: (a) embed mutable code block via `text-embedding-3-small`, cosine-sim across island; if max-sim > η=0.95, (b) LLM-as-novelty-judge "meaningfully different?" Ablation: embedding-stage gives SUBSTANTIAL gain; LLM-judge stage only marginal → for us, **the cheap embedding gate is the whole win; skip the LLM judge.** Reject near-dup BEFORE spending a multi-minute compression eval.
3. **UCB1 bandit over an LLM ensemble** (NOVEL). Each LLM = an arm; reward = `exp(max(r_i − r_i^baseline, 0)) − 1` (exp+max → rewards bold high-variance jumps; baseline = max(parent fitness, seed)). Ablation: bandit ensemble beats single-LLM AND fixed-ensemble. Models tested: GPT-4/Claude Sonnet/Gemini 2.5/o4-mini/DeepSeek. We have multi-model dispatch (llmx) → adopt UCB1 over {Opus, GPT-5.x, Gemini-flash} as mutators, reward = bit-savings improvement.
4. **Meta-scratchpad** (NOVEL, cheap). Every T generations, summarize the successful solutions into "actionable recommendations" appended to the mutation prompt — evolves the search GUIDANCE itself (not just the population). Trivial to bolt onto our diff-prompt; turns winning-edit patterns into in-context priors.
5. Mutation mix: diff-edits 45% / full-rewrite 45% / crossover 10% (per-task tunable); invalid proposals → auto-resample with Reflexion feedback. (Crossover = LMX, we already know it helps.)

Other results: AIME math-scaffold (75 gens, 3-expert peer-review, transfers to unseen 2023/2025), ALE-bench +2.3% (one task 5th→2nd), MoE load-balance loss (30 iters, new regularizer). Breadth of domains = strong evidence the harness generalizes.

### 2. BaSE — "Compute Allocation in Evolutionary Search: Depth–Breadth to Multi-Armed Bandits" — arXiv:2605.29268v2, **May 29 2026** (IN WINDOW)
Repo: github.com/keruiwu/self-evolving-allocation (Xing, He, Wu et al.). Directly answers the team-lead's budget-allocation question.

Thesis: fixed budget **C = T·N** (T=depth/generations, N=breadth/children-per-gen). Optimal split is TASK-DEPENDENT (Circle Packing favors depth; others balance) — so don't hard-code it, LEARN it online. "Capability ordering collapses on effective FLOPs" (compute is the real axis, echoing AlphaEvolve §2.6 / our single-machine note).
Mechanism: **BaSE (Bandit-based Self-Evolving).** Arms = parallel evolutionary TRAJECTORIES from the same seed; each pull = one LLM call extending that trajectory. Bandit decides which trajectory gets the next call. Three variants tried: **UCB, EXP3.P, Thompson Sampling** (Thompson wins).
Results (Qwen3-8B, C=512 calls; baselines Greedy/OpenEvolve/CodeEvolve/ShinkaEvolve):
- Heilbronn Triangle: Thompson 0.8736 vs Greedy 0.6780 = **+28.8%** (big when landscape is rugged)
- Circle Packing +0.18%, MinMaxDist +0.06% (small when depth-dominant)
- **Mean +12.3% over 8 model-task cells.** Threshold-reaching (MMD τ=0.95): **106 gens vs Greedy's 485 = 4.6× faster.**
Steal: cast depth-vs-breadth as a Thompson-sampling bandit over trajectories instead of a fixed island schedule. The payoff scales with landscape ruggedness — hutter's bit-exact landscape is plausibly rugged (many edits neutral, rare ones pay), so this is a genuine candidate, not a marginal tweak. NOTE on currency: run on Qwen3-8B (not frontier) — the MECHANISM transfers (bandit allocation is scale-independent), but absolute % gains may differ with a frontier mutator.

### 3. OpenEvolve — the mature open AlphaEvolve substrate (reference, not novel)
Repo: github.com/algorithmicsuperintelligence/openevolve — **6,549 stars, 1,046 forks, 117 open issues, active, has its own CLAUDE.md** (Python). This is the de-facto open-source AlphaEvolve reimplementation and the COMMON BASELINE that BaSE and AdaEvolve both benchmark against (their circle-packing / MinMaxDist / Heilbronn tasks come from OpenEvolve's example suite). MAP-Elites × island, diff-edits. NOT novel mechanism — it IS the AlphaEvolve design we already have — but it's the **most battle-tested reference codebase to read for implementation patterns** (config schema, evaluator harness, checkpointing) if we want a known-good scaffold rather than rolling our own. The fork (matt783, theahura) and 0-star clones are noise; the algorithmicsuperintelligence one is the real fork lineage. Maturity = high.

### 4. AdaEvolve — arXiv:2602.20133 (Feb 2026, Berkeley/Cemri et al.) — SLIGHTLY PRE-WINDOW, already referenced
"Adaptive LLM Driven Zeroth-Order Optimization." Multi-island adaptive search with **UCB-based island selection** (docs: skydiscover-ai mintlify). Same author cluster as EvoX (2602.23413) and overlaps GAE authors (Berkeley Sky lab). Frames LLM-evolve as zeroth-order optimization (no gradients, query-only). The UCB-island-selection idea is now SUBSUMED by the two stronger 2026 papers above: ShinkaEvolve's UCB1 is over MODELS (richer arm), BaSE's bandit is over TRAJECTORIES with a proper depth-breadth analysis. Verdict: AdaEvolve was the early-2026 UCB-on-islands step; ShinkaEvolve + BaSE are the matured successors. Don't re-mine AdaEvolve separately.

### 5. Frontier signal (May–Jun 2026, mechanism-novel but UNPROVEN / not yet stealable)
These name the right next bottlenecks but are abstract-only or workshop posters with NO numbers/repo yet — log as directions, do NOT cite as demonstrated:
- **GAE: Graph-Augmented Evolution** (OpenReview 9HAc5Yjf7L, ICML2026-AI4Science poster, 30 May 2026). Names the three bottlenecks precisely: *structurally blind parent selection, sparse whole-program rewards, static mutation operators*. Proposed fix = (a) relational GNN → typed-computation-graph program embeddings for STRUCTURE-AWARE parent selection, (b) RL meta-controller picks parent + mutation direction from reward history, (c) **online GRPO fine-tuning of the LLM mutator at test-time** on group-normalized fitness. Tested on symbolic regression for nonlinear oscillators. CAVEAT: abstract gives ZERO numbers, no repo, no named RL algorithm — unverified. The GRPO-test-time-finetune idea collides with our standing DGM self-judge-Goodhart caution (a learned mutator can drift toward reward-hacking the verifier) and requires open-weight + training infra we don't run for mutators. Watch, don't build.
- **PartEvo / "Partition to Evolve"** (NeurIPS 2025, niching-enhanced LES). Feature-assisted niche construction in abstract code space; beats EoH and FunSearch; up to +90.1% on resource-scheduling meta-heuristics. = a niching/QD refinement of the island idea (relatives of MAP-Elites). Maturity: published, but mechanism (niche construction in language space) overlaps ShinkaEvolve's novelty-rejection at lower leverage for us.
- **POISE** (OpenReview EPWdJDKSXx, ACL ARR Jun 2026): genealogically-linked archive (proposals↔code↔evals↔NL-reflections), 64 candidates, GRPO→ +4.6 overall / AIME25 pass@32 26.7→43.3%. = AI-Scientist-style RL-algorithm discovery; archive-with-reflections idea overlaps ShinkaEvolve meta-scratchpad.
- Verifier-design side (relevant to our bit-exact gate but a DIFFERENT axis — RLVR for code verifiers, not evolve frameworks): **Aletheia** (TMLR, 13 Jun 2026, "what makes RLVR for code verifiers tick"), **RobustTests** (ACL ARR, faulty-code-driven test synthesis + dense reward to stop reward-hacking from thin test coverage). Flag for the verifier-quality memo, not this one — our hutter verifier is bit-exact (no reward-hacking surface), so low relevance there; anim's verifier is softer and could care.

---

## RANKED STEAL LIST (leverage for hutter/anim verifier-gated, slow-eval search)

| Rank | Mechanism | Source | Why it wins HERE | Effort |
|---|---|---|---|---|
| 1 | **Embedding-based novelty rejection** (cosine on mutated block, η≈0.95, reject near-dups BEFORE eval) | ShinkaEvolve §; 2509.19349 | Our binding constraint is slow/expensive evals (compression run = min–hrs). Killing duplicate evals is pure throughput-for-free. Cheap embedding gate is the whole win (LLM-judge stage only marginal — skip it). | LOW |
| 2 | **Weighted parent sampling = fitness × 1/(1+offspring_count)** | ShinkaEvolve | Replaces our (1+1)/greedy pick with a tunable explore-exploit dial that auto-spreads draws off over-mined parents. Directly attacks "structurally blind parent selection." | LOW |
| 3 | **UCB1 bandit over LLM-mutator ensemble** (arm=model, reward=exp(max(Δfit,0))−1) | ShinkaEvolve | We already have multi-model dispatch (llmx: Opus/GPT-5.x/Gemini). Adaptively route mutation calls to whichever model is paying off on THIS problem; exp+max favors bold jumps (good for rugged compression landscape). | MED |
| 4 | **Thompson-sampling depth↔breadth allocation** (arm=trajectory, bandit picks who gets next call) | BaSE; 2605.29268 | Stops hard-coding island/generation schedule; payoff scales with ruggedness (+28.8% on rugged Heilbronn; 4.6× faster to threshold). Hutter landscape is plausibly rugged. | MED |
| 5 | **Meta-scratchpad** (every T gens, summarize winning edits → append to mutation prompt) | ShinkaEvolve | Turns the population's own success patterns into in-context priors for the mutator. Cheap; compounds. | LOW |

Deliberately NOT stealing: GAE's online-GRPO mutator fine-tune (unproven + collides with DGM self-judge-Goodhart caution + needs training infra); AdaEvolve UCB-islands (subsumed by #3/#4); niching/QD high-res grids (prior memo already cautioned QD payoff unproven at slow-eval/few-hundred-sample regime — our regime).

## Currency / reproducibility notes
- ShinkaEvolve: REAL repo (~1K★), ICLR 2026 poster, frontier-era models in ensemble (Claude Sonnet/GPT-4/Gemini 2.5/o4-mini). Most directly reproducible. HIGHEST confidence.
- BaSE: real repo (keruiwu/self-evolving-allocation), arXiv 29 May 2026 — IN WINDOW. Ran on Qwen3-8B (non-frontier) → mechanism transfers (bandit allocation is scale-independent) but absolute %s may differ with frontier mutator. Treat the +12.3%/4.6× as directional, re-measure on our stack.
- OpenEvolve: most mature codebase (6.5K★) = best reference scaffold; not novel.
- GAE/POISE/PartEvo: abstract-or-workshop-only, no/limited numbers → directional signals, NOT demonstrated results. Per team-lead's press-release-vs-result discipline: do not cite as evidence.


