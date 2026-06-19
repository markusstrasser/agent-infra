---
title: "RSI & Self-Evolving Agents — arXiv SoTA Delta (vs known set)"
date: 2026-06-19
axis: "arXiv papers on recursive self-improvement & self-evolving agents — the DELTA"
known_set: [DGM, AutoAgent, DSPy, GEPA, Hermes, Karpathy-autoresearch, AI-Scientist-v1/v2, AdaEvolve]
status: COMPLETE
---

# RSI & Self-Evolving Agents — arXiv SoTA Delta

Goal: find NEW (May–June 2026, last ~6-8 weeks) arXiv work to steal from for
(a) harness-level RSI loop, (b) verifier-gated program-search testgrounds, (c) eval/fitness design.
SKIP known set above unless genuinely new version/result since ~May 2026.

For each: arXiv id + date · 1-line claim · leverage (a/b/c + how) · verified-vs-asserted · code?

---

## Epoch-2 (handed-off ID verification + safety/bounds axis routed around S2)

### Handed-off IDs — VERIFIED
- **EFC = "Scaling Laws for Agent Harnesses via Effective Feedback Compute"** — arXiv:2605.29682 (May 28 2026). VERIFIED from abstract. Claim: raw tokens & tool-calls explain LIMITED variation in agent FAILURE RATES (R²=0.33 / 0.42); their "Oracle-EFC" and "Estimated-EFC" coordinates reach **R²=0.94**. Law relates FEEDBACK QUALITY (operationalized = informative, valid, non-redundant, retained) → failure rate. Base model NOT named in abstract (frontier status unverified). Code: not mentioned. LEVERAGE = (a)+(c), HIGH: quantitative spine for our premise that *quality of human corrections* (not volume) gates self-improvement — gives 4 named quality axes (informative/valid/non-redundant/retained) to score corrections against + a measurable target (predict failure-rate). Strongest epoch-2 find.
- **SIA = "Self Improving AI with Harness & Weight Updates"** — arXiv:2605.27276 (May 26 2026, rev May 28). VERIFIED. Claim: ONE agent simultaneously updates BOTH another agent's harness/scaffold (prompts/tools/logic) AND its model WEIGHTS — vs optimizing levers separately; gains across 3 domains. Base model unnamed; code not indicated. Keywords: Self-Improving Agents, Test-Time Training, RL, Harness Engineering. LEVERAGE = (a), MEDIUM: harness+weights JOINT-update is beyond our harness-only loop (we don't train weights) — ceiling/direction note, not directly portable.
- **RHO** — wenbo.io lead resolves to TWO different things; disambiguated:
  - arXiv:2606.16458 **"RHO: Your Coding Agent is Secretly a Roboticist"** (Berkeley Embodied Science + AMD; Svegliato, Seshia, Zaharia). Literal "RHO" acronym but coding-agent→robotics-control, NOT RSI-core. Low leverage.
  - **wenbo.io = Wenbo Pan**, whose on-axis paper is **"Evolving Agents in the Dark: Retrospective Harness Optimization via Self-Preference"** — arXiv:2606.05922 (Jun 2026, CityU HK). RSI-relevant: retrospective harness optimization via SELF-PREFERENCE (no external verifier — "in the dark"). LEVERAGE = (a)+(c): self-preference as improvement signal is exactly the risk our verifier-gating guards (LLM-judges-own-output = Trapped-Priors/semantic-laundering) — read as the CAUTIONARY failure mode to gate.

### Bonus harness-RSI hits surfaced en route (Exa)
- **Self-Harness: "Harnesses That Improve Themselves"** — arXiv:2606.09498 (Jun 2026, Shanghai AI Lab). On-axis (a). Epoch-3 candidate.
- **Meta-Harness: End-to-End Opt** — surfaced (one of A2H's 5 named baselines); confirms "auto-harness" sub-field is crowded as of Jun 2026.

### Safety / verification-BOUNDS axis (routed via Exa + OpenAlex, NOT S2)
- **"On the Limits of Self-Improving in LLMs: The Singularity Is Not Near Without Symbolic Model Synthesis"** — arXiv:2601.05280 (Jan 5 2026). Claim (ASSERTED, title-level — body not full-read): pure-LLM self-improvement is BOUNDED; unbounded RSI needs symbolic model synthesis. Frontier-era. LEVERAGE = (a)+(b): theoretical ceiling argument supporting our verifier-gated *program-search* (symbolic/executable) grounds over pure prompt-self-edit loops. Borderline frontier; verify body before citing.
- **"Exploration Hacking: Can LLMs Learn to Resist RL Training?"** — arXiv:2604.28182 (Apr 30 2026). Reward-hacking / training-resistance face of self-improvement safety. LEVERAGE = (a)+(c): the reward-hacking risk our eval/fitness must be robust to. Frontier. Note only.
- OpenAlex backend returned mostly alignment-ETHICS (Rewarded Soups, pluralistic-alignment, "ethical evolution") — NOT RSI-convergence theory. The two arXiv hits above (via Exa) are the real bounds coverage; OpenAlex low-yield here.

### Epoch-2 honest caveats
EFC + SIA verified from abstracts only (no full PDF, no code confirmation). The two bounds papers are title/preview-level, NOT body-verified. "Singularity Is Not Near" is Jan-2026 = borderline frontier. All three handed-off IDs now resolved (EFC, SIA confirmed; RHO disambiguated into 2 papers).

---

## RANKED SYNTHESIS (top NEW findings by leverage; known set confirmed absent below)

**Top 3 to steal from (all May–Jun 2026, code released, body-verified):**

1. **Adaptive Auto-Harness / A2H — arXiv:2606.01770 (Jun 2026)** — for (a) harness RSI.
   Steal the **harness-TREE-with-solve-time-routing** insight: a single densely-updated harness
   goes brittle and degrades — exactly the failure mode our monotonic blindspot→act-drain
   accretion risks. A2H keeps a tree and routes per-task. Also ships **human-steering hooks for
   when history lacks signal** = formal validation of our human-gated `questions`/HUMAN.md
   escalation. Code: A-EVO-Lab/a-evolve. CAVEAT: "beats 5 baselines" is ASSERTED — no magnitude
   numbers in abstract; verify the PDF before citing a win. Same lab as the A-Evolve baseline.

2. **FAMOU (co-evolutionary strategy evolution) — arXiv:2606.10389 (Jun 2026)** — for (b)+(c).
   Cleanest NEW treatment of **non-stationary fitness**: as your agent improves, a fixed verifier
   goes stale. Three portable mechanisms: (i) evaluator co-evolution (champions re-enter the
   opponent pool), (ii) hierarchical deep eval (statistically-sound vs noisy-short — our
   noisy-verifier→more-samples problem), (iii) weakness-pressure (active hard-case mining).
   VERIFIED numbers: 0.526 combined / 61.7% unseen-opponent win / 1st-place AAMAS-2026 MCTF.
   Code: 1xiangliu1/FAMOU-CoEvo. Directly relevant to our behavioral-eval (fixed corrections →
   the eval bar should RISE as the harness learns them) and to hutter/anim moving-bar grounds.

3. **AutoLibra — arXiv:2505.02820 (May 2025)** — for (c) behavioral-eval. Induces eval METRICS
   directly from open-ended human feedback ("if you see X do Y") and rewards intermediate
   emergent behaviors that task-success misses. This IS our pipeline's missing half: we turn
   session-corrections into eval *cases*; AutoLibra turns the same signal into reusable *metrics*.
   CAVEAT: May-2025 = borderline frontier; method (metric-induction) is largely scale-independent
   so it transfers, but re-measure any rates. Only 1 cite.

**Second tier (note, don't prioritize):**
- Synthesizing Multi-Agent Harnesses for Vuln Discovery (2604.20801) — harness-as-synthesis-target + clear exploit verifier; (a)+(b).
- Audited Skill-Graph Self-Improvement (2512.23760, Dec 2025) — verifiable-reward + audited skill graph; likely a Hermes-line extension (known cluster) — verify novelty.
- EvoFSM (2601.09465) — bounded/controllable self-rewrite via FSM; relevant to gating WHERE rewrite happens.
- Latent Heuristic Search (2605.17137) — continuous (not discrete-syntax) search space for program-search grounds.
- Alpha-mining cluster (Hubble 2604.09601, FactorEngine 2603.16365) — "unconstrained program-gen is unsafe → auditable/safe generation" design pattern for verifier-gating.

**Known-set confirmed (NOT a delta):** DGM 2505.22954, ADAS 2408.08435, Gödel Agent 2410.04444,
Symbolic-Learning 2406.18532 all surfaced where expected — the delta above is genuinely new work.

**Coverage gaps / honest caveats:** RSI *safety/verification-bounds* search returned EMPTY twice
(S2 403-throttling on longer queries — known gotcha) — that sub-axis is UNDER-COVERED here, not
proven empty. Self-rewarding/self-play-for-improvement surfaced mostly multi-agent-architecture
variants, not single-harness RSI. No paper bodies beyond A2H + FAMOU were full-text verified;
all "results" for second-tier items are abstract-level (ASSERTED).

---


---

## Findings (appended incrementally)

### Search 1 raw hits (S2 "self-evolving LLM agents optimize own prompts/tools/scaffold")
- **Adaptive Auto-Harness (A2H)** — arXiv:2606.01770 (Jun 2026, 0 cites). Explicitly names A-Evolve, GEPA, Meta-Harness as priors; their gap = those are eval'd on FIXED offline benchmarks, A2H targets OPEN-ENDED TASK STREAMS (sustained self-improvement at deployment). DIRECTLY (a) harness RSI — this is our exact problem (open-ended stream, not fixed bench). HIGH PRIORITY — read body.
- **AutoLibra** — arXiv:2505.02820 (May 2025, 1 cite). Induces agent eval METRICS from open-ended human feedback ("if you find X, do Y"); rewards intermediate emergent behaviors task-success misses. DIRECTLY (c) behavioral-eval — we turn human session-corrections into eval cases; this is metric-induction from the same signal. HIGH PRIORITY.
- **MAS² (Self-Generative/Configuring/Rectifying MAS)** — arXiv:2509.24323 (Sep 2025, 2 cites). Multi-agent system that self-generates/configures/rectifies. (a) but multi-agent flavor.
- **EvoFSM** — arXiv:2601.09465 (Jan 2026, 1 cite). Controllable self-evolution for deep-research via finite-state-machines (constrains where rewrite happens). (a) — the "controllable/bounded rewrite" angle is relevant to our gated loop.
- **CyberEvolver** — arXiv:2605.26195 (May 2026, 0 cites). Self-evolving cybersecurity agent, on-the-fly scaffold revision. (a) domain-specific; verifier = exploit success (clear verifier testground analog).
- **Learn Like Humans / meta-cognitive reflection** — arXiv:2601.11974 (Jan 2026, 0 cites). Claims existing self-improving frameworks use inefficient multi-turn recursive loops w/ high cost; proposes meta-cognitive reflection for cheaper self-improvement. (a) cost-of-loop angle.
- **Gödel Agent** — arXiv:2410.04444 (Oct 2024, 19 cites). Self-referential RSI framework, searches whole agent design space. PRE-FRONTIER (Oct 2024) — validity uncertain; likely subsumed by DGM (known set). Note only.
- **Symbolic Learning Enables Self-Evolving Agents** — arXiv:2406.18532 (Jun 2024, 87 cites). PRE-FRONTIER. Note only (foundational, well-cited, but old).
- bioRxiv/medRxiv preprint search EMPTY (expected — CS/arXiv axis, not bio).

### Search 2 (RSI safety/verification bounds) — S2 returned EMPTY. Retry via different terms later if budget.

### Search 3 raw hits (verifier-gated evolutionary program search — testground (b))
- **Co-Evolutionary Mechanisms for LLM-Driven Strategy Evolution in Adversarial Games** — arXiv:2606.10389 (Jun 2026, 0 cites). KEY problem: in LLM code-evolution for adversarial games the EVALUATION LANDSCAPE SHIFTS as strategies improve → fixed eval breaks (Red-Queen). Proposes co-evolutionary eval. DIRECTLY (b)+(c) — our testgrounds have a moving bar; this is the "fitness is non-stationary" problem head-on. HIGH PRIORITY — read body.
- **Synthesizing Multi-Agent Harnesses for Vulnerability Discovery** — arXiv:2604.20801 (Apr 2026, 2 cites). LLM agents auto-SYNTHESIZE the harness (the program wiring multiple agents) for vuln discovery; verifier = real exploit. (a)+(b) — harness-as-search-target + clear verifier testground. Relevant.
- **Latent Heuristic Search** — arXiv:2605.17137 (May 2026, 0 cites). Searches CONTINUOUS latent space instead of discrete program syntax for automated algorithm design (vs FunSearch/AlphaEvolve discrete sampling). (b) — alternative search-space mechanism for our program-search grounds.
- **Hubble (alpha factor discovery)** — arXiv:2604.09601 (Apr 2026, 1 cite). Agentic factor mining; explicitly frames "unconstrained program generation is operationally unsafe" → safe/diverse/reproducible. (b) verifier-gating + safety-of-generation design pattern.
- **FactorEngine** — arXiv:2603.16365 (Mar 2026, 0 cites). Program-level knowledge-infused factor mining; "executable + auditable + tractable at scale" requirement. (b) auditable-program-search design.
- **Cognitive Alpha Mining** — arXiv:2511.18850 (Nov 2025, 3 cites). LLM code-based evolution for alphas. (b) — note, slightly older.
- **PyVRP+ (metacognitive heuristic evolution)** — arXiv:2604.07872 (Apr 2026, 1 cite). LLM metacognitive heuristic evolution for VRP hybrid genetic search. (b) domain-specific.
- LLM-FE 2503.14434, Search-Based LLMs for Code Opt 2408.12159, MM-EvoSearch 2508.05433 — pre-frontier/older, note only.

### A2H body detail (arXiv:2606.01770) — VERIFIED from abstract+page
- Optimizes: prompts, skills, tools, memories, AND supporting infrastructure (full harness).
- MECHANISM = **"harness tree with solve-time routing"** — instead of ONE densely-updated harness (which goes brittle / degrades), maintains a TREE of harnesses and routes per-task at solve time. This is the key delta vs GEPA/A-Evolve/Meta-Harness (single monotonically-updated artifact).
- Non-stationarity: explicitly handles "histories grow without fixed endpoint, heterogeneous tasks need different harnesses, distributions shift over time."
- **"human-steering hooks for cases where history lacks the needed signal"** — built-in human-in-loop escalation when the self-improvement signal is absent. MAPS to our human-gated `questions`/act-drain + HUMAN.md escalation pattern.
- Results: "outperforms five existing auto-harness baselines" on prediction-market / security-competition / event-forecasting STREAMS. NO concrete numbers in abstract (ASSERTED, magnitude unverified — read full PDF to verify).
- Code: YES — github A-EVO-Lab/a-evolve (note: SAME repo as A-Evolve baseline; A2H appears to be from the A-Evolve lab itself).

### FAMOU body detail (arXiv:2606.10389) — VERIFIED from page, concrete numbers
Paper name = FAMOU. Three named co-evolutionary mechanisms to keep fitness meaningful as agents improve:
1. **Evaluator co-evolution** — discovered champions get added back into the OPPONENT POOL (the baseline you're scored against literally evolves with you).
2. **Hierarchical deep evaluation** — replaces noisy short evals with statistically-sound assessments (= our "noisy verifier → more samples" problem; they formalize it).
3. **Weakness pressure** — dynamically prioritizes the hardest opponents to break plateaus (= active-hard-case mining).
- Progress vs moving baseline = **opponent-pool rotation** (fitness measured against evolving champion set, not fixed ELO).
- Numbers (VERIFIED): combined score 0.526 (best vs baselines); 61.7% win-rate generalization to UNSEEN opponents; 1st place hardware round-robin / 3rd simulation at AAMAS 2026 MCTF competition.
- Code: YES — github 1xiangliu1/FAMOU-CoEvo.
- LEVERAGE: this is the cleanest treatment of NON-STATIONARY FITNESS for our verifier-gated testgrounds (hutter/anim-workbench) AND for the behavioral-eval (corrections get fixed → the eval bar should rise, not stay static). Mechanisms 1+3 are directly portable.

### Search 5 raw (meta-agent search / self-rewarding) — mostly KNOWN SET or multi-agent variants
- ADAS 2408.08435 (Hu/Lu/Clune, 215 cites) + DGM 2505.22954 (121 cites) + Gödel Agent 2410.04444 = KNOWN SET / pre-frontier. Skip.
- AutoMaAS 2510.02669, SwarmAgentic 2506.15672, MAS-ZERO 2505.14996, AgenticRS 2603.26085 — multi-agent ARCHITECTURE search; tangential to single-harness RSI. Note only.
- **RuleSmith** — arXiv:2602.06232 (Feb 2026, 1 cite). Multi-agent LLM auto game-BALANCING (couples game engine + multi-agent reasoning + iterative tuning). (c) — closest analog to anim-workbench-as-testground where the "rules" are tuned against an engine verifier. Minor note.

### Search 4 hit (test-time/continual self-improvement)
- **Audited Skill-Graph Self-Improvement for Agentic LLMs** — arXiv:2512.23760 (Dec 2025, 3 cites; Ken Huang & Jerry Huang — same author cluster as Hermes/skill-graph work in our known set). Combines verifiable rewards + experience synthesis + continual memory + an AUDITED skill graph under partial observability/long horizons. (a)+(c) — the "audited" + "verifiable reward" framing is close to our corpus-attestation + verifier-gated philosophy. Dec 2025 = borderline frontier. Worth a note; likely an extension of the Hermes line we already have — verify novelty vs known set before over-weighting.

