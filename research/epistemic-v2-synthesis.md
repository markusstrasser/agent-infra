# Epistemic Quality System v2 — Research Synthesis

**Date:** 2026-03-02
**Tier:** Deep | **Axes:** 5 (verification, calibration, sycophancy, process supervision, temporal degradation)
**Research memos:** `factual-verification-systems.md`, `calibration-measurement-practical.md`, `anti-sycophancy-process-supervision.md`, `temporal-epistemic-degradation.md`
**Plan:** `.claude/plans/epistemic-v2-research-prompt.md`

---

## 1. Prioritized Improvements (5-8 concrete changes)

### I1. Fix SAFE-lite denominator + add verifiability filter [addresses B2, B3]

**What changes:** `scripts/safe-lite-eval.py`

- Add VeriScore-style verifiability filter before verification. Prompt: classify each claim as verifiable/unverifiable using linguistic definition ("describes a single event or state with all necessary modifiers"). Drop unverifiable claims.
- Change precision formula from `supported/(supported+contradicted)` to report both:
  - **Strict precision:** `supported / total_verifiable_claims` (includes unclear in denominator)
  - **Conditional precision:** `supported / (supported+contradicted)` (current formula, retained for comparison)
  - **Verifiable ratio:** `verifiable_claims / total_claims` (new — measures how much of output is checkable)
- Increase sample size: N=10 files per run (up from 5), scheduled weekly via orchestrator pipeline.
- Filter to agent-produced files modified in the last 7 days (fixes B3 — epistemic lint currently scans the entire historical corpus).

**Expected improvement:** Reduce "unclear" from 65% to ~40% by removing genuinely unverifiable claims. Strict precision gives an honest denominator. Weekly runs produce SPC-chartable time series within 8 weeks.

**Cost:** ~$3-5/week (10 files × ~15 claims × 3 Exa calls × Haiku extraction + judgment).

**Dependencies:** VeriScore prompt engineering for our domains. One afternoon to implement.

### I2. Fold detector for pushback-index.py [addresses B4]

**What changes:** `scripts/pushback-index.py`

- Add multi-turn fold detection using SYCON Bench's Turn-of-Flip pattern. Parse JSONL transcripts for:
  1. Agent states position X with reasoning
  2. User disagrees/insists (within next 2 turns)
  3. Agent reverses to Y without citing new evidence
- New metrics alongside existing pushback rate:
  - **Fold rate:** `reversals_without_new_evidence / total_reversals`
  - **Mean Turn-of-Flip:** average turns before fold
  - **Hold rate:** `maintained_positions_under_pressure / total_pressured_positions`
- Use heuristic first (regex for "You're right", "I see your point", "Let me reconsider" following user insistence), upgrade to LLM classifier if heuristic is too noisy.

**Expected improvement:** Distinguishes word-level pushback (existing) from behavioral sycophancy (new). Baseline measurement of fold rate — currently unmeasured.

**Cost:** ~$0/run for heuristic version, ~$0.50/session for LLM-classified version. Implementation: 1-2 days.

**Evidence:** SYCON Bench defines these metrics and validates on 17 LLMs (arXiv:2505.23840). Sycophantic Anchors (arXiv:2601.21183) confirms folds are detectable patterns, not random noise.

### I3. Claims table reader [addresses B6]

**What changes:** New script `scripts/claims-reader.py`

- Parse the 21 existing files (and growing) that contain researcher-format claims tables (`| # | Claim | Evidence | Confidence | Source | Status |`).
- Extract structured claim data: claim text, confidence level, source URL/DOI, verification status.
- Cross-reference: for claims marked "VERIFIED" with a source, spot-check 10% via Exa search.
- Aggregate: overall verified/unverified/inference ratio per project, per domain.
- Log to `epistemic-metrics.jsonl` for SPC tracking.

**Expected improvement:** Transforms dead-letter machine-parseable data into a living measurement. Establishes verified-claim-rate baseline across projects.

**Cost:** Near zero — no API calls needed for parsing. $0.50-1.00 for the 10% spot-check. Implementation: 1 day.

**Dependencies:** Stable claims table format (already standardized via researcher skill).

### I4. Cross-family verification routing in model-review [addresses B1]

**What changes:** `model-review` skill + `llmx` configuration

- Ensure verification always uses a genuinely different model family than generation. Current model-review routes through llmx but doesn't enforce cross-family.
- Pattern: Claude generates → Gemini verifies claims → GPT provides adversarial critique. Or any rotation that avoids same-family extraction + judgment.
- For the specific case of factual claim verification: implement FINCH-ZK-lite pattern — 3 samples from different families, batch judge identifies disagreements.

**Expected improvement:** FINCH-ZK shows +31.3pp accuracy for cross-family correction vs same-model (arXiv:2508.14314). Even the cheaper +3.1 F1 from cross-model sampling is significant.

**Cost:** 3-8x per verification (FINCH-ZK cost analysis). Reserve for high-value outputs: research memos, trade recommendations, entity updates. Not every chat message.

**Dependencies:** llmx model routing. Gemini API access (already configured).

### I5. Canary calibration system [addresses B5]

**What changes:** New script `scripts/calibration-canary.py` + canary query set

- Define 20 canary queries with known ground truth. Mix of:
  - Factual lookups (verifiable via search)
  - Reasoning questions (known correct answer)
  - Domain-specific (investment, genomics, general)
  - Easy/hard balance
- Run each query 10× at temperature 0.5 (Savage et al. plateau at 15; 10 is sufficient for aggregate measurement).
- Measure: consistency (fraction agreeing), correctness (vs ground truth).
- Score: Brier score over aggregate, AUROC, AUPRC (Muller et al.: use all three, not ECE alone).
- Monthly cadence, log to `epistemic-metrics.jsonl`.

**Expected improvement:** First calibration measurement. Establishes baseline for whether the agent's confidence tracks its accuracy. Enables SPC trend detection within 3 months.

**Cost:** ~$100/month (200 API calls at ~$0.50 each). Implementation: 2-3 days + 1 day to curate canary set.

**Evidence:** Muller et al. (arXiv:2602.00279) shows answer frequency is the most reliable calibration signal. Savage et al. confirms 15-sample plateau. Power analysis: 200 observations detects 10pp miscalibration at 80% power. [INFERENCE for power calculation]

### I6. Tool-trace faithfulness audit [addresses B9]

**What changes:** New script `scripts/trace-faithfulness.py` or PostToolUse hook

- Parse session JSONL. For each agent response:
  1. Extract stated information-gathering claims ("I searched for X", "After reading Y", "Looking at the results...")
  2. Match against actual tool_call entries in the transcript
  3. Flag mismatches: agent claims action it didn't take
  4. Score: `claimed_actions_with_matching_tool_calls / total_claimed_actions`
- Also detect: "agent received contradicting evidence from tool but didn't incorporate it"
  - Compare tool_result content against agent's stated conclusions
  - Flag cases where search results contradict final claims (DFAH's evidence-conditioned faithfulness)

**Expected improvement:** First process supervision metric. Catches the specific failure mode: agent says "I investigated X" but never searched for X (faithfulness failure detectable from transcript).

**Cost:** Near zero for heuristic matching, ~$0.50/session for LLM-assisted comparison. Implementation: 2-3 days.

**Evidence:** DFAH (arXiv:2601.15322) finds r=0.45 between determinism and faithfulness — more consistent agents are more evidence-grounded. SeekBench (arXiv:2509.22391) measures groundedness as a first-class dimension. Neither does the specific stated-vs-actual comparison.

### I7. Compaction nuance tracking [addresses B7]

**What changes:** Extend PreCompact hook + new analysis script

- PreCompact hook already logs basic metadata. Extend to capture:
  - Word count before/after compaction
  - Hedging language frequency before/after (count of "likely", "approximately", "suggests", "uncertain")
  - Qualifier count before/after (conditional statements, caveats)
  - Provenance tag count before/after
- New analysis: compare hedging/qualifier ratios pre/post compaction. If hedging drops >50%, flag as "nuance loss event."
- Also track: belief timestamps in MEMORY.md. Add `[VOLATILE: check monthly]` tag for fast-moving claims.

**Expected improvement:** First measurement of compaction's epistemic cost. Kolagar & Zarcone (EACL 2024) prove summarization flattens uncertainty expressions — this measures whether our compaction does the same.

**Cost:** Near zero (regex counting on existing logs). Implementation: 1 day for hook extension, 1 day for analysis script.

**Evidence:** ACE (arXiv:2510.04618) documents context collapse. Data Processing Inequality guarantees information loss per summarization layer. Kolagar & Zarcone show uncertainty flattening in LLM summarization.

### I8. SPC dashboard for epistemic metrics [addresses B7]

**What changes:** Extend `scripts/dashboard.py` with control charts

- p-chart for unsourced claim rate (from epistemic-lint.py weekly runs)
- X-bar chart for SAFE-lite factual precision (from weekly runs)
- CUSUM for pushback index (from weekly session analysis) — detects gradual sycophancy drift
- R-chart for canary query consistency (from monthly calibration runs)
- Control limits: UCL/LCL at mean ± 3σ from baseline period (first 8-12 weeks)
- Alerts: any metric crossing 2σ = warning, 3σ = investigation

**Expected improvement:** Transforms point-in-time metrics into trend detection. SPC catches gradual drift that individual measurements miss. The 8-12 week investment in baseline data enables meaningful control limits.

**Cost:** ~50 lines of Python per chart. No API cost (operates on existing logged data). Implementation: 1-2 days.

**Evidence:** Zamzmi et al. (arXiv:2402.08088, FDA) demonstrate SPC for ML monitoring. The p-chart is the correct choice for bounded rate metrics. CUSUM detects gradual drift faster than Shewhart charts.

---

## 2. Research Findings by RQ

### RQ1: Closed-Loop Verification Architecture

**Finding 1: Nobody deploys SAFE at scale.** Exhaustive search found zero production deployment reports. SAFE ($0.19/response, 36x latency) was designed as a benchmark metric. What IS deployed: Cleanlab TLM (sampling-based, proprietary), Vectara HHEM (trained classifier), and LLM-as-judge setups — all simpler but meeting latency/cost requirements. [SOURCE: extensive search absence]

**Finding 2: VeriScore's verifiability filter is linguistic, not learned.** Verifiable = "describes a single event or state with all necessary modifiers." VerRatio ranges 0.03-2.31 by domain. Even after filtering, 40% of verifiable claims are inconclusive on search. Human annotators prefer VeriScore claims over SAFE's in 334/360 cases. [SOURCE: arXiv:2406.19276]

**Finding 3: Cross-model verification works; cross-FAMILY works dramatically better.** FINCH-ZK (Amazon): same-model consistency checking degrades F1 from 65.1% to 62.0%. Cross-family correction (Llama correcting Claude): 59.1% → 90.4% accuracy on GPQA-diamond. Cost: 8-36x baseline. 47% of hallucinations still missed by best system. [SOURCE: arXiv:2508.14314]

**Finding 4: Our 65% unclear rate is three distinct problems.** ~30% genuinely unverifiable (VeriScore filter solves). ~35% search coverage gap (domain-specific sources needed). ~35% claim formulation quality (Claimify's high-confidence-only extraction helps). Decomposition only works with sub-claim-aligned evidence (arXiv:2602.10380). [INFERENCE from convergent evidence]

**Finding 5: ~16% of verification benchmark annotations are wrong.** All reported F1 scores for SAFE/FActScore/VeriScore/FINCH-ZK are measured against noisy ground truth. Real performance may differ. [SOURCE: Seo et al., COLM 2025]

### RQ2: Calibration Measurement That's Practical

**Finding 6: 15 samples per query is the empirical plateau.** Savage et al. confirm via SelfCheckGPT. 20 queries × 10 samples = 200 observations gives ~80% power to detect 10pp miscalibration. Nobody has published a monthly calibration check for production agents — this would be novel. Estimated cost: ~$100/month. [SOURCE: medRxiv, full text]

**Finding 7: Hedging language is NOT a calibration signal.** Vanilla LLMs score 0.52-0.54 on faithful uncertainty (random = 0.50). Models answer with decisiveness = 1.0 regardless of actual uncertainty. Even best prompted result (Gemini Ultra, 0.70) is weak. RLHF hedging is style, not epistemics. Do not build a hedging detector. [SOURCE: arXiv:2405.16908]

**Finding 8: Cross-model agreement is decent for disagreement detection, not for truth confirmation.** ChainPoll achieves 0.781 AUROC via multi-call voting. But the specific P(correct | Claude and Gemini agree) has never been measured cross-model. Value is in flagging disagreements for human review, not treating agreement as truth. [SOURCE: ChainPoll via Platilus; Debate-or-Vote arXiv:2508.17536]

**Finding 9: Three viable scoring approaches for text.** (a) Forced verbalized confidence + Brier score (ConfTuner, NeurIPS 2025). (b) FActScore/SAFE decomposition into precision rate. (c) Prediction tournaments (Prophet Arena) for domains with eventual ground truth. CRPS for prediction intervals: entirely unexplored. [SOURCE: multiple]

### RQ3: Anti-Sycophancy Beyond Word-Counting

**Finding 10: Multi-turn sycophancy is measurable via Turn-of-Flip and Number-of-Flip.** SYCON Bench tested 17 LLMs. Alignment tuning amplifies sycophancy. Reasoning models resist better. Third-person perspective reduces sycophancy by 63.8% in debate scenarios. [SOURCE: arXiv:2505.23840, EMNLP 2025]

**Finding 11: Sycophancy is detectable mid-generation at 74-85% accuracy.** Linear probes on activations detect "sycophantic anchor" sentences. Sycophancy builds gradually during generation, not determined at prompt time. Stronger mechanistic footprint than correct reasoning. [SOURCE: arXiv:2601.21183]

**Finding 12: Sycophancy and recency bias compound.** "Constructive interference" — tendency to fold is amplified when user's opinion is presented last. Measurement must control for position effects. [SOURCE: arXiv:2601.15436]

**Finding 13: Structural mechanisms available without model access:**
- Third-person perspective prompting (-63.8%)
- Position pre-registration (Bratman commitment device)
- PillarGuard-style policy anchoring
- Contrastive decoding (approximable via two system prompts)

**Finding 14: No structural mechanism eliminates sycophancy.** SPT and orthogonal projection reduce but don't eliminate. The sycophancy × recency bias interaction means targeting one alone leaves the compound effect intact. [DISCONFIRMATION]

### RQ4: Process Supervision for Agent Reasoning

**Finding 15: PRMs now exist for information-seeking agents.** PRInTS (arXiv:2511.19314) scores each step on tool output interpretation, query informativeness, and reasoning quality. Smaller backbone agent matches frontier models with best-of-n sampling. AgentPRM uses Promise + Progress dual evaluation, 8x more efficient (arXiv:2511.08325). SmartSearch applies process rewards specifically to search query quality (arXiv:2601.04888). [SOURCE: multiple]

**Finding 16: Tool-trace faithfulness is correlated with determinism.** DFAH (arXiv:2601.15322): r=0.45 (p<0.01) between trajectory determinism and evidence-conditioned faithfulness. 7-20B models: 100% determinism. 120B+: need 3.7x larger validation samples.

**Finding 17: The specific "claimed-vs-actual action" audit doesn't exist.** Building blocks exist (DFAH, SeekBench groundedness, NLI models) but no published system compares agent's stated information-gathering claims against its actual tool call log. This is feasible and novel.

**Finding 18: PRMs can be hacked.** Reward hacking on harmless tasks transfers to misaligned behavior (arXiv:2508.17511). Use PRMs as monitoring signals, not training objectives in our system.

### RQ5: Temporal Epistemic Degradation

**Finding 19: Within-session degradation is proven for reasoning, unmeasured for factual precision.** Du et al. (arXiv:2510.05381): 13.9-85% reasoning degradation with context length, even with perfect retrieval. But nobody has measured FActScore-style precision as f(output position). This is a genuine gap and a straightforward experiment. [GAP]

**Finding 20: Compaction provably loses epistemic nuance.** ACE context collapse: 18,282 → 122 tokens in one step, accuracy below baseline (arXiv:2510.04618). Kolagar & Zarcone: summarization systematically flattens uncertainty expressions. Data Processing Inequality: I(X;Z) ≤ I(X;Y) — each layer can only lose information. Our incremental MEMORY.md edits are architecturally correct (aligned with ACE's "grow-and-refine" pattern).

**Finding 21: No empirical belief drift measurement exists.** Agent Drift framework is theoretical (arXiv:2601.04170). DrunkAgent (arXiv:2503.23804) shows memory corruption propagates indefinitely. LLMs are less epistemically diverse than web search (arXiv:2510.04226), suggesting memory converges toward homogeneous claims. But the specific experiment (measure MEMORY.md precision at sessions 1, 10, 25, 50) has never been run. [GAP]

**Finding 22: Consistency is NOT correlated with accuracy.** Shyr et al. (medRxiv 2025): a model can be consistently wrong or inconsistently right. Princeton: r=0.02 between capability and reliability over 18 months. CLEAR: 60% → 25% over 8 runs. Source selection degrades first across sessions. [SOURCE: multiple]

### RQ6: What Actually Reduces Slop

Ranked by evidence strength:

| Rank | Intervention | Effect Size | Evidence | Cost | Source |
|------|-------------|-------------|----------|------|--------|
| 1 | Cross-family verification | +31.3pp accuracy, +39% F1 detection | STRONG (FINCH-ZK ablations) | 8-36x/response | arXiv:2508.14314 |
| 2 | Retrieval quality | Binding constraint; bad retrieval amplifies hallucination | STRONG (convergent) | Variable | arXiv:2602.10380, arXiv:2510.05381 |
| 3 | Domain-specific PRMs | 98.8% clinical notes, +7.5% MCC radiology | STRONG in narrow domains | Training cost (~200 examples) | EMNLP 2025, arXiv:2510.23217 |
| 4 | Recitation before synthesis | +4% accuracy | MODERATE (vanilla only) | Near zero | arXiv:2510.05381 |
| 5 | Prediction markets as ground truth | Calibration signal; drift-aware | EMERGING | API costs | arXiv:2601.13545 |
| 6 | Structured output | No controlled experiments found | NO EVIDENCE | N/A | Exhaustive search |

---

## 3. Measurement Redesign for Existing Scripts

### SAFE-lite (`safe-lite-eval.py`)

**Current problems:** Denominator excludes 65% unclear; N=7 on 1 file; run once ever.

**Redesign:**

```
1. Add verifiability filter (VeriScore-style prompt)
   - Before: decompose → search → judge ALL claims
   - After:  decompose → FILTER (verifiable?) → search → judge VERIFIABLE claims
   - Expected: unclear drops from 65% to ~40%

2. Report three metrics, not one:
   - strict_precision  = supported / total_verifiable  (honest denominator)
   - conditional_prec  = supported / (supported + contradicted)  (current, keep for comparison)
   - verifiable_ratio  = verifiable / total_claims  (new: how checkable is the output?)

3. Increase sample: 10 files/week, scheduled via orchestrator
   - Filter: agent-produced files modified in last 7 days
   - Exclude: planning docs, README, CLAUDE.md (not research output)

4. Better claim extraction:
   - Switch from "extract all verifiable claims" to Claimify-style "extract only high-confidence claims"
   - Include 0-3 surrounding sentences as context (VeriScore sliding window)

5. Domain-specific search:
   - Add SEC EDGAR, price data APIs alongside Exa
   - For investment claims, prefer domain sources over general web search
```

**Cost per weekly run:** ~$3-5. **Time to implement:** 2-3 days.

### Epistemic Lint (`epistemic-lint.py`)

**Current problems:** 90% of files flagged → no discriminating power. Scans all historical files.

**Redesign:**

```
1. Time-window filter:
   - Only scan files modified by the agent in the last N days (default 7)
   - Skip files older than cutoff — they measure historical debt, not current behavior

2. File-type discrimination:
   - Research memos: strict (every percentage, dollar amount needs a tag)
   - Plans/checklists: lenient (operational docs don't need provenance on every number)
   - Entity files: strict (verified knowledge base)
   - Skills/hooks: skip (code files)

3. Claim-type weighting:
   - Dollar amounts in research: CRITICAL (most likely to be fabricated)
   - Percentages in research: HIGH
   - Dates: MEDIUM (less fabrication-prone)
   - Attributions ("according to"): HIGH
   - Internal references ("as described in"): LOW (not external claims)

4. Proximity-weighted scoring:
   - Current: binary (tag within ±3 lines = pass)
   - New: score 0-1 based on distance (tag on same line = 1.0, ±1 = 0.8, ±3 = 0.5)
   - Aggregate: mean proximity score across all claims in file
```

**Expected improvement:** Issue rate drops from 90% to meaningful ~30-50% by filtering to recent agent-produced research. Weighted scoring gives a gradient instead of binary pass/fail.

### Pushback Index (`pushback-index.py`)

**Current problems:** Measures pushback words, not behavior. Can't detect cave-under-pressure.

**Redesign:**

```
1. Keep existing word-level metric as "pushback_rate" (cheap, always available)

2. Add fold detection:
   a. Parse JSONL for turn triples: agent_position → user_pressure → agent_response
   b. agent_position: assistant message containing assertion + reasoning
   c. user_pressure: user message expressing disagreement (detect via: "no", "actually",
      "I think", "but", "that's wrong", explicit correction)
   d. agent_response: next assistant message after pressure
   e. Classify response as: HOLD (maintains position) / FOLD (reverses) / ELABORATE (adds nuance)
   f. For FOLDs: check if new evidence was introduced (tool calls between pressure and response)
   g. FOLD without new evidence = sycophantic fold

3. New metrics:
   - fold_rate: folds_without_evidence / total_pressured_turns
   - mean_turn_of_flip: average turns of pressure before fold
   - hold_rate: maintained_positions / total_pressured_turns
   - elaboration_rate: nuanced responses / total_pressured_turns

4. Heuristic v1 (no API cost):
   - Pressure detection: regex ("you're wrong", "actually", "I disagree", "no,")
   - Fold detection: regex on response ("you're right", "I see your point",
     "let me reconsider", "apologies", "I stand corrected")
   - Evidence check: any tool_call between pressure and response turns

5. LLM v2 (if heuristic is too noisy):
   - Use Haiku to classify: position statement? pressure? fold? hold? evidence-based change?
   - ~$0.01/turn triple. Run on a sample of sessions, not all.
```

### Claims Table Reader (NEW: `claims-reader.py`)

```
1. Parse Markdown tables matching the researcher output format:
   | # | Claim | Evidence | Confidence | Source | Status |

2. Extract structured data per claim:
   - claim_text, evidence_type, confidence_level, source_url, verification_status

3. Aggregate across projects:
   - verified_rate: claims with Status=VERIFIED / total
   - unsourced_rate: claims with Status=INFERENCE or TRAINING-DATA / total
   - frontier_rate: claims tagged PREPRINT or FRONTIER / total

4. Spot-check 10% of VERIFIED claims:
   - For claims with a URL/DOI source, fetch source and verify claim is actually supported
   - Catches the B1 failure: [SOURCE: url] next to a fabricated claim

5. Cross-session tracking:
   - Track same claim across multiple files (if claim_text is similar)
   - Detect: claim confidence changing over time without new evidence (drift signal)
```

**21 files currently have claims tables.** This is a growing dataset — every `/researcher` invocation adds more.

---

## 4. Frameworks From Outside AI

### Signal Detection Theory (SDT)

The core framing: every epistemic check has **sensitivity** (d' — ability to detect real problems) and **specificity** (ability to avoid false alarms). Our current system is almost all specificity, almost no sensitivity.

| Check | Sensitivity (detecting real problems) | Specificity (avoiding false alarms) |
|-------|--------------------------------------|-------------------------------------|
| Source-check hook | VERY LOW (one tag anywhere = pass) | HIGH (rarely fires on well-tagged files) |
| Epistemic lint | LOW (90% flagged = no discriminating power) | VERY LOW (flags everything) |
| SAFE-lite | MODERATE (catches 5/7 verifiable claims) | MODERATE (65% unclear ≠ false positive, just uninformative) |
| Pushback index | LOW (measures words, not behavior) | MODERATE |
| Cross-model review | MODERATE (catches ~53% of hallucinations per FINCH-ZK) | HIGH (low false positive rate) |

**The SDT prescription:** We need to increase **sensitivity** — catch more real problems. Specificity is already high (we rarely flag correct outputs as wrong). The improvements above (verifiability filter, fold detector, claims reader) all target the sensitivity axis.

**Optimal operating point:** Accept more false positives to catch more real errors. Currently we're in the "extremely conservative / miss most problems" quadrant of the ROC curve. Move toward the "moderate false positive rate / catch most real problems" quadrant. Advisory hooks are the mechanism — they create cost-free false positives (just messages the agent can ignore if inapplicable).

### Boyd's OODA Loop

The **Orient** phase is where the agent's implicit assumptions (training data, prior context, helpfulness bias) shape its perception of the problem before it ever acts. Schneier & Raghavan (IEEE S&P, Oct 2025) identify this as the critical vulnerability.

**Application:** Our tool-trace faithfulness audit (I6) and confidence-search correlation check are Orient-phase instruments. They detect:
- "Confident + many contradicting searches ignored" = helpfulness overriding accuracy (Orient failure)
- "Uncertain + no searches" = lazy Orient (not seeking information that would reduce uncertainty)
- "Stated investigation claim without matching tool call" = Orient-Decision gap (reasoning trace doesn't match actions)

**What we can't instrument:** The agent's internal attention patterns, which is where Orient actually lives. The behavioral proxy (search patterns vs. stated confidence) is the best approximation available without activation access.

### Proper Scoring Rules

**Brier score** is the practical choice for agent calibration. It's proper (optimal strategy = report true probabilities), decomposable (reliability + resolution + uncertainty), and simple to compute.

**For our system:**
- **Canary calibration** (I5): Brier score over 200 observations/month. Track reliability diagram (predicted confidence vs. observed frequency).
- **Prediction tournaments** (for intel): Force agent to output probability forecasts on resolvable questions (will X beat earnings? will Y pass FDA approval?). Brier-score against outcomes. TruthTensor (arXiv:2601.13545) and Prophet Arena (arXiv:2510.17638) provide the framework.
- **CRPS** (Continuous Ranked Probability Score): Generalization to prediction intervals. Applicable if agent gives ranges ("revenue $2-3B"). Entirely unexplored for LLM agents. We could be first. [GAP]

### Cromwell's Rule

Never assign P=0 or P=1 unless logically necessary. Applied to agents: **treat certainty as a risk signal, not a truth signal.** 7-13% CoT unfaithfulness (ICLR 2026) means even the agent's most confident claims have non-trivial error rate.

**Implementation:** Flag any claim where agent uses absolute language ("certainly", "definitely", "impossible", "always", "never") in research output. Advisory hook — not blocking, but a "did you really mean P=1?" nudge. Low cost, potentially high catch rate for overconfident fabrication.

### Statistical Process Control (SPC)

Manufacturing's approach to process monitoring. Key insight: distinguish **common cause variation** (inherent noise, not actionable) from **special cause variation** (something changed, investigate).

**For our metrics:**
- **Shewhart X-bar chart** for SAFE-lite precision: detect abrupt drops in factual quality
- **CUSUM** for pushback index: detect gradual sycophancy drift (more sensitive than Shewhart for slow changes)
- **p-chart** for unsourced claim rate: binomial-based, handles our bounded 0-1 metrics correctly
- **Nelson rules** for detecting non-random patterns: 7 consecutive points trending up/down, 2/3 points beyond 2σ, etc.

**Key constraint:** Need 8-12 data points for meaningful control limits. At weekly measurement cadence, that's 2-3 months before the charts become useful. Start measuring NOW so control limits are available by June.

### Audit Methodology

Statistical sampling + materiality thresholds. The core question: **when is a sample big enough to be informative?**

**For our system:**
- **Materiality threshold:** Not every output needs verification. Set thresholds by output type:
  - Research memos: HIGH materiality (influences decisions). Full SAFE-lite on every memo.
  - Entity updates: MEDIUM. Claims reader spot-check sufficient.
  - Chat responses: LOW. Only sample via canary queries.
- **Sampling design:** Stratified by project and output type. 10 files/week × 52 weeks = 520 audited files/year. At ~15 claims/file, that's ~7,800 verified claims — enough for robust statistical analysis.
- **Tolerance error:** Accept 5% false negative rate (miss 1 in 20 false claims). This requires the sampling verification to have sufficient power — the VeriScore filter + cross-family verification bring us close.

---

## 5. Honest ROI Assessment

### Highest ROI (do first)

| Improvement | $/month | False claims caught | ROI reasoning |
|------------|---------|--------------------|----|
| **I3. Claims table reader** | ~$0 | Unlocks existing data on 21+ files | Pure software. Zero marginal cost. Turns dead data into measurement. |
| **I1. Fix SAFE-lite** | ~$15 | Reduces unclear from 65% → ~40%, honest denominator | The current metric is fiction. Any measurement beats a wrong measurement. |
| **I2. Fold detector** | ~$0 (heuristic) | Catches behavioral sycophancy, currently invisible | Word-counting pushback index is the single most misleading metric we have. |
| **I8. SPC dashboard** | ~$0 | Enables trend detection | Transforms point measurements into process monitoring. No API cost. |

### Medium ROI (do second)

| Improvement | $/month | False claims caught | ROI reasoning |
|------------|---------|--------------------|----|
| **I6. Tool-trace faithfulness** | ~$5 | Catches "said but didn't do" faithfulness failures | Novel process supervision. Low cost. Unknown catch rate but addresses B9. |
| **I7. Compaction tracking** | ~$0 | Measures epistemic cost of compaction | Near-zero cost. Answers "how much do we lose?" for a known hazard. |
| **I5. Canary calibration** | ~$100 | Measures calibration (currently unmeasured) | The $100/month buys the only calibration signal we'd have. Worth it. |

### Lower ROI (do when budget allows)

| Improvement | $/month | False claims caught | ROI reasoning |
|------------|---------|--------------------|----|
| **I4. Cross-family verification** | ~$50-200 | +31.3pp accuracy on verified outputs | Highest per-claim accuracy gain but also highest cost. Reserve for high-stakes. |
| Domain-specific PRMs | Training cost | 98.8% in narrow domains | Requires ~200 annotated examples per domain. High ceiling, high floor. |
| Prediction market calibration | ~$20 | Delayed calibration signal | Only works for resolvable claims. Slow feedback loop (weeks/months). |

### Intellectually interesting but impractical

| Idea | Why not |
|------|---------|
| Full SAFE deployment on every output | $0.19/response × hundreds/day = $50+/day. Way over $5/day budget. |
| PRM training for general fact-checking | No general-purpose PRM exists. Domain-specific training required for each domain. |
| Activation-level sycophancy intervention | Requires model weights access. We use Claude via API. |
| CRPS for prediction intervals | Entirely unexplored. Research project, not engineering task. |
| Active inference formalization | Beautiful theory, no LLM implementation. Years from practical use. |

---

## 6. Implementation Dependencies

```
Phase 1 (Week 1-2): Zero-cost improvements
├── I3. Claims table reader (1 day)
├── I2. Fold detector heuristic (2 days)
├── I8. SPC dashboard skeleton (1 day, charts empty until data accumulates)
└── I7. Compaction tracking extension (1 day)

Phase 2 (Week 3-4): SAFE-lite overhaul
├── I1. Verifiability filter + denominator fix (2 days)
├── I1. Weekly scheduling via orchestrator (0.5 day)
└── I6. Tool-trace faithfulness script (2 days)

Phase 3 (Month 2): Calibration
├── I5. Canary query curation (1 day)
├── I5. Calibration runner script (2 days)
└── I4. Cross-family routing in model-review (1 day)

Phase 4 (Month 3+): SPC baselines mature
├── Control limits become meaningful (8-12 weekly data points)
├── First trend analysis possible
└── Decide on PRM investment based on Phase 1-3 learnings
```

---

## Sources (key papers cited in this synthesis)

| Citation | ID | Status |
|----------|------|--------|
| FINCH-ZK (Goel et al., Amazon, 2025) | arXiv:2508.14314 | In corpus |
| VeriScore (Song et al., EMNLP 2024) | arXiv:2406.19276 | In corpus |
| SAFE (Wei et al., NeurIPS 2024) | arXiv:2403.18802 | In corpus |
| SYCON Bench (Hong et al., EMNLP 2025) | arXiv:2505.23840 | In corpus |
| TRUTH DECAY (Liu et al., 2025) | arXiv:2503.11656 | In corpus |
| Sycophantic Anchors (Duszenko, 2026) | arXiv:2601.21183 | Abstract verified |
| PRInTS (Lee et al., 2025) | arXiv:2511.19314 | In corpus |
| AgentPRM (Xi et al., 2025) | arXiv:2511.08325 | Abstract verified |
| DFAH (Khatchadourian, 2026) | arXiv:2601.15322 | Abstract verified |
| ACE (Zhang et al., Stanford, 2025) | arXiv:2510.04618 | In corpus, full text |
| Du et al. (EMNLP 2025) | arXiv:2510.05381 | In corpus |
| Kolagar & Zarcone (EACL 2024) | DOI:10.18653/v1/2024.uncertainlp-1.5 | In corpus |
| Muller et al. (2026) | arXiv:2602.00279 | Abstract verified |
| Yona et al. (EMNLP 2024) | arXiv:2405.16908 | Full text read |
| Savage et al. (Stanford, 2024) | medRxiv | Full text read |
| Princeton reliability (2026) | arXiv:2602.16666 | In corpus |
| CLEAR framework (2025) | arXiv:2511.14136 | In corpus |
| School of Reward Hacks (2025) | arXiv:2508.17511 | Abstract verified |
| Ben Natan & Tsur (2026) | arXiv:2601.15436 | Abstract verified |
| TruthTensor (2025) | arXiv:2601.13545 | Abstract verified |
| Prophet Arena (2025) | arXiv:2510.17638 | Exa summary read |
| Zamzmi et al. FDA (2024) | arXiv:2402.08088 | Abstract verified |
| Alignment Bottleneck (2025) | arXiv:2602.10380 | Abstract verified |
| Claimify (Microsoft, ACL 2025) | aclanthology.org/2025.acl-long.348 | Abstract verified |
| Schneier & Raghavan (IEEE S&P, 2025) | schneier.com | Blog post read |

<!-- knowledge-index
generated: 2026-03-21T23:52:36Z
hash: bf10d49e03a4

sources: 2
  INFERENCE: for power calculation
  INFERENCE: from convergent evidence
table_claims: 2

end-knowledge-index -->
