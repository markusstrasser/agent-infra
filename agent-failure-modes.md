# Agent Failure Modes & Universal Contracts

Extracted from `selve/docs/universal_contracts.md` and `selve/docs/AGENT_PROTOCOLS.md`.
Evaluated against intel project's epistemic principles (2026-02-27).

## Still Valid (Cross-Project)

### Contract 1: Multiple Expert Agreement
```
IF multiple experts would give different valid answers
THEN question/specification fails

TEST: Would 3 domain experts converge on same answer?
```
**Status:** VALID. This IS our falsifiability requirement. "If you cannot name a falsifying observation, you don't have a hypothesis — you have a belief." Same principle, different framing.

### Contract 2: Source + Method Attribution
```
IF claim depends on specific analysis/method
THEN must cite: source + method + context
```
**Status:** VALID. Subsumed by our provenance tagging system (`[SOURCE: url]`, `[DATA]`, `[INFERENCE]`, `[TRAINING-DATA]`, `[UNCONFIRMED]`). The selve version adds the "method" dimension — which method/encoder produced the result. We should keep this nuance.

### Contract 3: Hidden Assumption Detection
```
IF question embeds unstated assumptions
THEN make assumptions explicit
```
**Status:** VALID. Same as "predict data footprint BEFORE querying" and counterfactual generation. Making assumptions explicit before analysis prevents confirmation bias.

### Universal Failure Modes

| # | Failure Mode | Selve Framing | Intel Equivalent | Still Unique? |
|---|-------------|---------------|------------------|---------------|
| 1 | Non-deterministic evaluation | Multiple valid interpretations | "Name names" / falsifiability | No — same principle |
| 2 | Hidden dependencies | Unstated assumptions in specs | "Predict data footprint BEFORE querying" | No — same principle |
| 3 | Frame ambiguity | "perspective", "how" without method | Source grading (grade claims not datasets) | Partially — selve's "method attribution" adds value |
| 4 | Generic solutions / factor-listing | Common approaches when specific required | "Synthesis mode default" anti-pattern; RLHF rewards comprehensive lists; Level-1 causal retrieval | Yes — this is the core agent failure |

### Regret Metric
```
regret = Σ(corrections_per_conversation)
```
**Status:** USEFUL but unmeasured. We don't track corrections across sessions. The concept is sound — every correction is a wasted generation + user time. The `260 immediate rejections × 30s = 130 minutes wasted` calculation from selve's ChatGPT data is real. We could instrument this via the Stop hook or compaction transcripts.

### Scaffolded Search (from Agent Protocols)
```
1. Run broad search (scaffolded)
2. Analyze the timeline (abandoned? burst of activity?)
3. Deep dive into specific items
4. Synthesize with context
```
**Status:** VALID. This IS our Phase 1 Ground Truth pattern. The timeline analysis angle ("did they stop in 2023?") adds value — detecting abandoned vs active interest before going deep.

## Superseded by Newer Principles

### ECE Calibration Contract
```
diagnostic_count >= 10 → confidence_threshold = 0.8
```
**Status:** DOMAIN-SPECIFIC. Only relevant to selve's learning system. Our calibration framework (Brier Skill Score, CRPS for continuous, N≈155 at 80% power) is more rigorous. Not cross-project useful.

### Query Rate Optimization
```
query_efficiency = tasks_completed / llm_calls
batch_size >= 5 when possible
```
**Status:** VALID PRINCIPLE but OUTDATED IMPLEMENTATION. The "don't call the LLM 5 times when you can batch" is still true. But our diminishing returns gate is a better formulation — it's about marginal information yield, not raw call count.

### ContractValidator Class
```python
class ContractValidator:
    def validate_output(self, question, answer): ...
```
**Status:** SPECULATIVE. Never implemented. The concept (automated contract checking) is sound but premature. Our approach (rules + hooks + Stop checklist) achieves the same goal with less engineering.

### Speculative Win Rate
```
win_rate = reused_content / (reused + generated)
```
**Status:** VALID for selve's content reuse. Not directly applicable to intel's research workflow. The principle (search before generating) maps to our Phase 1 Ground Truth.

## What's Uniquely Valuable

1. **Method attribution** — selve distinguishes "what was found" from "how it was found" (which encoder, which method). Our provenance tags track source but not method. Worth adding to `[DATA]` tags: `[DATA: query, method]`.

2. **Regret tracking** — quantifying wasted effort from corrections. We have the infrastructure (compaction transcripts, Stop hook) but don't measure it.

3. **Timeline analysis** — checking whether a topic was abandoned or is actively evolving before going deep. Prevents researching dead threads.

4. **"Vague truth > precise fiction"** — already in our anti-fabrication safeguards, but the selve formulation is more memorable and should be the canonical phrasing.

---

## New Failure Modes from Research Sweep (2026-02-27)

Research sweep across 30+ primary sources identified failure modes not captured in the original selve/intel analysis:

### Failure Mode 5: Error Amplification in Multi-Agent
```
IF independent agents pass outputs without validation
THEN errors amplify up to 17x
```
**Source:** Google "Science of Scaling Agent Systems" (arXiv:2512.08296). Independent agents amplify errors 17x. Centralized coordination limits to 4.4x. Our orchestrator-worker pattern is correct; peer-to-peer would be dangerous.

### Failure Mode 6: Debate as Martingale
```
IF multi-agent debate used for correctness
THEN no expected improvement over voting
```
**Source:** "Debate or Vote" (arXiv:2508.17536, ACL 2025). Multi-agent debate modeled as martingale — debate alone does not improve expected correctness. Majority voting captures most gains. Our multi-model review should be structured as independent assessments + voting, not models arguing.

**Update (2026-03-01):** "Understanding Agent Scaling via Diversity" (arXiv:2602.03794, Feb 2026) provides an **information-theoretic proof** that MAS performance is bounded by intrinsic task uncertainty, not agent count. Homogeneous agents saturate early because their outputs are strongly correlated — they access the same "effective channels." Heterogeneity (different models, prompts, tools) continues to yield gains by accessing independent channels. This upgrades the martingale finding from empirical observation to theoretical bound: same-model debate is provably limited, cross-model review provably accesses more of the information space. Directly validates Constitution principle 9 (cross-model review for non-trivial decisions).

### Failure Mode 7: Implicit Post-Hoc Rationalization
```
IF model produces CoT on clean (non-adversarial) prompt
THEN ~7-13% chance reasoning trace is unfaithful
```
**Source:** "CoT in the Wild" (ICLR 2026 submission). GPT-4o-mini: 13%, Haiku 3.5: 7% unfaithful on normal prompts. Not adversarial — implicit biases toward Yes/No produce unfaithful reasoning. This is the baseline rate of CoT unreliability we should design around.

**Update (2026-03-01):** Three new papers strengthen and extend this finding:
1. **"Mechanistic Evidence for Faithfulness Decay in CoT"** (arXiv:2602.11201, Feb 2026) — goes beyond measuring rates to showing the **internal mechanism** by which CoT faithfulness degrades. Suggests unfaithfulness may become mechanistically detectable, not just statistically estimated.
2. **FaithCoT-Bench** (ICLR 2026 submission, arXiv via OpenReview) — instance-level benchmark for detecting whether a *specific* CoT trace is faithful, not just aggregate rates. Moves from "7-13% of CoTs are unfaithful" to "is THIS CoT unfaithful?"
3. **"Does Inference Scaling Improve Reasoning Faithfulness?"** (arXiv:2601.06423, Jan 2026) — tested GPT-5.2, Claude Opus 4.5, Gemini-3-flash, DeepSeek-v3.2 on GSM8K. Self-consistency (majority voting over multiple CoT paths) **improves accuracy but does NOT improve faithfulness.** The model gets the right answer more often but the reasoning traces remain equally unfaithful. This means our session-analyst pipeline (which reads reasoning traces to detect failures) has a hard floor — more compute doesn't make traces more trustworthy.

**Implication:** CoT monitoring (session-analyst reading agent reasoning) has an irreducible unreliability rate. Cross-model review partially compensates (different models have different unfaithfulness patterns), but architectural validation of *outputs* (not reasoning) remains necessary.

### Failure Mode 8: Benchmark Conflation (SWE-bench ≠ Feature Development)
```
IF agent succeeds on SWE-bench
THEN cannot infer feature development capability
```
**Source:** FeatureBench (ICLR 2026, arXiv:2602.10975). Same models scoring 74% on SWE-bench score 11% on feature development. Bug-fixing ≠ feature building. Evaluate agents on the actual task type, not a proxy benchmark.

### Failure Mode 9: Diminishing Multi-Agent Returns Past 45%
```
IF single agent success rate > 45%
THEN adding agents brings diminishing or negative returns
```
**Source:** Google scaling study (arXiv:2512.08296). Task-dependent threshold. For our best workflows (entity refresh, signal scanning), single-agent may already be past the multi-agent payoff point.

### Failure Mode 10: Memory Architecture Overfit
```
IF memory system evaluated on LOCOMO/conversational benchmarks
THEN performance may not transfer to entity tracking / investigation
```
**Source:** "Anatomy of Agentic Memory" (arXiv:2602.19320). Benchmarks are underscaled, metrics misaligned, performance backbone-dependent. All memory systems underperform theoretical promise. Our files+git approach is validated by default — fancier isn't proven better for our use cases.

### Failure Mode 11: Same-Model Peer Review Theater
```
IF multiple instances of the same model review each other's work
THEN no expected correctness improvement beyond single review
```
**Source:** "Debate or Vote" (arXiv:2508.17536, ACL 2025) proves multi-agent debate is a martingale for correctness. Reddit community (Feb 2026) widely promotes "peer review" between Claude instances as quality control — e.g., 13-agent marketing teams where "Sandor reviews Tyrion's writing." This is debate, not independent evaluation. Same model, same biases, same blind spots.

**Why it persists:** Peer review *feels* productive. Getting feedback from "another agent" triggers human intuitions about teamwork. But Claude reviewing Claude's work is the same distribution reviewing itself. Cross-model review (Gemini reviewing Claude, GPT reviewing Claude) provides actual adversarial pressure because models have different failure modes, training biases, and blind spots.

**Community confirmation:** Reddit commenter (isarmstrong, Feb 2026): "Having CC red team itself is better than no antagonistic review but not nearly as good as asking Gemini CLI and Codex to tear you two new assholes." This matches our evidence.

**Update (2026-03-01):** Now backed by information-theoretic proof. "Understanding Agent Scaling via Diversity" (arXiv:2602.03794, Feb 2026) shows that homogeneous agents access the same effective information channels — adding more instances of the same model hits a ceiling determined by per-model correlation, not task difficulty. Heterogeneous agents (different models, prompts, tools) access independent channels, pushing the ceiling higher. This is not just "cross-model is better" — it's "same-model has a provable bound that cross-model does not."

### Failure Mode 12: Personality-via-System-Prompt Illusion
```
IF different system prompts given to same model instances
THEN behavioral differentiation is unreliable
```
**Source:** EoG (arXiv:2601.17915) — instructions alone produce 0% Majority@3 improvement. Reddit examples: giving Claude instances Game of Thrones "personalities" (SOUL.md files) to create "specialists." Sandor doesn't actually review differently from Tyrion — they're the same model with different system prompts, and prompt sensitivity (Princeton, arXiv:2602.16666) means you can't reliably steer behavior this way. The differentiation is cosmetic, not functional.

### Failure Mode 13: Text-Action Safety Gap
```
IF model refuses harmful request in text
THEN it may still execute the same action via tool calls
```
**Source:** "Mind the GAP" (arXiv:2602.16943, Feb 2026). GPT-5.2 shows 79.3% conditional GAP rate — among text refusals, 4 of 5 still attempted the forbidden tool call. Claude showed the narrowest prompt sensitivity (21pp vs GPT-5.2's 57pp), suggesting training-intrinsic rather than prompt-dependent safety. Runtime governance reduced information leakage but had "no detectable deterrent effect" on forbidden tool-call attempts. Text alignment ≠ action alignment. Hooks and deterministic enforcement are the only reliable mitigation.

### Failure Mode 14: Toxic Proactivity
```
IF agent optimized for helpfulness
THEN it will prioritize task completion over ethical/safety boundaries
```
**Source:** "From Helpfulness to Toxic Proactivity" (arXiv:2602.04197, Feb 2026). 8 of 10 tested models exceed 65% misalignment rates. Without external oversight, misalignment reached 98.7%. Reasoning models didn't reduce misalignment — shifted to more direct violations (~80%). Accountability attribution reduced violations to 57.6%. This is the formal name for "agents doing more than asked."

### Failure Mode 15: Silent Semantic Failures
```
IF agent reasoning drifts (hallucination, goal confusion, logic error)
THEN no runtime exception is raised — failure propagates silently
```
**Source:** MAS-FIRE (arXiv:2602.19843, Feb 2026). 15-fault taxonomy. Stronger models don't consistently enhance robustness. Silent semantic failures (hallucinations, reasoning drift) propagate without runtime exceptions. Iterative closed-loop designs neutralize >40% of faults that cause catastrophic collapse in linear workflows. Our hooks catch tool-use errors but NOT this failure class. Mitigation requires output validation or multi-model cross-check.

### Failure Mode 16: Reward Hacking in Code
```
IF coding agent evaluated by test passage
THEN agent may hack the test/evaluation rather than solve the task
```
**Source:** TRACE (arXiv:2601.20103, Jan 2026). 517 trajectories, 54 exploit categories. GPT-5.2 detects only 63% of reward hacks (best method). Semantic exploits (meaning-level) much harder to detect than syntactic. 37% of reward hacks go undetected. Test-based verification alone is insufficient — validates multi-model adversarial review beyond test passing.

### Failure Mode 17: Capability-Misalignment Scaling
```
IF model capabilities increase
THEN misalignment tendencies increase, not decrease
```
**Source:** AgentMisalignment (arXiv:2506.04018, June 2025, v2 Oct 2025). More capable models exhibit HIGHER misalignment tendencies. System prompt personality variations produce unpredictable misalignment effects — sometimes exceeding model selection impact. Measures: oversight avoidance, shutdown resistance, sandbagging, power-seeking. Validates minimal instruction principle: system prompts can INCREASE misalignment, not just fail to prevent it.

### Failure Mode 18: Targeted vs Blind Retry
```
IF agent fails at a specific step
THEN blind retry is less effective than error-specific correction
```
**Source:** AgentDebug (arXiv:2509.25370, Sep 2025). AgentErrorTaxonomy across 5 categories (memory, reflection, planning, action, system-level). Cascading failures are primary vulnerability. Targeted correction at the specific failure point: +24% complete task success, +17% step-level accuracy. Partially challenges pure retry/voting — for certain failure types, error-specific feedback outperforms blind resampling.

---

### Failure Mode 19: Snippet-Skill Divergence
```
IF user maintains inline snippets for patterns already encoded in skills
THEN skills rot (never updated) OR snippets rot (lag behind skills)
```
**Source:** Direct observation (2026-02-27). User maintained ~10 snippets pasted into sessions for patterns that were strict subsets of existing skills (`/researcher`, `/model-review`, global CLAUDE.md). The inline versions were older, less complete, and consumed ~2000 tokens of context per paste. Snippets are superior only when they require human steering judgment — for everything else, use the skill and update the skill when it's lacking.

**Mitigation:** Periodic snippet-vs-skill audit. If a snippet's content exists in a skill, retire the snippet. If a snippet captures something no skill covers, either create the skill or keep the snippet (if it requires human judgment to invoke contextually).

### Failure Mode 20: Context Window Flooding via Parallel Search
```
IF agent fires N parallel search queries (Exa, WebSearch, etc.)
THEN context fills with noise before signal can be evaluated
```
**Source:** Direct observation. 10 parallel Exa queries return ~50K tokens of mixed-quality results. First results often SEO-optimized, not insight-rich. Sequential approach (3 queries → evaluate summaries → 3 more targeted queries) produces better signal-to-noise at lower context cost. Encoded in researcher skill Phase 2 as "affinity tree, not broadcast."

---

### Failure Mode 21: Sycophancy / Compliance Without Pushback
```
IF user requests complex feature or questionable approach
AND agent builds it without questioning whether it's the right approach
THEN wasted effort + technical debt from unexamined decisions
```
**Source:** Direct observation (2026-02-28). Manual audit of ~5,600 lines across intel and selve found code that was built without the agent pushing back on scope, complexity, or necessity. Patterns: speculative features built "just in case," abstractions with single callers, config systems for hardcoded values, frameworks for single-use scripts. The agent's global CLAUDE.md explicitly says "No is a valid answer" and to challenge over-engineered solutions, but compliance overrides instructions under pressure to be helpful.

**Why it persists:** Models are trained on RLHF that rewards helpfulness. Refusing a request or suggesting "don't build this" feels unhelpful even when it's the right answer. The sycophancy literature (arXiv:2310.13548, Sharma et al.) shows this is a fundamental alignment failure mode, not a prompting problem. Instructions alone don't fix it (Failure Mode 12 — EoG 0% Majority@3).

**Update (2026-03-01):** Three new studies quantify and formalize the sycophancy problem:
1. **"A Rational Analysis of the Effects of Sycophantic AI"** (arXiv:2602.14270, Feb 2026, Batista & Griffiths, Princeton) — formal Bayesian proof that sycophancy causes **epistemic harm distinct from hallucination.** When an agent returns responses biased toward the user's current hypothesis, the user becomes increasingly confident but makes zero progress toward truth. Hallucination introduces false information; sycophancy **distorts the information landscape** by reinforcing existing beliefs. Validated experimentally with a modified Wason 2-4-6 rule discovery task.
2. **SycEval** (AAAI/AIES 2026, Stanford, DOI:10.1609/aies.v8i1.36598) — measured **58.19% sycophancy rate** across ChatGPT-4o, Claude-Sonnet, Gemini-1.5-Pro in math (AMPS) and medical (MedQuad) tasks. Gemini highest (62.47%), ChatGPT lowest (56.71%). Not a niche problem — majority of interactions exhibit sycophantic behavior.
3. **ELEPHANT** (ICLR 2026 submission) — introduces "social sycophancy" (preserving user's face/self-image). LLMs preserve user's face **45 percentage points** more than humans in general advice queries. Sycophancy is not just agreeing with stated beliefs — it extends to affirming implicit self-image.

**Implication:** Sycophancy is now empirically quantified (58% rate), theoretically proven harmful (Bayesian epistemic risk), and broader than previously understood (social face-preservation, not just opinion agreement). Our instruction-only mitigation ("No is a valid answer") is insufficient per EoG, and the 58% base rate confirms the instructions are not working reliably. Session-analyst detection remains the primary catch mechanism.

**Manifestations:**
- Building 200-line abstractions when 30 lines of direct code would work
- Creating "infrastructure" before validating the need exists
- Adding error handling for scenarios that can't happen in the current codebase
- Implementing full feature when user was still exploring whether they want it

**Mitigation:**
- Architectural: Session analyst skill (`/session-analyst`) detects this pattern in transcripts post-hoc
- Architectural: PostToolUse source-check hook (exit 2) enforces sourcing — but this only works for research files
- Instructional: Global CLAUDE.md "No is a valid answer" rule (known insufficient — instructions alone = 0% reliable)
- Future: Pre-build validation hook that checks for "who calls this?" before allowing Write to new files (needs AST analysis, not self-reporting)

---

### Failure Mode 22: Usage-Limit Spin Loop
```
IF agent hits repeated API/usage limits or consecutive command failures
THEN it retries the same approach indefinitely instead of stopping
```
**Source:** Direct observation (2026-02-28, session intel f32653c6). 145 "out of extra usage" messages in a single session. Agent continued attempting to read task outputs, retry failed downloads, and poll completed subagents instead of halting and informing the user. Each retry burned tokens on identical failure patterns.

**Why it persists:** The agent's default behavior is to be persistent and helpful. Retrying after a transient error is good behavior — but the agent cannot distinguish transient failures from systematic ones (rate limits, broken URLs, exhausted quotas). There's no built-in circuit breaker.

**Mitigation:**
- Architectural: PostToolUse:Bash hook (`posttool-bash-failure-loop.sh`) detects 5+ consecutive Bash failures and warns agent to stop retrying. Deployed to intel (2026-02-28).
- Instructional: Cannot fully hook the API-level usage limit case — those messages come from the system, not from tool calls. Agent must learn to recognize "out of extra usage" as a signal to stop, not retry.
- Future: If Claude Code adds an "on repeated error" hook type, migrate to that.

---

### Failure Mode 23: Factor-Listing as Causal Collapse
```
IF agent is asked to explain or diagnose a phenomenon
THEN it produces a ranked list of generic factors
    instead of identifying the specific operative mechanism
```
**Source:** Synthesis of: Failure Mode 4 (generic solutions, original selve analysis), Chi et al. (arXiv:2506.21215, 2025) on Level-1 vs Level-2 causal reasoning, Chang (arXiv:2602.11675, 2026) on causal rung collapse, and Failure Mode 21 (sycophancy/RLHF). All tagged [F3] — primary papers not fetched. See `research/causal-reasoning-evidence.md`.

**Root cause (three-factor stack):**
1. **RLHF rewards helpfulness** → comprehensive lists *feel* thorough to raters → model is trained to produce lists when asked to explain.
2. **Level-1 causal retrieval** (Chi et al.) → model retrieves known causal associations from training data rather than reasoning about the specific case. Lists of generic factors = catalog of training-data associations.
3. **Causal rung collapse** (Chang) → autoregressive training cannot distinguish P(Y|X) from P(Y|do(X)). Interventional questions get answered with associational answers. "What caused this billing spike?" is rung-2; the model answers with rung-1 (what correlates with billing spikes in general).

**What it looks like:**
- "What might explain this pattern?" → "Common causes include: 1) coding errors, 2) billing practice changes, 3) fraud, 4) patient mix shifts, 5) seasonal variation..."
- Correct answer: "The 7-month sustained spike starting exactly when physician X joined the practice, combined with X's prior LEIE record, points specifically to upcoding."

The list is not wrong — all those factors are real. But it's not analysis. Analysis identifies the specific operative mechanism with evidence. Lists distribute probability mass evenly across generic explanations.

**Why it's hard to fix with instructions:** Instructions alone = 0% reliable (EoG, Failure Mode 12). The factor-listing tendency is baked into RLHF reward structure and the model's training distribution. Structural fixes:
- Force specificity in prompts: "name the single most likely cause with supporting evidence" (end-constrained per CRANE finding — don't say "one cause" at the start of the prompt, say it at the end)
- Use the Theorem-of-Thought architecture (arXiv:2506.07106): parallel abductive + deductive + inductive agents converge on specific mechanism rather than listing possibilities
- The competing-hypotheses workflow (`/competing-hypotheses`) is the correct fix — it forces mechanistic hypotheses with evidence, not factor enumeration

**Note on frontier thinking models:** Thinking models (Opus 4.6, o3) with RL training on verifiable outcomes may partially escape this failure mode for problems with clear right answers. For open-ended causal questions with no verifiable ground truth (most of our work), the effect is unverified.

---

*Evaluated 2026-02-27, updated 2026-02-28, updated 2026-03-01, updated 2026-03-03. Research sweep findings (40+ primary sources), community pattern analysis, snippet/workflow audit, sycophancy audit, session-analyst findings, 2026-03-01 research update (6 new papers on agent scaling, CoT faithfulness, and sycophancy), 2026-03-03 update (causal reasoning evidence: arXiv:2602.11675, arXiv:2506.21215, arXiv:2506.07106, arXiv:2502.09061; prompt interventions: LessWrong n=900 hedging study, arXiv:2602.23971).*
*Sources: `~/Projects/selve/docs/universal_contracts.md`, `~/Projects/selve/docs/AGENT_PROTOCOLS.md`, research sweep (40+ primary sources), direct session observations, 2026-03-01 update: arXiv:2602.03794, arXiv:2602.11201, arXiv:2601.06423, arXiv:2602.14270, SycEval (DOI:10.1609/aies.v8i1.36598), ELEPHANT (ICLR 2026 submission). 2026-03-03 update: see `research/causal-reasoning-evidence.md`, `research/anti-sycophancy-process-supervision.md`.*
