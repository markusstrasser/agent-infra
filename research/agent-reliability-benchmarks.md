# Agent Reliability: Capability =/= Reliability — Now With Better Data

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**Princeton "Towards a Science of AI Agent Reliability" (Feb 2026)** [SOURCE: arXiv:2602.16666] — still the most rigorous study. Not superseded. No follow-up including Opus 4.6/GPT-5.3/Gemini 3.1 Pro yet.

Key findings unchanged:
1. **"Reliability gains lag noticeably behind capability progress."** r=0.02 over 18 months.
2. **Outcome consistency universally low.** Same task, same model, different runs = different outcomes.
3. **"What but not when" pattern.** Higher distributional than sequential consistency.
4. **Financial accuracy violations most prevalent failure mode.**
5. **Claude models showed stronger calibration.** But not uniformly across other reliability dimensions.
6. **Reasoning models "generally (but not consistently) more reliable."**
7. **Prompt sensitivity persists.**

**NEW — CLEAR Framework (arXiv:2511.14136):** Five-dimensional enterprise evaluation (Cost, Latency, Efficacy, Assurance, Reliability). **60% pass@1 drops to 25% over 8 consecutive runs.** Accuracy-only evaluation predicts production success at r=0.41; CLEAR predicts at r=0.83. Agents optimized for accuracy alone are 4.4-10.8x more expensive than cost-aware alternatives. [SOURCE: arXiv:2511.14136] [PREPRINT]

**NEW — FeatureBench (ICLR 2026, arXiv:2602.10975):** Benchmarks feature-level development (not bug-fixing). 200 tasks from 24 repos. Claude Opus 4.5 solves only **11.0%** (vs 74.4% on SWE-bench). GPT-5.1-Codex at 12.5%. Exposes that SWE-bench success is dominated by bug-fixing; feature development remains extremely hard for all models. [SOURCE: arXiv:2602.10975] [PUBLISHED ICLR 2026]

**NEW — "Debate or Vote" (arXiv:2508.17536, ACL 2025 Findings):** Multi-agent debate modeled as a martingale over belief trajectories — **debate alone does not improve expected correctness.** Majority voting alone accounts for most gains attributed to multi-agent debate. Voting protocols: +13.2% on reasoning tasks. Consensus protocols: +2.8% on knowledge tasks. [SOURCE: arXiv:2508.17536, ACL 2025] [PUBLISHED]

**NEW — International AI Safety Report 2026:** "Increasingly capable and reliable, though they remain prone to basic errors." "Less reliable when projects involve many steps." "Current techniques can reduce failure rates but not to the level required in many high-stakes settings." [SOURCE: internationalaisafetyreport.org/2026]

### SWE-bench State of the Art (Feb 2026, updated)

| Model | SWE-bench Verified | SWE-bench Pro | FeatureBench | SWE-EVO | Terminal-Bench 2.0 |
|---|---|---|---|---|---|
| Claude Opus 4.6 | ~80.8% | — | — | — | 65.4% |
| Claude Opus 4.5 | ~80.9% | 45.9% | 11.0% | — | 59.8% |
| GPT-5.3-Codex | — | 56.8% | — | — | 77.3% |
| GPT-5.2 | ~80.0% | — | — | — | — |
| GPT-4 + OpenHands | — | — | — | 21% | — |
| MiniMax M2.5 | 80.2% | — | — | — | — |
| Gemini 3.1 Pro | — | 54.2% | — | — | — |

Key observations:
- **Open-weight model (MiniMax M2.5) at SWE-bench parity** (80.2%). Frontier capability no longer requires frontier pricing. Changes the cost-reliability tradeoff for retry strategies. [SOURCE: Simon Willison, Feb 2026]
- **SWE-bench Verified is saturating.** Top 4 models within 0.9% of each other. SWE-bench Pro and FeatureBench show the real gaps.
- **Feature development is 6-7x harder than bug-fixing** for the same models on the same benchmark methodology. This is the gap that matters for production agents.

**NEW — Six Sigma Agent (arXiv:2601.22290, Jan 2026):** Mathematical proof for majority voting: n independent outputs with error rate p achieves system error O(p^ceil(n/2)). 5% error + 5 agents = 0.11% error. 13 agents = 3.4 DPMO (Six Sigma). Claims 14,700x reliability improvement, 80% cost reduction vs single expensive model. **Limitation:** Only validated on atomic decomposable tasks, not long-horizon sequential work. Provides the cost-normalized math for unknown #3 below. [SOURCE: arXiv:2601.22290] [PREPRINT]

**NEW — SWE-EVO (arXiv:2512.18470, Dec 2025, revised Jan 2026):** Benchmarks long-horizon software evolution: 48 tasks averaging 21 files, 874 tests. GPT-4 + OpenHands: 21% on SWE-EVO vs 65% on single-issue SWE-bench — another 3x drop on long-horizon tasks. Confirms FeatureBench finding that SWE-bench overstates real capability. Context management is the binding constraint for multi-file tasks. [SOURCE: arXiv:2512.18470] [PREPRINT]

**NEW — METR 50% Time Horizon (arXiv:2503.14499):** The task length an AI can complete at 50% reliability has been doubling every ~7 months (accelerating to ~4 months in 2024-2025). o3 at ~110 minutes, Claude 3.7 Sonnet at ~50 minutes. No data for Opus 4.6 yet. International AI Safety Report 2026 cites this as key evidence. [SOURCE: metr.org/time-horizons, arXiv:2503.14499]

**NEW — GDPval-AA (Artificial Analysis):** Economically valuable knowledge work across 44 occupations, 9 GDP sectors. Opus 4.6 at 1606 Elo, GPT-5.2 at 1462 (144 Elo gap ≈ 70% win rate), Gemini 3 Pro at 1195. [SOURCE: artificialanalysis.ai/evaluations/gdpval-aa] [BENCHMARK]

**NEW — APEX-Agents (Mercor):** Long-horizon cross-application tasks from investment banking, consulting, law. Gemini 3.1 Pro leads at 33.5%, nearly doubling prior best. [SOURCE: emergentmind.com/papers/2601.14242] [BENCHMARK]

### Primary-Source Case Studies

**Knuth "Claude's Cycles" (Feb 28, 2026)** [SOURCE: www-cs-faculty.stanford.edu/~knuth/papers/claude-cycles.pdf] — Opus 4.6 solved an open combinatorics problem (decomposing arcs of m³-vertex digraph into three directed Hamiltonian cycles for odd m). 31 self-directed explorations over ~1 hour. Strategy: reformulation → brute-force DFS → structural analysis (fiber decomposition) → simulated annealing → recognized SA can't generalize → pure construction. Knuth verified the proof, then extended the analysis (760 valid "Claude-like" decompositions exist).

Operational observations:
- Required human coaching throughout (Filip Stappers). Repeated reminders to document progress despite explicit instructions.
- Lost results on restarts — no persistent state across sessions.
- Degraded on harder subproblem (even m): "not even able to write and run explore programs correctly anymore."
- Solution correct for odd m, even case remains open.

**Relevance:** Strongest public primary-source evidence of Opus 4.6 creative problem-solving, from the most credible possible evaluator. But the problem had an automated verifier (cycle correctness is checkable programmatically) — consistent with the finding that agents excel on verifiable domains. Does not extrapolate to domains without ground truth.

### What's CLAIMED → PARTIALLY RESOLVED

- ~~Opus 4.6 and Gemini 3.1 Pro are too new for independent evaluation.~~ → Vendor benchmarks now available but still NO independent reliability evaluation (Princeton-style). SWE-bench Pro and Terminal-Bench 2.0 provide some independent data.
- ~~Long-horizon agent reliability beyond SWE-bench.~~ → FeatureBench (11%), APEX-Agents (33.5%), and Terminal-Bench 2.0 confirm: enterprise tasks are dramatically harder. SWE-bench was a floor, not a ceiling.

### Engineering implications for us

**NEW — majority voting works for correctness on reasoning tasks.** The Debate-or-Vote paper proves that multi-agent debate (models arguing toward consensus) is a martingale for correctness — voting captures most gains. This validates retry logic and majority-vote architectures for deterministic tasks. NOTE: This does NOT apply to multi-model review for adversarial pressure or creative divergence (different models finding different flaws or offering different approaches). Opus-as-judge-with-context is classification, not debate. Getting alternative perspectives from Gemini/GPT is creative divergence, not consensus-seeking.

**NEW — cost-normalized retry with cheaper models.** MiniMax M2.5 at SWE-bench parity opens the strategy: cheap model + many retries + majority vote may beat expensive model + single shot. Not yet tested systematically, but the economics shifted.

<!-- knowledge-index
generated: 2026-03-21T23:52:34Z
hash: 0f13469584e3


end-knowledge-index -->
