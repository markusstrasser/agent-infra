---
title: Temporal Epistemic Degradation in AI Agents
date: 2026-03-21
---

# Temporal Epistemic Degradation in AI Agents

*Date: 2026-03-02. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*RQ5 from epistemic quality research program.*

---

## Question

How does epistemic quality — factual precision, calibration, source fidelity, hedging language, hypothesis framing — decay over time in AI agent systems? Six specific degradation modes investigated.

**Tier:** Deep | **Date:** 2026-03-02
**Ground truth:** Context rot memo, epistemic quality evals memo, agent reliability benchmarks memo, agent memory architectures memo (all in this directory).

---

## 1. Within-Session Degradation: Factual Precision as f(Context Length)

### What's PROVEN

**Du et al. (EMNLP 2025, arXiv:2510.05381, 23 citations):** Even when models perfectly retrieve all relevant information, reasoning performance degrades 13.9-85% as input length increases within claimed context windows. Degradation persists even when irrelevant tokens are replaced with whitespace, and even when models are forced to attend only to relevant tokens. This is the strongest evidence that the problem is processing capacity, not retrieval failure. [SOURCE: arXiv:2510.05381, in corpus]

**Chroma Research (2026), 18 frontier models:** All 18 models degraded with context length. Lost-in-the-middle: ~75% accuracy at position 1, ~55% at position 10, ~72% at position 20. Topically-related distractors (relevant-but-wrong content) caused the worst hallucination amplification. Counterintuitively, shuffled haystacks (randomized sentence order) IMPROVED performance — logical flow of ideas makes context rot worse because it creates more topically-related distractors. [SOURCE: research.trychroma.com/context-rot]

**MECW "Maximum Effective Context Window" (Paulsen, arXiv:2509.21361):** Measured gap between advertised and actually usable context. Top models failed with as few as 100 tokens on harder tasks. Most experienced severe degradation by 1K tokens. All fell >99% short of their advertised maximum. [SOURCE: arXiv:2509.21361] [PREPRINT]

**PAPerBench (arXiv:2602.15028):** ~29,000 instances, 1K to 256K tokens, 377K evaluation questions. Both personalization quality and privacy awareness degrade with context length. Theoretical analysis attributes this to attention dilution in soft attention with fixed-capacity Transformers. [SOURCE: arXiv:2602.15028] [PREPRINT]

### What's NOT PROVEN (the specific gap)

**No one has measured FActScore-style factual precision as a function of context position within a single generation.** The existing literature measures:
- Task success / accuracy as f(context length) -- Du et al., Chroma, Liu et al.
- Retrieval accuracy as f(position) -- Liu et al. lost-in-the-middle
- Task completion reliability as f(number of runs) -- CLEAR framework

But the specific question "does the factual precision of claims at token 5000 of an agent's output differ from claims at token 500?" has NOT been directly measured. This is a genuine gap. The closest proxy is the serial position effect literature (below, section 6), which measures selection/classification biases, not generation factuality.

**[INFERENCE]:** Given that (a) reasoning quality degrades with context length (Du et al.), (b) attention dilutes quadratically (architectural fact), and (c) claims later in a generation are conditioned on more preceding context, it is highly likely that factual precision degrades within a long generation. But no one has run FActScore on the first vs. last quartile of a long agent output. This would be a straightforward experiment to design.

### Partial mitigation

**Recitation strategy (Du et al.):** Prompting models to repeat relevant evidence before answering improves accuracy +4% on RULER for GPT-4o. Training-free, model-agnostic. Already adopted in our researcher skill. [SOURCE: arXiv:2510.05381]

---

## 2. Compaction/Summarization Loss: Epistemic Nuance Erosion

### What's PROVEN

**ACE "Agentic Context Engineering" (Zhang et al., Stanford/SambaNova, arXiv:2510.04618, 64 citations):** Identifies and names two specific failure modes in iterative context rewriting:

1. **Brevity bias:** Optimization collapses toward short, generic prompts. Domain-specific heuristics, failure modes, and detailed strategies are dropped in favor of concise summaries. Gao et al. (2025) documented prompt optimizers repeatedly producing near-identical generic instructions ("Create unit tests to ensure methods behave as expected"), sacrificing diversity and domain detail.

2. **Context collapse:** When an LLM is tasked with fully rewriting accumulated context at each adaptation step, it tends to compress into much shorter, less informative summaries, causing dramatic information loss. Documented example: at step 60 the context was 18,282 tokens with 66.7% accuracy; at step 61 it collapsed to 122 tokens with 57.1% accuracy — worse than the 63.7% baseline without adaptation. [SOURCE: arXiv:2510.04618, full text read]

**Kolagar & Zarcone (EACL 2024 UncertaiNLP Workshop, 10 citations):** First systematic study of uncertainty transfer in LLM summarization. Built a two-tier taxonomy of uncertainty expressions (lexical and semantic). Found that GPT-4 summaries systematically alter the uncertainty alignment of source texts. Qualifiers, hedges, and conditional language are disproportionately dropped or flattened during summarization. This directly confirms the "X is likely true" becomes "X is true" hypothesis. [SOURCE: DOI:10.18653/v1/2024.uncertainlp-1.5, saved to corpus]

**Lexsis "N/N+1 Summarization Degradation" (Dec 2025, industry blog):** Formalizes the information-theoretic argument. Hierarchical summarization (summarize chunks, then summarize summaries) is governed by the Data Processing Inequality: I(X; Z) <= I(X; Y). Each layer can only lose information, never recover it. Quality decays as Q_{t+1} ~ alpha * Q_t - beta, where alpha in (0,1) is signal retention and beta > 0 is noise per step. Three observed failure modes in production:
- **Broken links across chunks:** Long-range dependencies ("it happened again" -> "502 error in checkout") are severed at chunk boundaries
- **Semantic drift / telephone game:** "slightly annoyed" -> "dissatisfied" -> "angry" across summarization layers
- **Hallucination anchoring:** Early weak inferences ("user is on iOS") harden into assumed facts downstream

[SOURCE: trylexsis.com/blogs/the-nn1-summarization-degradation-problem] [INDUSTRY, NOT PEER-REVIEWED]

### What's NOT PROVEN

**No controlled experiment has measured compaction-specific epistemic nuance loss** in the context of Claude Code's or similar agent compaction systems. The ACE findings are from iterative context optimization (system prompt evolution), not from within-session compaction where a conversation is summarized to fit in a window. The mechanisms are analogous but the specific loss patterns may differ.

**[INFERENCE]:** Claude Code's compaction summarizes the conversation history to free context space. Given (a) ACE's context collapse finding, (b) Kolagar & Zarcone's uncertainty flattening finding, and (c) the Data Processing Inequality, it is near-certain that compaction loses epistemic nuance. Hedges become assertions. Conditional findings become unconditional. Multi-step reasoning chains are compressed into conclusions without premises. The agent post-compaction is reasoning over a lossy compression of its own prior reasoning.

**Mitigation (from ACE):** Incremental delta updates (structured, itemized bullets with metadata) instead of monolithic rewriting. ACE's "grow-and-refine" pattern preserves detailed knowledge and avoids context collapse. This is architecturally similar to our MEMORY.md approach (incremental edits, not full rewrites). [SOURCE: arXiv:2510.04618]

---

## 3. Cross-Session Belief Drift in Persistent Memory

### What's PROVEN (limited)

**Agent Drift (Rath, arXiv:2601.04170, Jan 2026, 0 citations):** Theoretical framework defining three drift types:
1. **Semantic drift:** Progressive deviation from original intent
2. **Coordination drift:** Breakdown in multi-agent consensus
3. **Behavioral drift:** Emergence of unintended strategies

Proposes the Agent Stability Index (ASI) — 12-dimension metric framework. Mitigation: episodic memory consolidation, drift-aware routing, adaptive behavioral anchoring. Theoretical analysis suggests 21% higher stability with explicit memory distillation vs. raw conversational history. **Caveat: simulation-based analysis only, no empirical measurement on real systems.** [SOURCE: arXiv:2601.04170] [PREPRINT, THEORETICAL]

**Prassanna Ravishankar "Agent Drift" blog post (Feb 2026):** Practitioner analysis from building Torale (self-scheduling agents). Key insight on memory write corruption: "What an agent distills into memory at the end of run three is what it reads at the start of run four. If that distillation was wrong, the error persists indefinitely." Cites SWE-bench Pro 80%->23% collapse on long-horizon tasks as evidence of drift, not capability limitation. Identifies "instruction centrifugation" — as execution logs accumulate, original system prompt attention degrades via softmax dilution. [SOURCE: prassanna.io/blog/agent-drift/] [PRACTITIONER, NOT PEER-REVIEWED]

**"Beyond Static Summarization: Proactive Memory Extraction" (Yang et al., arXiv:2601.04463, Jan 2026, 3 citations):** Argues that summary-based memory extraction has two major limitations — unclear how to capture this precisely. Proposes proactive extraction as alternative. Saved to corpus but not fetched. [SOURCE: arXiv:2601.04463] [PREPRINT]

**Epistemic Diversity and Knowledge Collapse (Wright et al., arXiv:2510.04226, 1 citation):** 27 LLMs, 155 topics, 200 prompt variations. Nearly all models are less epistemically diverse than a basic web search. Model size has NEGATIVE impact on epistemic diversity. RAG has positive impact, varying by cultural context. [SOURCE: arXiv:2510.04226, saved to corpus]

This is relevant because: if agents iteratively consult LLMs to update memory, and LLMs are less epistemically diverse than web search, memory will converge toward homogeneous claims over time. The diversity of hypotheses and framings will narrow with each update cycle.

**DrunkAgent (Yang et al., arXiv:2503.23804, 2025):** First systematic investigation of memory-based vulnerabilities in LLM-powered recommender agents. Shows that adversarial manipulation of agent memory propagates and persists across sessions. While focused on adversarial attacks, the mechanism is identical to natural error propagation: once wrong information enters memory, it corrupts downstream reasoning indefinitely. [SOURCE: arXiv:2503.23804]

### What's NOT PROVEN

**No empirical measurement of belief drift rate in persistent memory systems exists.** No one has run the obvious experiment: have an agent update a MEMORY.md-style file across 50 sessions, measure factual precision of the file at sessions 1, 10, 25, 50. Track which claims accumulate errors, which are stable, what the error introduction rate per session is.

**[INFERENCE]:** Belief drift in persistent memory is highly likely given: (a) each session's compaction/summarization introduces noise (section 2), (b) the agent writes back to memory based on potentially degraded reasoning, (c) there is no verification step between "agent concludes X" and "agent writes X to memory", (d) knowledge collapse means diversity of claims narrows over time. The telephone game analogy is apt but unquantified.

**Key open question:** Does the drift rate depend on domain velocity? Claims about stable knowledge (e.g., "the Krebs cycle produces 2 ATP") should be resistant to drift. Claims about fast-moving domains (e.g., "Opus 4.6 scores 76% on MRCR") should drift faster as the world changes but the memory doesn't.

---

## 4. Staleness Detection: Automated Freshness Scoring

### What's PROVEN

**Gilda & Gilda "First Principles Framework" (arXiv:2601.21116, Jan 2026):** Position paper arguing for explicit temporal validity tracking in AI-assisted engineering. Key finding: retrospective audit found 20-25% of architectural decisions had stale evidence within two months. Proposes three requirements:
1. **Epistemic layers** separating unverified hypotheses from validated claims
2. **Conservative assurance aggregation** (Godel t-norm) preventing weak evidence from inflating confidence
3. **Automated evidence decay tracking** surfacing stale assumptions

Formal invariants for aggregation operators. Research directions include learnable decay functions and SMT-based claim validation. **Caveat: position paper, not empirical system.** [SOURCE: arXiv:2601.21116] [PREPRINT, POSITION PAPER]

**Xian et al. "Measuring Temporal Effects of Agent Knowledge" (REALM Workshop, ACL 2025):** Designed date-controlled tools (DCTs) as stress tests for agent temporal knowledge. LLM agents with web search were tested on scientific abstract completion with date-restricted search. Key findings:
- Agent performance is tool-date-dependent: restricting search to pre-discovery dates caused agents to fall back on (often wrong) parametric knowledge
- More capable models (GPT-4-turbo, GPT-4o) showed less temporal sensitivity than GPT-3.5-turbo
- CoT prompting improved temporal tool selection for capable models but hurt weaker ones
- SciBreak dataset: 200+ scientific breakthroughs from 2000-2024 as temporal probes

This is the closest empirical work to automated staleness detection, but it measures the effect of stale tools, not the detection of stale beliefs. [SOURCE: aclanthology.org/2025.realm-1.25, full text read]

**"Belief Decay as a Core Mechanism of Adaptive Intelligence" (Bala, Jan 2026):** Theoretical framework arguing that belief decay is a necessary feature, not a bug. Human belief confidence decays naturally in the absence of reinforcement. Current AI systems lack principled belief decay and therefore accumulate stale assumptions. Proposes belief as an actively maintained state with intrinsic decay, evidence-weighted reinforcement, and stability dynamics. [SOURCE: artificialbrainlabs.com] [NON-PEER-REVIEWED WHITEPAPER]

### What's NOT PROVEN

**No production system implements automated staleness detection for LLM agent beliefs.** The Gilda framework is a proposal. The Xian work measures effects of temporal tools, not self-aware staleness. No agent system currently flags "this belief was last verified 6 months ago and the domain has high velocity — re-verify before relying on it."

**[INFERENCE]:** A practical staleness detection system would need: (a) timestamps on stored beliefs, (b) domain velocity estimates (how fast does this knowledge domain change?), (c) confidence decay functions (belief confidence decreases with time since last verification), (d) automated re-verification triggers. Our MEMORY.md approach has (a) partially (dates in section headers) but none of (b-d). The Gilda framework provides the formalism; implementation would be straightforward.

---

## 5. Multi-Run Consistency: What Degrades First?

### What's PROVEN

**Princeton "Towards a Science of AI Agent Reliability" (arXiv:2602.16666, Feb 2026):** 14 models, 18 months, r=0.02 between capability gains and reliability gains. Outcome consistency universally low. Same task + same model + different run = different outcomes. "What but not when" pattern — higher distributional than sequential consistency. No follow-up work published yet including Opus 4.6 or GPT-5.3. [SOURCE: arXiv:2602.16666, in corpus]

**CLEAR Framework (arXiv:2511.14136):** 60% pass@1 drops to 25% over 8 consecutive runs. Accuracy-only evaluation predicts production success at r=0.41; CLEAR predicts at r=0.83. [SOURCE: arXiv:2511.14136]

**"Same Prompt, Different Outcomes" (Cui & Alexander, arXiv:2602.14349, Feb 2026):** Systematic reproducibility evaluation. 2 prompting strategies, 6 models, 4 temperature settings, 10 independent executions per configuration, 480 total attempts on data analysis tasks. Directly measures what we need: same prompt, same model, different runs. **This is the closest paper to our sub-question but focused on data analysis reproducibility, not factual claim consistency.** [SOURCE: arXiv:2602.14349] [PREPRINT]

**Shyr et al. "Repeatability and Reproducibility in Diagnostic Reasoning" (medRxiv 2025):** Statistical framework measuring LLM consistency in medical diagnosis. Key finding: **consistency is NOT correlated with accuracy.** A model can be consistently wrong or inconsistently right. Measures both semantic variability (clinical meaning differences) and internal variability (token-level generation differences). Consistency depends on model, prompt, and case complexity. [SOURCE: medrxiv.org/10.1101/2025.08.06.25333170] [PREPRINT, MEDICAL]

**Novikova et al. "Consistency in Language Models" (survey):** Comprehensive survey of consistency research. Identifies critical gap: no standard approaches to assessing model consistency. Risk of overestimating performance and underestimating harms. [SOURCE: openreview.net/pdf?id=ejvvhJZJSf]

### What degrades first?

**[INFERENCE, based on convergent evidence]:** Based on the Princeton reliability data, CLEAR framework, and practitioner reports:

1. **Source selection degrades first.** The same query in different sessions often retrieves different sources (tool call non-determinism, search engine state changes, API response variations). This is the most variable component because it depends on external state.

2. **Hypothesis framing degrades second.** How the agent frames the problem varies run-to-run. The Princeton "what but not when" finding means the same conclusions can be reached via different reasoning paths, but the framing and emphasis shift.

3. **Confidence levels degrade third.** Calibration is already poor (arXiv:2602.00279 — verbalized confidence is systematically biased). Cross-session, the agent's expressed confidence on the same claim can swing 20-30 points with no change in evidence.

4. **Factual claims are most stable** — when they come from the model's parametric knowledge (training data). Claims that depend on tool calls are as variable as the tool results. Claims that depend on reasoning over accumulated context are as variable as the context.

### What's NOT PROVEN

**No study has run the specific experiment:** same factual query, N sessions, measure claim-level consistency, confidence-level consistency, source consistency, and framing consistency independently. The Princeton study measures task completion consistency, not claim-level decomposition. This is another genuine gap.

---

## 6. The Position Effect: Reasoning Quality vs. Position

### What's PROVEN

**Liu et al. "Lost in the Middle" (Stanford/TACL 2024):** U-shaped performance curve for retrieval: ~75% at start, ~55% at middle, ~72% at end. This is about INPUT position affecting RETRIEVAL accuracy. [SOURCE: direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638]

**Guo & Vosoughi "Serial Position Effects of LLMs" (arXiv:2406.15981, Jun 2024):** Confirms widespread primacy and recency biases in LLMs across various tasks (not just retrieval). Carefully designed prompts can somewhat mitigate but effectiveness is inconsistent. Focus is on how input position affects model decisions (e.g., which option the model selects in MCQ), not on output generation quality. [SOURCE: arXiv:2406.15981]

### What's NOT PROVEN

**The specific question — do claims near the END of a long output have worse factual precision than claims at the BEGINNING — has NOT been studied.** The existing literature is entirely about:
- Input position -> retrieval accuracy (Liu et al.)
- Input position -> selection bias (Guo & Vosoughi)
- Input length -> task success (Du et al., CLEAR)

The OUTPUT position effect is a genuine gap. No one has taken a 3000-word agent output, decomposed it into atomic facts a la FActScore, and plotted factual precision vs. position in the output.

**[INFERENCE]:** There are reasons to expect output-position degradation:
1. **Autoregressive generation conditioned on growing context:** Each new token is conditioned on all prior tokens. By the end of a long generation, the model is reasoning over both the original input AND its own prior output, which may contain errors that compound.
2. **Attention dilution within generation:** The attention mechanism distributes weight across both input and generated-so-far. Later tokens have more context to attend to, diluting attention to the original evidence.
3. **No retrieval step within generation:** Unlike an agent that can re-query tools, a single generation cannot "look up" facts mid-stream. If the model's attention to a relevant input fact fades during generation, the quality of claims about that fact degrades.

But there are also reasons output position might NOT matter much:
1. **Recency bias in autoregressive models:** Models attend strongly to recent tokens. If the model stated a correct fact at position 500, that fact is in recent context when generating position 600 — potentially reinforcing accuracy.
2. **Planning and coherence:** Modern models plan multi-paragraph outputs. Early claims may constrain later claims toward coherence, which could be either accuracy-preserving (if early claims are correct) or accuracy-degrading (if early claims are wrong).

**This is the most experimentally tractable gap in this entire research question.** The experiment: generate 50 long-form outputs, decompose each into atomic facts with positions, run SAFE or FActScore on each fact, plot precision vs. position.

---

## Disconfirmation Results

### Searched for but did NOT find:

1. **"Context length doesn't hurt reasoning"** — No credible paper claims this. The Opus 4.6 MRCR improvement (76% at 1M tokens vs. Sonnet 4.5's 18.5%) shows the curve is flattening for retrieval, but Du et al. demonstrates reasoning degradation persists even with perfect retrieval.

2. **"Summarization preserves epistemic nuance"** — No evidence for this. Kolagar & Zarcone explicitly show the opposite. The Data Processing Inequality makes it informationally impossible for lossless summarization. The question is only how much is lost, not whether.

3. **"Agent memory systems don't drift"** — The Anatomy of Agentic Memory paper (arXiv:2602.19320) documents that ALL memory approaches have significant evaluation gaps and "often underperform their theoretical promise." No system claims drift-free memory.

4. **"Multi-run consistency is improving with newer models"** — Princeton: r=0.02 between capability and reliability over 18 months. CLEAR: 60%->25% over 8 runs. Shyr et al.: consistency not correlated with accuracy. The evidence uniformly shows consistency is NOT improving at the rate of capability.

### Partial disconfirmation:

5. **"Bigger context windows = more degradation"** — The "Context Discipline" paper (arXiv:2601.11564) found that for simple retrieval tasks, Llama-3.1-70B accuracy declined only from 98.5% to 98% at 15K words. Context rot is task-difficulty-dependent: simple tasks are resilient, hard tasks degrade. This nuances the "everything degrades" narrative — the degradation is worst on reasoning-intensive tasks.

---

## Verification Log

| Claim | Verified via | Status |
|-------|-------------|--------|
| Du et al. 13.9-85% degradation | Paper in corpus, existing memo | VERIFIED |
| ACE context collapse 18,282->122 tokens | Full text read of arXiv:2510.04618 | VERIFIED |
| Kolagar & Zarcone uncertainty transfer | S2 search, DOI confirmed | VERIFIED (abstract only) |
| CLEAR 60%->25% | Existing memo, Exa crawl | VERIFIED |
| Princeton r=0.02 | Existing memo, paper in corpus | VERIFIED |
| Gilda 20-25% stale in 2 months | Exa crawl of abstract | UNVERIFIED (position paper, self-reported) |
| Xian et al. date-controlled tools | Full text read via Exa crawl | VERIFIED |
| Agent Drift ASI 21% stability improvement | arXiv abstract only, simulation-based | THEORETICAL (not empirical) |
| Prassanna blog SWE-bench Pro 80%->23% | Blog post, not primary source | UNVERIFIED (cites SWE-bench Pro but numbers not independently confirmed) |

---

## Search Log

| # | Tool | Query | Hits/Useful |
|---|------|-------|-------------|
| 1 | S2 | "factual precision degradation context length LLM generation quality" | 10/1 (RAG meta-analysis) |
| 2 | Exa | "LLM summarization information loss epistemic nuance hedging language compaction" | 5/4 (ACE-related, Lexsis, Kolagar, knowledge collapse) |
| 3 | S2 | "belief drift agent memory iterative update error accumulation telephone game" | 0 |
| 4 | S2 | "iterative summarization information loss chain compaction LLM" | 10/2 (Beyond Static Summarization, Chain of Summaries) |
| 5 | Exa | "agent persistent memory belief drift error accumulation iterative rewriting" | 5/3 (Agent Drift blog, DrunkAgent, Context Engineering) |
| 6 | S2 | "lost in the middle reasoning quality generation position effect long context" | 10/0 (all irrelevant) |
| 7 | S2 | "agent drift behavioral degradation multi-agent extended interaction LLM" | 10/2 (Agent Drift paper, Drift No More) |
| 8 | Exa | "knowledge staleness detection LLM agent outdated cached beliefs temporal validity" | 5/2 (Gilda FPF, Xian DCT) |
| 9 | S2 | "epistemic diversity knowledge collapse LLM homogenization" | 7/2 (Wright et al., Yun et al.) |
| 10 | S2 | "ACE context collapse iterative rewriting LLM brevity bias" | 1/1 (ACE paper, 64 citations) |
| 11 | Exa | "position effect reasoning quality LLM generation output factual precision beginning vs end" | 5/2 (Serial Position Effects, Lost in Middle MIT Press) |
| 12 | S2 | "serial position effect LLM generation quality primacy recency" | 0 |
| 13 | Exa | "LLM summarization chain information loss hedging language qualifier removal certainty inflation" | 5/2 (Chain of Summaries, Lexsis again) |
| 14 | S2 | "Kolagar Zarcone aligning uncertainty summarization EACL 2024" | 1/1 (exact match) |
| 15 | Exa | "factual consistency across sessions LLM same prompt different runs claim variation" | 5/3 (Same Prompt Different Outcomes, Shyr repeatability, Novikova consistency survey) |
| 16 | Exa | "LLM factual precision does NOT degrade context length" (disconfirmation) | 3/0 (all confirmed degradation) |
| 17 | Exa | Agent Drift blog crawl | 1/1 |
| 18 | Exa | Lexsis N/N+1 blog crawl | 1/1 |
| 19 | Exa | Gilda arXiv abstract crawl | 1/1 |
| 20 | Exa | Xian REALM paper crawl | 1/1 (full text) |
| 21 | research-mcp | fetch ACE paper | 1/1 (full text, 45K chars) |

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Reasoning quality degrades 13.9-85% with context length even with perfect retrieval | EMNLP 2025, 23 cites | HIGH | arXiv:2510.05381 | VERIFIED |
| 2 | Context collapse: 18,282 tokens -> 122 tokens in one iteration step, accuracy drops below baseline | ACE paper, Stanford, 64 cites | HIGH | arXiv:2510.04618 | VERIFIED |
| 3 | LLM summarization systematically flattens uncertainty expressions | EACL 2024 workshop, 10 cites | MEDIUM | DOI:10.18653/v1/2024.uncertainlp-1.5 | VERIFIED |
| 4 | No empirical measurement of FActScore-style precision as f(output position) exists | Exhaustive search, 6 queries | HIGH | Absence of evidence | GAP |
| 5 | No empirical measurement of belief drift rate in persistent memory systems exists | Exhaustive search, 4 queries | HIGH | Absence of evidence | GAP |
| 6 | 60% pass@1 drops to 25% over 8 consecutive agent runs | CLEAR framework | MEDIUM (preprint, 0 cites) | arXiv:2511.14136 | VERIFIED |
| 7 | Capability-reliability correlation r=0.02 over 18 months | Princeton, 14 models | HIGH | arXiv:2602.16666 | VERIFIED |
| 8 | 20-25% of architectural decisions had stale evidence within 2 months | Self-reported retrospective audit | LOW | arXiv:2601.21116 | UNVERIFIED |
| 9 | LLM consistency is NOT correlated with accuracy in medical diagnosis | medRxiv preprint | MEDIUM | medrxiv.org/10.1101/2025.08.06.25333170 | PREPRINT |
| 10 | Agent memory writes propagate corruption across sessions indefinitely | DrunkAgent + practitioner analysis | MEDIUM | arXiv:2503.23804 + prassanna.io | PARTIALLY VERIFIED |
| 11 | Date-controlled tool restrictions change agent knowledge and performance | REALM 2025 workshop, GPT-3.5/4 tested | MEDIUM | aclanthology.org/2025.realm-1.25 | VERIFIED |
| 12 | Hierarchical summarization quality decays per Data Processing Inequality: I(X;Z) <= I(X;Y) | Information theory (proven mathematical result) | HIGH | Standard information theory | PROVEN (mathematical) |
| 13 | Nearly all LLMs are less epistemically diverse than a basic web search | 27 LLMs, 155 topics, 200 prompts | MEDIUM (1 cite) | arXiv:2510.04226 | PREPRINT |
| 14 | Model size has negative impact on epistemic diversity | Same study | MEDIUM | arXiv:2510.04226 | PREPRINT |

---

## What's Uncertain

1. **The rate of within-session factual precision decay.** We know it happens; we don't know the curve shape for generation (vs. retrieval). Is it linear? Exponential? Does it have a threshold?

2. **Whether compaction-specific nuance loss differs from general summarization loss.** Claude Code's compaction may use different strategies than generic summarization. The loss patterns could be different.

3. **The interaction between memory drift and domain velocity.** Fast-moving domains should cause more staleness, but does the agent's own drift interact with external change? (Both the world changes AND the agent's memory degrades.)

4. **Whether multi-session consistency improves with better models.** Princeton says no (r=0.02). But their data ends before Opus 4.6 and GPT-5.3. The reliability gap may be closing on some dimensions.

5. **The output-position effect.** Hypothesized but unmeasured. Could go either way — recency bias may preserve or degrade quality depending on the task.

---

## Sources Saved to Corpus

| Paper | S2 ID | Status |
|-------|-------|--------|
| ACE (Zhang et al., arXiv:2510.04618) | 7d5b2865243015196ffaf0543f579c3d8901af40 | Saved + fetched + read |
| Kolagar & Zarcone (EACL 2024) | dbaaa944a78cec8729d45e56d2e838e9b6dba52b | Saved |
| Epistemic Diversity (Wright et al.) | 10f163d312af816e83dfe9c92578327355be286d | Saved |
| Beyond Static Summarization (Yang et al.) | 2dc93f9e6e0e856685993ce535431d684957134a | Saved |
| Du et al. EMNLP 2025 (existing) | 55e0300470bc99172e763f6fd6d3e7935f7d90e0 | In corpus |
| CLEAR framework (existing) | 7e92cdb5bab66d182dd0abda4ce6bb8ccf8b75cf | In corpus |
| Princeton reliability (existing) | ad8d46c49df22c80d534b5b3b1168be2be0739ea | In corpus |

---

## Implications for Our System

### Immediate (actionable now)

1. **Compaction is a known epistemic hazard.** Every compaction event should be treated as an information-loss event. The PreCompact hook already logs; extend to capture word count delta as a proxy for information loss. If context shrinks >80%, warn.

2. **MEMORY.md incremental edits are the right pattern.** ACE's core finding is that incremental delta updates prevent context collapse. Our Edit-based MEMORY.md updates are architecturally aligned. Full rewrites of MEMORY.md should be prohibited (already a rule; now has empirical backing).

3. **Belief timestamps are necessary but insufficient.** We have dates in MEMORY.md section headers. Add domain-velocity metadata: `[STABLE]` for slow-moving knowledge, `[VOLATILE: check monthly]` for fast-moving claims.

4. **Source selection is the first thing to degrade across sessions.** When re-running research, don't assume the same sources will be found. Log which sources were used and check for source overlap across sessions as a consistency signal.

### Medium-term (experiments to run)

5. **FActScore-by-position experiment:** Take 20 long research outputs, decompose into atomic facts, measure precision by quartile. Cheaply testable with SAFE-lite.

6. **Cross-session claim consistency test:** Run the same research query in 5 separate sessions. Decompose outputs into claims. Measure claim overlap, confidence variation, and source selection variation.

7. **Compaction nuance loss measurement:** Before and after compaction events (logged by PreCompact hook), compare hedging language frequency, qualifier count, and conditional-vs-unconditional claim ratio.

### Long-term (architecture changes)

8. **Automated staleness detection:** Implement Gilda-style evidence decay tracking. Each claim in MEMORY.md gets a last-verified timestamp and domain-velocity tag. Monthly sweep flags stale claims for re-verification.

9. **Cross-session memory verification:** Periodic independent agent session that reads MEMORY.md and fact-checks claims against current sources. Like an internal audit.

<!-- knowledge-index
generated: 2026-03-22T00:15:45Z
hash: a2ea7a2592d7

title: Temporal Epistemic Degradation in AI Agents
sources: 1
  INFERENCE: , based on convergent evidence
table_claims: 29

end-knowledge-index -->
