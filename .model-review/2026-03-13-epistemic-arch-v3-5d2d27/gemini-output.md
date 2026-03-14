Here is a review of your Epistemic Architecture v3 plan, evaluated against your constraints (1 developer, $25/day, personal project) and your core constitutional principle (Maximize rate agents become autonomous via declining supervision).

### ## 1. Strengths and Weaknesses

**Strengths:**
*   **High Pragmatism:** Using project-path deterministic routing instead of an LLM classifier is brilliant for a solo developer. It saves latency, avoids a failure point, and costs $0.
*   **Strong Epistemic Hygiene:** Acknowledging that "bad scaffolding is worse than none" (Girolli 2026) and treating confirmation bias as the boss-level threat shows a deep understanding of agentic failure modes.
*   **Architecture over Instructions:** You are actively moving away from bloated system prompts and toward structural forcing. 
*   **Sunk-cost Avoidance:** Choosing *not* to build a monolithic bias detection system and focusing only on the highest-damage biases per domain.

**Weaknesses:**
*   **Scope Bloat for a Solo Dev:** 13 items across 3 layers in 3 months is enterprise-scale ambition. Building the scaffolding for Scite APIs, Jaccard distance calculators, and Gini coefficient tracking will likely cannibalize your time to actually *use* the agents.
*   **Missing the "Autonomy Ratchet":** Your constitution demands *declining supervision*. Your plan measures errors, but it lacks a mechanical link where a good score automatically reduces human-in-the-loop (HITL) gating. 
*   **API Cost/Rate-Limit Vulnerability:** Integrating external tools like Scite and Kalshi, plus running multiple cross-model evaluations, can easily shatter a $25/day budget if an agent gets stuck in a retry-loop.
*   **Trajectory Calibration (ACC-lite) Delusion:** You cannot extract 48 meaningful trajectory features in Month 3 if you aren't logging the exact right data exhaust in Month 1. Without log-probs, behavioral proxy logging is your only hope, and it isn't in Phase 1.

### ## 2. What Was Missed

*   **Data Exhaust Standardization:** To answer Q1 (trajectory calibration without log-probs), you need behavioral proxies: *tool-call churn rate, token backspaces (if streaming is intercepted), pause latency, edit distance between draft and final output, and self-correction frequency*. If Phase 1 doesn't implement a standardized `trace_logger.py` to capture these exact behavioral features in your JSONL, Phase 3 is dead on arrival.
*   **The "Fail Open" Mechanism:** You stated "fail open" as a rule, but didn't specify the architecture for it. If the Scite API times out, or the Kalshi API changes its endpoints, does your agent crash? You need a universal `@fail_open(fallback_value=None)` decorator for all Layer 1 and 2 measurement hooks.
*   **Budgeting for "Anonymized Model-Review":** Doing LLM-as-a-judge on long transcripts to evaluate disconfirmation (Phase 1, Item 4) is highly token-intensive. At $25/day, analyzing a heavy autoresearch trajectory with GPT-4o or Claude 3.5 Sonnet will eat your budget fast. You need a fast, cheap router model (e.g., Haiku or Gemini Flash) doing the linting.
*   **Supervision Decay Logic:** You missed defining the thresholds. *When* does an agent earn the right to execute a trade without a human checking the thesis challenge metric? 

### ## 3. Better Approaches

*   **Consolidate Layer 1 (Domain-Specific):** Instead of writing custom logic for Trading, Research, and Engineering, build ONE universal "Disconfirmation Scaffold" that injects different prompts based on the project path.
    *   *Path = /trading*: Inject "Find 3 data points contradicting this ticker's thesis."
    *   *Path = /research*: Inject "Find 2 high-impact papers refuting this mechanism."
    *   *Path = /engineering*: Inject "Identify 2 distributional shifts that would break this architecture."
*   **Cheap Consensus Hallucination Detection (Alternative to Scite):** Before paying for Scite or wrestling with its API limits, test a structural prompting approach: Force the agent to query PubMed/ArXiv for `"exact claim" AND (refutes OR contradicts OR fails)` and count the hits. If hits > 0, flag for review. This uses your existing web-search tool, costing nothing extra.
*   **Goodhart Detection via Simple Ratios:** Don't wait for Month 3 to do n≥8 metric correlation divergence. Just track `Token Length : Reward Score` or `Tool Calls : Confidence Level`. If confidence goes up while the number of tool calls drops to zero, the agent is Goodharting its own certainty.
*   **"Show Your Work" Trajectories:** To substitute for ACC paper log-probs, enforce `<draft>`, `<critique>`, and `<final>` XML tags in the output. The token edit distance between `<draft>` and `<final>` is your strongest cheap proxy for epistemic calibration.

### ## 4. Top 5 Priority Changes (with testable criteria)

**1. Move Data Exhaust Logging to Phase 1 (Week 1)**
*   *Why:* You cannot do ACC-lite trajectory features in Month 3 without a backlog of rich, structured traces.
*   *Testable Criterion:* Every agent session outputs a `.jsonl` file containing: timestamp, tool-call count, `<draft>` to `<final>` edit distance, and self-correction flags.

**2. Build the "Autonomy Ratchet" into Layer 2**
*   *Why:* To satisfy your core constitutional principle. Measurement without a mechanical reward (less supervision) is just dashboard vanity.
*   *Testable Criterion:* Script reads the last 10 trajectory calibrations. If `ECE < 0.1` and `missed_negative_rate < 5%`, the `REQUIRE_HUMAN_APPROVAL` boolean for that domain automatically flips to `False`.

**3. Build a `@fail_open` Decorator for All Measurement Hooks**
*   *Why:* API fragility (Kalshi, Scite, cross-model calls) will stall your autonomous agent.
*   *Testable Criterion:* Wrap the Scite and Kalshi checks. Disconnect your internet, run the agent. The agent must proceed to completion, logging `[MEASUREMENT_FAILED_OPEN]` rather than throwing a Python traceback.

**4. Prune Phase 2 to ONE Domain First**
*   *Why:* 1 developer doing Trading, Research, and Engineering simultaneously is a trap. 
*   *Testable Criterion:* Pause Research and Engineering. Build the thesis challenge metric for Trading. Run 20 autonomous sessions. Prove the metric actually correlates with epistemic success before building the others.

**5. Swap Anonymized Reviews for Structural Proxies**
*   *Why:* LLMs reviewing LLMs (Item 4) is expensive and often degrades into sycophancy, violating Principle 3. 
*   *Testable Criterion:* Replace prompt-based review with deterministic checks (e.g., Did the agent query a contrasting API? Did it extract a negative result? Yes/No Boolean based on tool-use logs, costing $0).

### ## 5. Constitutional Alignment

*   **Maximize autonomy / declining supervision:** *Failed.* The plan outlines how to *measure* autonomy, but lacks the mechanical code to actually *decline supervision*. Implementing the "Autonomy Ratchet" (Priority #2) fixes this.
*   **Architecture over instructions:** *Passed.* Project-path routing, metric correlation tracking, and fold-detectors are excellent architectural solutions.
*   **Measure before enforcing:** *Passed.* The phased rollout perfectly aligns with this.
*   **Fail open:** *Incomplete.* Stated in the prompt, but not embedded in the Phase 1/2 implementation steps. Priority #3 fixes this.
*   **Recurring patterns (10+) become architecture:** *Passed.* Moving from 25 memos to 3 layers of code is the exact realization of this rule. 

### ## 6. Blind Spots In My Own Analysis

*   **The ACC/Girolli 2026 Assumption:** You cited papers/metrics from late 2025/2026. I am assuming these feature sets (like the 48 trajectory features) rely heavily on internal token probabilities or massive ensemble techniques that frontier labs use, which are hostile to solo developers. If they are purely text-based (like pause tokens in reasoning models), my skepticism about Q1 might be overly pessimistic.
*   **Your existing Layer 0:** I am assuming your current Layer 0 (SAFE-lite, pushback-index) is efficient. If it is already consuming 80% of your $25/day budget, adding Layer 1 and Scite will break your pipeline immediately.
*   **Scite API costs:** I am evaluating this as an external commercial API. If you have academic/institutional access, my warnings about the budget constraints for Phase 1/Item 1 are moot. 
*   **The efficacy of "Thesis Challenge":** I am assuming a structural "disconfirmation prompt" will yield meaningful thesis challenges. However, frontier models are highly susceptible to "lazy disconfirmation" (finding weak strawman arguments to easily knock down). True thesis challenge might require an entirely separate, adversarial agent instance, which doubles compute costs.
