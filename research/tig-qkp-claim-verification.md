---
title: TIG QKP Claim Verification
date: 2026-03-25
---

## TIG QKP Claim Verification — Research Memo

**Question:** Verify the claim: "For the Quadratic Knapsack Problem, 476 iterative submissions by independent contributors brought solution quality to a level that now exceeds methods published by Hochbaum et al. in the European Journal of Operational Research (2025)." Also verify the referenced No Priors podcast conversation with Andrej Karpathy.

**Tier:** Standard | **Date:** 2026-03-25
**Ground truth:** No prior research on TIG or QKP in the researcher corpus.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Hochbaum et al. published a QKP paper in EJOR 2025 | Full paper read (arXiv version); EJOR Vol. 323, Issue 2, pp. 425-440 | HIGH | [DOI: 10.1016/j.ejor.2024.12.019](https://doi.org/10.1016/j.ejor.2024.12.019), [arXiv: 2408.12183](https://arxiv.org/abs/2408.12183) | VERIFIED |
| 2 | TIG's crowd-sourced approach exceeds Hochbaum's QKBP method | TIG's own blog post (July 2025) claims this; RockawayX (investor) echoes. TIG claims superiority on "most benchmarks" and faster runtimes. Independent verification absent. | MEDIUM | [Medium blog](https://medium.com/@tigfoundation/an-advancement-in-algorithmic-innovation-tig-surpasses-established-state-of-the-art-methods-in-the-c13ef52eb606), [RockawayX](https://www.rockawayx.com/insights/the-innovation-game-surpasses-sota-quadratic-knapsack-problem) | SELF-REPORTED, UNVERIFIED BY THIRD PARTY |
| 3 | 476 iterative submissions by independent contributors | Not directly confirmed. Main branch has ~22 knapsack algorithms visible. Total monorepo has ~971 commits across all challenges. TIG's submission model uses rounds with merge-point mechanics; many submissions are iterative versions that supersede predecessors. 476 is plausible as cumulative submissions across rounds but unverifiable from public repo state. | LOW | [GitHub: tig-monorepo](https://github.com/tig-foundation/tig-monorepo), TIG docs | UNVERIFIED — PLAUSIBLE BUT NOT CONFIRMABLE |
| 4 | Andrej Karpathy discussed autoresearch on No Priors podcast | Published March 20, 2026. Episode title: "Andrej Karpathy on Code Agents, AutoResearch, and the Loopy Era of AI." Host: Sarah Guo. | HIGH | [YouTube](https://www.youtube.com/watch?v=kwSVtQ7dziU), [Podscan](https://podscan.fm/podcasts/no-priors-artificial-intelligence-technology-startups/episodes/andrej-karpathy-on-code-agents-autoresearch-and-the-loopy-era-of-ai) | VERIFIED |

---

### Key Findings

#### 1. Hochbaum et al. EJOR 2025 Paper — VERIFIED

The paper is real. Full citation:

> Hochbaum, D. S., Baumann, P., Goldschmidt, O., & Zhang, Y. (2025). "A fast and effective breakpoints heuristic algorithm for the quadratic knapsack problem." *European Journal of Operational Research*, 323(2), 425-440.

The paper (arXiv preprint: August 2024, published in EJOR 2025) introduces **QKBP** (Quadratic Knapsack BreakPoints), a heuristic based on the breakpoints algorithm previously used for maximum diversity and maximum dispersion problems. Key claims from the paper:
- Provides optimal or near-optimal solutions across a wide range of benchmark instances
- Achieves "several orders of magnitude speedups" compared to prior SOTA methods
- Authors: Hochbaum (UC Berkeley IEOR), Baumann (University of Bern), Goldschmidt (Riverside County Office of Education), Zhang (UC Berkeley)
- 6 citations on Semantic Scholar as of March 2025

[SOURCE: arXiv:2408.12183, DOI: 10.1016/j.ejor.2024.12.019]

#### 2. TIG's SOTA Claims — PARTIALLY VERIFIED (Self-Reported)

TIG Foundation published a blog post in July 2025 claiming their top-performing knapsack algorithm "rivals and, in some respects, surpasses" established SOTA methods. Their specific comparative claims:

- **Competes with:** GRASP+Tabu (Yang et al., 2013), IHEA (Chen & Hao, 2017) — these are well-known QKP metaheuristics
- **Outperforms:** DP+FE (Fomeni & Letchford, 2014) and **QKBP (Hochbaum et al., 2025)** "on most benchmarks"
- **Key advantage claimed:** Comparable solution quality at "orders of magnitude faster runtimes"

**Critical caveat:** This is entirely self-reported by TIG Foundation and echoed by RockawayX, which is an investor in TIG. No independent academic benchmarking or peer review confirms these claims. The comparison methodology, benchmark instances used, and what "most benchmarks" means specifically are not disclosed in the blog post. The claim about "exceeding" Hochbaum is more nuanced in TIG's own writing than in the claim being verified — TIG says "outperforming ... QKBP on most benchmarks" which is not the same as universally exceeding.

[SOURCE: medium.com/@tigfoundation, rockawayx.com — both are TIG stakeholders]

#### 3. The "476 Submissions" Claim — PLAUSIBLE BUT UNVERIFIABLE

The TIG monorepo's `main` branch currently shows:
- **22 knapsack algorithms** (excluding template files and mod.rs)
- **124 total algorithm files** across 7 challenges (knapsack, satisfiability, vehicle routing, vector search, hypergraph, neuralnet optimizer, job scheduling)
- **~971 total commits** in the monorepo

The discrepancy between "476 submissions" and "22 visible algorithms" is explained by TIG's protocol mechanics:
1. **Submissions are iterative with versioning** — the commit log shows patterns like `near_knap`, `near_knap_improve_v1`, and various `v2`, `v3` suffixes
2. **Merge-point mechanics** — only algorithms achieving sufficient Benchmarker adoption (25% for code submissions) earn merge points; only the top submission per round gets merged to main
3. **Superseded algorithms are removed** — the main branch is a live snapshot, not a historical archive
4. **Private branches** — submissions go to private branches first, then public after a 2-round delay

So 476 cumulative submissions across all rounds since Round 44 (when QKP was introduced) is architecturally plausible — each round could have multiple competing submissions, most of which are eventually superseded. However, this number is not independently verifiable from the public GitHub state. It may come from TIG's internal submission tracking.

**The claim that these are "independent contributors" deserves scrutiny.** The GitHub repo shows only 7 contributors, and the commit log shows many submissions from a small number of player addresses (e.g., `0x3ce59606...` and `0x1884f0fe...` appear repeatedly). TIG's model explicitly encourages iterating on others' work, so "independent" may be misleading — it's more accurately described as an open, iterative, incentive-driven process with a small number of active participants building on each other.

[SOURCE: GitHub API, TIG docs]

#### 4. No Priors Podcast — VERIFIED

The episode exists and is real:
- **Title:** "Andrej Karpathy on Code Agents, AutoResearch, and the Loopy Era of AI"
- **Published:** March 20, 2026
- **Host:** Sarah Guo (Conviction)
- **Topics:** AutoResearch, code agents, multi-agent orchestration, home automation ("Dobby"), open-source models, robotics, education
- **Key quote context:** Karpathy discusses running multiple parallel agents, AutoResearch (recursive self-improvement loops for LLMs), and the "AI psychosis" of spending 16 hours/day directing agents

The reference to "your No Priors conversation" in the claim being verified would be addressing Karpathy directly, which makes sense if the claim originates from someone communicating with or about Karpathy post-episode.

[SOURCE: YouTube, Podscan.fm, PodScripts.co, StocksFoundry]

#### 5. QKP State-of-the-Art Context

For proper context on TIG's claims, here is the QKP research landscape as of 2025:

**Leading methods (academic literature):**
- **IHEA** (Chen & Hao, 2017): Iterated hyperplane exploration — considered among the best metaheuristic approaches
- **GRASP+Tabu** (Yang et al., 2013): Greedy randomized adaptive search + tabu search
- **DP+FE** (Fomeni & Letchford, 2014): Dynamic programming with fix-and-enumerate
- **QKBP** (Hochbaum et al., 2025): Breakpoints heuristic — the newest entry, emphasizing speed
- **BDD-based bounds** (Fennich, Coelho & Fomeni, 2025): Binary decision diagrams for tight bounds
- **Deep RL framework** (Huang et al., 2025): Emerging neural approach, no benchmark comparisons yet
- **Ising machine approaches** (Ohno et al., 2024; Akishima et al., 2025): Hardware-oriented methods

QKP is NP-hard with no known polynomial-time algorithms. For large instances (n > 200-400), heuristics dominate. The field is active with multiple 2024-2025 publications in EJOR, COR, and IEEE. A survey paper by Galli, Martello & Toth (EJOR 2025) reviews the full landscape.

**TIG's approach is fundamentally different** from academic publication: it's crowd-sourced iterative optimization under competitive economic incentives, not a single paper proposing a novel method. Comparing the two is like comparing a Kaggle leaderboard to a published algorithm — the Kaggle winner may score higher on the specific benchmark, but the published method has theoretical guarantees, reproducibility, and generalizability that ensemble-of-tweaks approaches typically lack.

[SOURCE: Semantic Scholar search results, arXiv, EJOR]

---

### What's Uncertain

1. **Independent verification of TIG's benchmarking claims** — No third-party has replicated TIG's comparison. The blog post doesn't specify which benchmark instances, instance sizes, or exact RPD values. Dr. Philipp Baumann (co-author on Hochbaum paper) is listed as TIG's Quadratic Knapsack challenge technical paper author, which creates an interesting connection but doesn't constitute independent verification.

2. **The "476" number** — Cannot be confirmed or denied from public data. TIG's submission system operates through on-chain rounds with private branches; the number may be accurate from their internal records but is not auditable.

3. **"Independent contributors"** — The visible contributor base is small (7 GitHub contributors, a handful of player addresses in commits). The incentive structure encourages iteration on existing submissions rather than truly independent development. Whether this constitutes "independent contributors" depends on definition.

4. **Generalizability of TIG's algorithms** — TIG optimizes for specific benchmark configurations used in their proof-of-work rounds. Whether their algorithms generalize to arbitrary QKP instances (different sizes, density patterns, weight distributions) is unknown. Academic methods are typically tested across diverse benchmark suites.

5. **Exact relationship between Hochbaum team and TIG** — Baumann appears on both the Hochbaum paper and TIG's challenge design. This could mean TIG has academic input on their challenge design (positive for rigor) but also means the comparison is not fully arms-length.

---

### Verdict

The claim is **partially true with significant caveats:**

- **True:** Hochbaum et al. published a QKP paper (QKBP) in EJOR 2025 -- verified.
- **True:** The No Priors/Karpathy podcast episode exists -- verified (March 20, 2026).
- **Partially true / self-reported:** TIG claims to outperform QKBP "on most benchmarks" -- this is TIG's own assessment, echoed only by their investor. No independent verification exists.
- **Unverifiable:** The "476 submissions" figure -- architecturally plausible given TIG's round-based submission model, but not confirmable from public data. The main branch shows ~22 knapsack algorithms.
- **Misleading:** "Independent contributors" -- the contributor base appears small and highly iterative. The model is closer to a small group of participants incrementally improving each other's code under economic incentives than hundreds of independent researchers.

The claim reads as promotional material that takes TIG's self-reported benchmarks at face value while using the specific number "476" and "independent contributors" to imply broader participation than is publicly evidenced.

<!-- knowledge-index
generated: 2026-03-26T05:08:47Z
hash: 8b9e0dadcb57

title: TIG QKP Claim Verification
table_claims: 4

end-knowledge-index -->
