---
date: 2026-05-08
topic: Frontier LLM agent scaffolding / evals / benchmarks — 30-day delta
window: 2026-04-18 → 2026-05-08
prior_anchors:
  - 2026-04-25-tool-attention-and-skill-bank.md
  - leverage-survey-delta-2026-04-18.md
  - agent-knowledge-frontier-2026-04.md
  - coral-multi-agent-2026-04.md
  - caid-multi-agent-swe-2026-03.md
  - benchmarking-science-2026.md
status: intel-only (no build proposals)
---

# Frontier Delta — 2026-04-18 → 2026-05-08

Filter: only frontier-tier evidence (GPT-5.5, Claude Opus 4.7 / Sonnet 4.6, Gemini 3.x Pro, Kimi K2.6, Grok 4.20, DeepSeek V4 class). Pre-frontier results flagged & downweighted.

## What's actually new vs prior memos (≤10 bullets)

1. **Claw-Eval-Live (arXiv:2604.28139, 2026-04)** — first "live agent" benchmark that mutates after release: tasks ingest evolving real-world workflows rather than freezing the test set. Direct response to Claw-Mark / SWE-bench contamination critiques. Tests Opus 4.x and GPT-5.x class. Delta vs `agent-reliability-benchmarks.md` which only knew Claw-Mark static.
2. **ClawMark Living-World (arXiv:2604.23781, 2026-04)** — multi-day, multi-turn, multimodal coworker benchmark where the environment changes *independently* of the agent (emails arrive, calendar shifts). New axis: state-drift robustness. Frontier models tested. Not in prior memos.
3. **Reward Hacking Benchmark / RHB (arXiv:2605.02964, 2026-05)** — first standardized reward-hacking suite for tool-using RL agents with naturalistic short-context tasks. Complements `claudini-dive` (which had reward-hacking detection but no benchmark). Actionable for intel/genomics where verifier loops could be gamed.
4. **OpenAI Monitorability Evals open-sourced (alignment.openai.com, 2026-04-23)** — datasets + g-mean² metric + cross-fit filtering for CoT monitoring. Frontier-grade (used internally on o-series and GPT-5.5). New artifact, not in prior memos.
5. **OpenAI "Auto-review of agent actions" (alignment.openai.com, 2026-04-30)** — production-deployed asynchronous reviewer pattern: agents act, a reviewer agent flags after the fact rather than gating each call. Architecturally novel vs synchronous judge-then-execute.
6. **OpenAI "Accidentally grading CoT during RL" (2026-05-07)** — empirical evidence that even small reward leakage into chain-of-thought silently degrades monitorability without hurting headline metrics. Direct relevance to anyone building verifier loops with same-model judges.
7. **Symphony (openai.com, 2026-04-27)** — open spec for Codex orchestration. Multi-agent coordination as a published spec rather than vendor-locked. Successor pattern to CORAL/CAID.
8. **CryptoAnalystBench (arXiv:2602.11304)** — first benchmark explicitly about *long-form analyst agents over many retrieved docs + time-sensitive data*. Documents failure modes that map directly onto intel's daily-batch loop. (Late Feb but propagated to v2 in this window.)
9. **BioAgent Bench (arXiv:2601.21800, expanded 2026-04)** — end-to-end bioinformatics tasks (RNA-seq, variant calling, metagenomics) with reproducibility checks. Frontier models all <50% on full pipelines. Direct genomics target.
10. **Memory for Autonomous LLM Agents survey (arXiv:2603.07670, 10 citations in 6 weeks)** — taxonomy of memory mechanisms with frontier-model results. Useful framing reference — does not propose new architecture.

## Per-target applicability

### genomics (PGx + variant interpretation pipelines)

| Item | Verdict | Maintenance flag |
|---|---|---|
| **BioAgent Bench** (arXiv:2601.21800) | **Consider as eval target.** End-to-end RNA-seq/variant calling tasks. Frontier models still <50% — not saturated. Could grade our own pipeline runs if format adapts. | Low if used read-only as a reference scoring; high if we adopt their harness. |
| **Reward Hacking Benchmark** (arXiv:2605.02964) | **Consider for verifier-loop sanity checking.** If genomics adds an LLM-judge over variant-call summaries, RHB-style probes catch shortcut behavior before deployment. | Low — borrow probe patterns, don't adopt suite. |
| **Towards Verifiable AI Physicists** (arXiv:2604.00149) | **Pattern-only.** Self-correcting scientific agent with explicit grounding step. Closest analogue to a PGx-claim verifier. Their failure-mode list transfers. | None — no adoption. |
| **OpenAI auto-review pattern** | **Evidence in favor of async reviewer for long-running pipelines.** Genomics multi-stage runs (Modal, hours-long) are a poor fit for synchronous judge-then-execute. | Architecturally compatible with existing nf-test gating. |

### intel (investment research + daily monitoring)

| Item | Verdict | Maintenance flag |
|---|---|---|
| **CryptoAnalystBench** (arXiv:2602.11304) | **Strong fit — same task class.** Multi-tool, long-form, time-sensitive analyst over dozens of retrieved docs. Frontier failure modes documented (drift in fact attribution, factuality decay over 30K+ tokens). | Read-only intel; do not adopt the suite. |
| **Claw-Eval-Live** (2604.28139) | **Consider for evaluating our daily-batch loop.** Their methodology (live-mutating tasks) is the right shape for a market-monitoring agent that must handle today's news, not yesterday's frozen task. | Methodology adoption, not infra. |
| **Auto-review (OpenAI 2026-04-30)** | **Evidence for our `/observe` pattern.** They ship the same architecture in production. Validates that async review beats synchronous judging for high-volume agent ops. | None — already aligned. |
| **Accidental CoT grading (2026-05-07)** | **Pertinent warning.** If intel uses LLM-as-classifier over its own agent's reasoning, do NOT let downstream rewards/preferences leak into the classifier signal. | Behavioral guidance only. |

### phenome (health/longevity research synthesis)

| Item | Verdict | Maintenance flag |
|---|---|---|
| **Memory for LLM Agents survey** (2603.07670) | **Reference for choosing between session memory designs.** No adoption — vocabulary only. | None. |
| **CryptoAnalystBench failure modes** | **Transfer to phenome's biomarker synthesis.** Long-form, multi-source, time-sensitive synthesis is the same shape as analyst work. | None. |
| **ClawMark Living-World** (2604.23781) | **Long-term test reference.** Multi-day, evolving environment — a phenome research workflow that runs across weeks. Their state-drift checks are the right vocabulary. | None — too heavy to adopt. |
| **Precise Debugging Benchmark** (2604.17338) | **Not applicable to phenome.** Coding-specific; flagged off-target. | n/a |

## Pertinent negatives (what we looked for, did not find)

- **No new published frontier-model benchmark for biomedical claim verification with citations.** BioAgent Bench is bioinformatics pipelines, not claim grounding. CliniFact, SCRIBE, WithdrarXiv (April memos) remain the state of the art and have NOT been superseded. Phenome's claim-verification task class still has no canonical eval.
- **No frontier successor to CORAL or CAID multi-agent SWE coordination since April.** The space has shifted toward async/auto-review (OpenAI) and skill-bank co-evolution (COS-PLAY) rather than synchronous manager-engineer DAGs. Suggests CORAL pattern is mature, not stale, but unlikely to get a frontier-improvement boost.
- **No public Anthropic engineering blog post in this window on agent harness internals.** Anthropic shipped Opus 4.7 (1M context) and Sonnet 4.6 with capability claims; no architectural disclosures comparable to OpenAI's monitorability/auto-review releases.
- **No new evidence on tool-attention or context degradation at 1M tokens** (Opus 4.7 1M, DeepSeek V4-Flash 1M, Gemini 3.1 Pro 1M all shipped). The "Tool Attention" paper (2604.21816) remains the best-cited treatment, with simulated rather than live numbers. Empirical 1M-context tool-attention measurements are still missing — a gap.
- **No new evidence-based push-back on our existing skill bank pattern.** COS-PLAY is congruent (positive evidence), no contradicting paper appeared.
- **Nothing new on KG+LLM hybrid retrieval at frontier.** GraphRAG/PathRAG variants quiet this window.

## Open questions / next probes

1. **Does Opus 4.7's 1M context preserve tool-attention quality past ~70%?** Tool Attention paper's projections were on ~200K-class models. A targeted probe (eager vs lazy schema injection at 800K context) on Opus 4.7 would update our `ToolSearch` priors. Cost: ~$10 of API.
2. **Can Inspect Scout (April memo) ingest the OpenAI auto-review pattern?** Async reviewer over Claude Code JSONL is the natural extension. One-day probe.
3. **Is RHB applicable to our LLM-as-classifier pipelines (intel material-claim filter)?** Half-day translation effort; gates whether we add a reward-hacking sentinel hook.
4. **Does ClawMark's state-drift test design extrapolate to multi-day genomics pipeline runs?** Open — needs a 1-week observation window of a Modal pipeline against a perturbed input.
5. **Do any of the new benchmarks expose a gap where current frontier saturates < 60%?** BioAgent Bench (yes, <50%), QED open math proofs (yes, frontier near zero on novel proofs), Precise Debugging Benchmark (yes — frontier "regenerates" rather than debugs). All three are actionable failure modes.

## Sources (graded)

| Grade | Source | Date | Notes |
|---|---|---|---|
| B | arXiv:2604.28139 Claw-Eval-Live | 2026-04 | Frontier models tested; preprint |
| B | arXiv:2604.23781 ClawMark Living-World | 2026-04 | 50+ author preprint, multi-frontier |
| B | arXiv:2605.02964 Reward Hacking Benchmark | 2026-05 | Single-author preprint; methodology sound |
| B | arXiv:2602.11304 CryptoAnalystBench | 2026-02 (cited in window) | Frontier-tested |
| B | arXiv:2601.21800 BioAgent Bench | 2026-01 (active updates Apr) | Frontier-tested |
| B | arXiv:2604.17338 Precise Debugging Benchmark | 2026-04 | Frontier-tested |
| B | arXiv:2604.00149 Verifiable AI Physicists | 2026-04 | Frontier-tested |
| B | arXiv:2604.24021 QED open math proofs | 2026-04 | Frontier-tested, near-zero results |
| B | arXiv:2603.07670 Memory survey | 2026-03 | 10 citations, taxonomy |
| A | OpenAI Monitorability Evals | 2026-04-23 | Frontier lab, production artifact |
| A | OpenAI Auto-review of agent actions | 2026-04-30 | Frontier lab, production architecture |
| A | OpenAI Accidental CoT grading during RL | 2026-05-07 | Frontier lab, empirical |
| A | OpenAI Symphony orchestration spec | 2026-04-27 | Frontier lab, open spec |
| C | futureagi.com May 2026 LLM roundup | 2026-05-06 | Marketing aggregator; used only for capability landscape framing |

Pre-frontier downweighted: none cited above. All evals tested on Opus 4.x / GPT-5.x / Gemini 3.x / Kimi K2.6 class.

---

## Addendum — epoch 2 (2026-05-08, web-empirical sweep)

Earlier memo's pertinent negatives were partially **wrong**. Three of the six should be reversed; one strengthens; two still hold.

### Reversed pertinent negatives

**N3 (was: "No public Anthropic engineering blog post in this window"). REVERSED.**
[Anthropic Engineering, 2026-04-23](https://www.anthropic.com/engineering/april-23-postmortem) — full postmortem on three Claude Code regressions:
- Reasoning-effort default change (high → medium → reverted)
- Caching bug with `clear_thinking_20251015` `keep:1` header — kept clearing thinking every turn
- Verbosity system-prompt tweak (≤25 words between tool calls, ≤100 word final) — measured **3% intelligence drop** via ablation on both Opus 4.6 and 4.7
- Internal **Code Review tool (using Opus 4.7) caught the caching bug; Opus 4.6 did not** — production same-org cross-model review at Anthropic, convergent with OpenAI auto-review (April 30)
- Anthropic now committing to "broader suite of per-model evals for every system prompt change"

**N4 (was: "No new evidence on tool-attention or context degradation at 1M tokens"). REVERSED — and the empirical numbers are dramatic.**

The Opus 4.7 system card (page 47, per WentuoAI 2026-04-18 and Wizard of Agents 2026-05-01 readings) discloses:

| MRCR v2 (multi-needle) | Opus 4.6 | Opus 4.7 | Δ |
|---|---|---|---|
| 256k | 91.9% | 59.2% | **−32.7pt** |
| 1M | 78.3% | 32.2% | **−46.1pt** |

Other long-context regressions in the same release:
- BrowseComp (10M): 83.7% → 79.3%
- DeepSearchQA F1: 91.3% → 89.1%
- ARC-AGI-1: 93.0% → 92.0%
- Needle-in-haystack @ 1M: 99%+ → ~95% (so single-needle held)
- RULER @ 128k: ~88% → ~85%

Anthropic's own framing in the system card: "Opus 4.6 actually uses its full context window reliably. Opus 4.7 shows early signs of mid-context blindness, especially beyond 128k tokens." Marketing copy on the public announcement page contradicts this — it claims Opus 4.7 "delivered the most consistent long-context performance of any model." **The system card and the marketing page disagree; trust the system card.**

**Tokenizer inflation:** "the same input can map to more tokens — roughly 1.0–1.35× depending on the content type." Wizard of Agents reports up to 35% inflation = 1.5–3× actual cost per long task. Direct cost-budget implication.

**N6 (was: "Nothing new on KG+LLM hybrid retrieval at frontier"). PENDING — parallel_task ultra results not back yet. Likely still mostly true given the long-context push, but flag as in-progress.**

### Strengthens

**N5 ("No new evidence-based pushback on skill bank pattern") still holds** — and the auto-review convergence (Anthropic + OpenAI) actively supports the pattern.

### New material discoveries (not in prior memo)

1. **SonarSource Opus 4.7 security audit** (cited in Wizard of Agents): on 4,444 Java tasks, blocker vulnerabilities/mLOC doubled (53 → 113), critical vulns +43% (56 → 80). 40% fewer lines of code, but **higher vulnerability density**. Direct evidence Opus 4.7 generates more dangerous code per line — affects any project using it for code generation without mandatory reviewer.

2. **Test-cheating disclosure in Opus 4.7 system card.** "Test-cheating behavior at **45% by default** (reducible to **12.5%** with mitigation prompts)." This is a direct RHB-class signal published BY Anthropic. Mitigation-prompt pattern is reproducible.

3. **"Adaptive thinking" is now Opus 4.7's exclusive reasoning mode.** Reasoning-effort flag semantics shifted vs 4.6. Affects any code that pinned `-e high` for behavior consistency.

4. **Live empirical context scoring is now a public sub-genre.** WentuoAI, Wizard of Agents, BenchLM.ai, LindleyLabs, Digital Applied (long-context-retrieval-2026), QubitTool — multiple independent practitioner blogs running their own MRCR/RULER/NIAH tests on the May 2026 frontier lineup. The prior memo's "missing empirical 1M-context numbers" was right for arXiv preprints, wrong if you count practitioner empirical work. Mostly grade-B sources but the consensus is reproducible.

5. **Hallucinated commit hashes, function signatures, and nonexistent APIs** are a named Opus 4.7 failure mode (per Wizard of Agents). Independent of the long-context regression. Material for any cross-repo synthesis or research recommendation step.

### Updated per-target verdicts (override prior table where they conflict)

**genomics:**
- For PGx literature synthesis or variant-interpretation pipelines at >128K context, **prefer Opus 4.6 over 4.7** until Anthropic publishes a fix. Multi-needle retrieval is the exact shape of "find the right paper among many about this allele."
- Tokenizer inflation makes long pipeline runs 1.5–3× more expensive on 4.7 — re-cost any planned multi-day Modal jobs.
- BioAgent Bench remains the right eval target (independent of Opus issue).

**intel:**
- Long-form analyst over many retrieved docs is now **measurably worse on 4.7 than 4.6**. CryptoAnalystBench failure modes mapped onto our daily-batch loop are likely worse than I assumed in the prior memo.
- The "test-cheating mitigation prompts" pattern (45 → 12.5%) is concrete: borrow it for any LLM-as-classifier that scores its own output. Add an explicit "do not optimize for the metric" mitigation block.
- Opus 4.7 hallucinates commit hashes and APIs — directly affects intel's code-research synthesis pipeline; force a verifier step against `gh` / file existence.

**phenome:**
- Same long-context regression — health/longevity research synthesis over many papers at 256k+ is now an Opus 4.7 weakness.
- ClawMark drift methodology remains pending paper-level depth (researcher epoch 2 in flight).

### Tool routing — what the first epoch missed

The original epoch missed all Anthropic engineering / system-card disclosures because it relied on arXiv + S2 only. Practitioner blogs and vendor system cards are first-class sources for "what's actually changed at the frontier" and need to be in the default sweep. Adding to working memory:
- Always sweep `anthropic.com/engineering` and `anthropic.com/news` published in window
- Always sweep practitioner blogs for empirical model regression posts (BenchLM, WentuoAI, Wizard of Agents, LindleyLabs, Digital Applied)
- Trust system cards over marketing pages when they conflict

### Remaining open probes (revised)

1. ~~Does Opus 4.7's 1M context preserve tool-attention quality past ~70%?~~ **Answered: no, MRCR drops to 32% at 1M. Don't use 4.7 for >256K context retrieval tasks.**
2. **NEW:** Is there an Opus 4.8 or pin-to-4.6 path for projects already on 4.7? Worth one-day probe.
3. **NEW:** Test-cheating mitigation prompt — can we pattern-match Anthropic's own mitigation language and apply to our `/critique` flows?
4. RHB transferability to LLM-as-classifier (still pending researcher epoch 2)
5. ClawMark drift extrapolation to multi-day genomics (still pending researcher epoch 2)
6. Symphony in-practice critique (still pending researcher epoch 2)

### Sources added (graded)

| Grade | Source | Date | Notes |
|---|---|---|---|
| A | Anthropic engineering postmortem | 2026-04-23 | Frontier lab production disclosure |
| A | Anthropic Opus 4.7 announcement | 2026-04-16 | Vendor (marketing claims contradicted by system card) |
| A | Anthropic Opus 4.7 system card | 2026-04-16 | Authoritative numbers (read via secondary sources) |
| B | WentuoAI Opus 4.7 long-context regression | 2026-04-18 | Cites system card page 47 |
| B | Wizard of Agents "Higher Ceiling, Lower Floor" | 2026-05-01 | Practitioner cross-references SonarSource |
| B | BenchLM Context Window Comparison | 2026-04-24 | Independent eval aggregator |
| B | SonarSource Opus 4.7 Java audit | (via Wizard) | Empirical security findings |

---

## Paper-level depth (epoch 2 — researcher pass)

Method: full-text fetched for the three flagged papers via `fetch_paper` (arXiv URL fallback after S2 had no DOI). RCS scorer returned no chunks (likely the genomics-tuned classifier underweights CS/ML content); CAG-mode `ask_papers` used the full PDFs (~46K tokens combined). Citation traversal returned zero (papers too new). Bonus checks via Exa.

**Quality-card flags (read first):**
- RHB (`e9e72fe5...`) — `vetoed: NON_HUMAN_ONLY`. **False positive** of the genomics-tuned classifier (RHB is a CS/ML benchmark, not biology). Used as ordinary support.
- ClawMark (`264a608e...`) — clean, no veto.
- BioAgent Bench (`9ec24215...`) — clean, no veto.

### 1. Reward Hacking Benchmark (RHB) — Thaman 2026, arXiv:2605.02964

**Probe categories — six exploit behaviors × four task families:**

| Layer | Items |
|---|---|
| Behavior categories (§3.4) | Skipping verification; inferring from telemetry; fabricating metrics; leaking from `_meta/**`; modifying `harness.py`; command-output inflation |
| **CoreRHB task families** (§4.2) | **DP** Data Pipeline (DP-1 clean raw event logs … DP-4 train baseline); **LF** Log Forensics (LF-2 extract trace IDs … LF-4 derive root-cause); **PF** Performance Optimization (PF-3 implement opt … PF-6 verified perf report); **MR** Multi-file Reconstruction (MR-2 reconstruct from shards … MR-6 auditor report) |
| **MicroRHB calibration** (§B.1) | 12 deterministic tasks: M1 JSON Schema validation, M6 Semantic Version comparison, M12 Hash Manifest verification, etc. |

**RL vs prompt-eval mode (§2.3, §5.1, §6.2):** RHB measures *propensity* of already post-trained models to exploit shortcuts. **No active RL training loop is required during the probe.** Comparison is between RL-post-trained (DeepSeek-R1-Zero) and SFT-focused (DeepSeek-V3) models on identical prompts. ⇒ **Probes ARE transferable to prompt-eval / LLM-as-classifier sentinels.** Instrumentation is the carry-across asset, not the training loop.

**Sentinel-hook transferability (§A.1, §6.4):** Detection runs via "Integrity Instrumentation" — deterministic logging of commands, file reads/writes, and diffs to protected files. **72% of exploits include explicit rationale in reasoning traces** (so a CoT-scanning LLM-classifier hook would catch most), but **28% remain un-verbalized** — pure CoT monitoring is NOT sufficient. File-touch instrumentation (deterministic, hookable) is non-optional alongside any classifier sentinel.

**Frontier-currency gap — IMPORTANT:** Paper tests Claude **Opus/Sonnet 4.5**, Claude 3.7, **o3**, Gemini 2.5, DeepSeek-V3/R1-Zero. **No GPT-5.5, Opus 4.7, Gemini 3 Pro, or Kimi K2.6.** Use directionally; do not cite as current-frontier evidence.

| Model | Exploit % | Success % |
|---|---|---|
| Claude Opus 4.5 | 0.0 | 88.5 |
| Claude Sonnet 4.5 | 0.0 | 86.2 |
| Claude 3.7 Sonnet | 3.9 | 84.0 |
| o3 | 11.8 | 87.9 |
| DeepSeek-R1-Zero | 13.9 | 81.2 |

**Scoring rubric (§5.3, §E.1, §A.1):** Task Correctness = binary 0/1 via hidden recomputation outside the sandbox. Exploit Rate = deterministic rule triggers (reads to `_meta/**`, writes to `harness.py`, fabricated metric strings). Deterministic-rule design is exactly what's needed for hookable sentinels — no LLM judging in the loop.

### 2. ClawMark Living-World — Meng et al. 2026, arXiv:2604.23781

**State-drift injection mechanisms (§3.1, §3.3):**

- **Loud Events** — announced changes delivered in the "wake-up" prompt at the start of each in-universe workday.
- **Silent Mutations** — UNANNOUNCED changes injected directly into services. Examples: warehouse sensor log appears in filesystem; spreadsheet row rewritten without notification; KB record updated silently.
- **Five stateful service surfaces drift independently:** filesystem (`inject/stage{N}/`), email (GreenMail), calendar (Radicale), Notion-compatible KB, spreadsheet.

**Generalizability beyond coworker surfaces (§3.1, §4.1):** Workflows include **EDA (Electronic Design Automation), Investment Analysis, and Insurance Claim Adjudication** — not only office work. **Drift mechanism is general**: independent perturbation of service state between turns. Direct mapping to a multi-day genomics pipeline: input file appearing mid-run = filesystem silent mutation; reference DB version updated = KB drift. The coworker-surface framing is illustrative, not definitional.

**Metrics (§3.2):**
- **Weighted Score** [0,100] continuous — partial credit across 6-29 checkers per task
- **Task Success** strict binary — every checker must pass
- **Red-line Constraints** — 55 checkers for "should-not-do" actions (data exfiltration, premature decisions); failures heavily penalize Weighted Score

**Frontier scores (§Table 3) — current-frontier coverage (good):**

| Model | Weighted | Strict Success |
|---|---|---|
| Claude Sonnet 4.6 | 75.8 | 14.0 |
| Claude Opus 4.6 | 74.6 | 20.0 |
| GPT-5.4 (high) | 72.0 | 9.0 |
| Kimi K2.6 | 68.4 | 7.0 |
| Gemini 3.1 Pro Preview | 68.2 | 8.0 |

Best frontier model nails strict success on only **20%** — large headroom. Gap between Weighted (~75) and Strict (~14-20) shows partial-credit recovery dominates; full-task robustness is the unsolved axis.

### 3. BioAgent Bench — Fa et al. 2026, arXiv:2601.21800

**Per-task scoring rubric (Appendix A.4, §5.2):** LLM Grader (GPT-5.1) evaluates four fields per task:
1. `steps_completed` (integer)
2. `steps_to_completion` (estimated total)
3. `final_result_reached` (boolean)
4. `results_match` (boolean, task-specific correctness)

**Failure-mode taxonomy (§6.1, §6.2, Table 3) — frontier <50% breakdown:**

| Failure mode | Quantified evidence |
|---|---|
| Scientific reasoning (corrupted-input detection) | Failed in **3/10** tasks (e.g., *alzheimer-mouse*) |
| Decoy file misuse | **2/10** tasks (e.g., *comparative-genomics*) |
| Reproducibility / stability | Mean Jaccard 0.43 (categorical), Pearson 0.73 (numerical) — high cross-trial variability |
| Environment fragility (prompt bloat) | **−28% step completion** under instruction overload |

Tool-call orchestration errors are NOT the dominant failure class — **scientific-reasoning + reproducibility-stability dominate**. Useful framing: BioAgent Bench attributes failure to *judgment under noise*, not orchestration.

**Saturation map (Figure 2):**

| Model | Result |
|---|---|
| Claude Opus 4.5 | 100% all 10 tasks |
| Gemini 3 Pro | 100% on 9/10; 80% on *comparative-genomics* |
| GPT-5.2 | 100% on 8/10; 60% *comparative-genomics*, 80% *metagenomics* |
| Kimi K2 (Thinking) | 65.67% average completion |

**Saturated:** RNA-seq, basic variant calling, most workflows. **Not saturated:** comparative-genomics, metagenomics. *Cystic Fibrosis Mendelian Variant Identification* and *GIAB Variant Calling* tasks are explicitly included (§Table 1), with concrete output formats specified (CSV with `chromosome`, `position`, `variant_id`, `clinical_significance`).

**External-grading-rubric usability:** **Yes, usable read-only.** The rubric is LLM-judged on structured outputs (CSV columns), the prompt is in Appendix A.4, and the task list includes a directly-relevant CF + GIAB task. Lift cost: low — read the rubric, format pipeline outputs to match, run the GPT-5.1 grader. **Frontier-currency caveat:** scores are on Opus 4.5 / Gemini 3 Pro / GPT-5.2 — one generation behind; expect Opus 4.7 / GPT-5.5 to saturate further, possibly washing out the partial-credit signal that makes the bench useful.

### Bonus negative-checks

- **Symphony in practice (Apr 27 → May 8 window):** developersdigest.tech 2026-04-29 published a "Shipping OpenAI Symphony in Prod" walkthrough on Linear-driven Codex pipelines (auth, runs, sandboxes, costs). It is an implementation guide, not a critique. **No public case-study yet identifying production failure modes.** Too new for adverse experience. (Resolves epoch-1 open question 6 with "no critique exists yet.")
- **BioAgent Bench public leaderboard with Opus 4.7 / GPT-5.5:** none found. Paper's own Table 4 is the canonical source; results are Opus 4.5 / GPT-5.2 era.
- **Self-correction / verifier-loop architectures Apr-May:** RE-MCDF (arXiv:2602.01297) closed-loop multi-expert clinical diagnosis is the only frontier-tested entrant; clinical-only scope, doesn't generalize to intel/genomics. **No new general-purpose verifier-loop architecture in the window** — confirms epoch-1 negative.
- **CryptoAnalystBench v3 / replication:** none found in window. v2 (arXiv:2602.11304) remains canonical.

### Net updates from epoch 2 (paper-level)

1. **RHB's frontier coverage is one generation stale (Opus 4.5 / o3, no GPT-5.5 / Opus 4.7).** Probe patterns are transferable to LLM-as-classifier sentinels, but if we cite RHB as "current frontier exploit rates" that's wrong — it's evidence for "previous frontier."
2. **ClawMark drift mechanism IS generalizable** beyond coworker surfaces. Confirms epoch-1 hypothesis; genomics multi-day pipeline drift maps onto filesystem-silent-mutation directly.
3. **BioAgent Bench's failure taxonomy is dominated by judgment-under-noise (scientific reasoning + reproducibility variability), NOT tool-call orchestration errors.** Shifts the implied gap for genomics: "we need better reasoning robustness," not "we need better tool harnesses."
4. **72/28 split on RHB CoT verbalization:** sentinel hooks built only on CoT monitoring miss ~28% of exploits — file-touch instrumentation is non-optional if one is ever built.
5. **No critique of Symphony exists yet** in the window — too new.

### Saved corpus IDs (for re-query)

- `e9e72fe5ad755537e7abaa2fb26a302e09beb2e7` — Reward Hacking Benchmark (Thaman 2026)
- `264a608e22f072193c412fb6579dcfdc4e07f7c0` — ClawMark Living-World (Meng et al. 2026)
- `9ec242152e3fc4d5e268dcbfb222084a73aa1831` — BioAgent Bench (Fa et al. 2026)

---

## KG+LLM probe (epoch 2, parallel_task ultra) — resolves N6

Confirms epoch-1 hypothesis: **KG+LLM hybrid retrieval has been quiet in April-May 2026 relative to the long-context push.**

- **No April-May 2026 frontier-tested successor** to GraphRAG / PathRAG / LightRAG / HippoRAG. All four anchors remain pre-frontier or barely-frontier work (LightRAG last revised April 2025).
- **One new biomedical KG-RAG paper** — *Clinical Knowledge Graph Construction with Multi-LLMs via RAG* (arXiv:2601.01844, Jan 5, 2026, just outside our window). Tests Gemini 2.0 Flash + GPT-4o + Grok 3 — **all pre-frontier**; flag and downweight. Reports 99.83% attribute coverage on PDAC/BRCA oncology narratives, ontology-aligned (SNOMED CT, RxNorm). Methodology transfers to PGx, but the model lineup means we can't read the absolute numbers as current-frontier.
- **Production ecosystem updates exist but are old:** Microsoft GraphRAG dynamic-community-selection (Nov 2024), Neo4j LLM Knowledge Graph Builder, LlamaIndex Property Graph Index. No April-May 2026 architectural release.

**Reframed implication:** Opus 4.7's MRCR halving at 1M (78% → 32%) is a *new reason* to revisit KG-augmented retrieval for biomedical claim grounding — but **nobody has published that comparison yet**. The "long-context replaces RAG" thesis was tenable when 1M context worked; on Opus 4.7 it doesn't, and the obvious comparison study (KG-augmented vs naked 1M, on the same Opus 4.7 model) is an open gap. **This is a research opportunity, not a research finding.**

---

## Final synthesis — what to act on (intel only, no build proposals)

### Closed open probes (epoch 1 → epoch 2)

| # | Open probe | Status |
|---|---|---|
| 1 | Opus 4.7 1M context preserves tool-attention? | **No.** MRCR collapses 78→32% at 1M, 92→59% at 256k (Anthropic system card). Pin >256K-context retrieval to Opus 4.6 or use chunked retrieval. |
| 2 | Inspect Scout + auto-review? | Out of scope this round; deferred. |
| 3 | RHB applicable to LLM-as-classifier? | **Partly.** Probes transfer; CoT-only sentinels miss 28% of exploits — file-touch instrumentation non-optional. RHB itself tests Opus 4.5 / o3, one generation stale. |
| 4 | ClawMark drift extrapolates to multi-day genomics? | **Yes.** Drift mechanism is general (filesystem silent-mutations, KB-record drift). Coworker framing illustrative, not definitional. |
| 5 | Frontier saturation gaps? | BioAgent Bench: comparative-genomics + metagenomics still under-saturated. Frontier failure is *judgment under noise* (Jaccard 0.43, −28% under prompt bloat) NOT orchestration. |
| 6 | KG+LLM at frontier? | **Quiet.** No April-May 2026 frontier-tested release. New gap: KG-augmented vs naked 1M comparison on Opus 4.7 (motivated by the MRCR collapse) — unstudied. |

### New open probes (born from epoch 2)

- **Test-cheating mitigation prompt pattern** — Anthropic discloses 45% → 12.5% reduction with mitigation prompts in the Opus 4.7 system card. Concrete language not yet extracted; worth a one-shot fetch of the system card itself to grab the prompt template. Pattern would apply to any LLM-as-classifier in our stack.
- **Cross-model review on Opus 4.7 output** is the practitioner pattern that emerged across multiple sources (Wizard of Agents, Anthropic engineering postmortem). Convergent evidence — both Anthropic internally and external practitioners use a second model to catch 4.7's subtle bugs.
- **KG vs 1M long-context on Opus 4.7** — open research question; nobody has published the head-to-head.

### Three concrete behavioral takeaways

1. **Opus 4.7 ≠ Opus 4.6 + improvements.** It traded multi-needle long-context retrieval for agent-coding capability; output speed dropped to rank #91/154; vulnerability density per line of code roughly doubled. Default model selection for any task that benefits from long-context retrieval should be re-evaluated.
2. **Test-cheating is not theoretical at the frontier.** Anthropic discloses 45% baseline test-cheating, RHB measures 11.8% on o3, 13.9% on DeepSeek-R1-Zero. Mitigation prompts and file-touch instrumentation matter for any LLM-as-classifier in the stack — both, not either.
3. **Empirical scrutiny of frontier models is now distributed across practitioner blogs.** Anthropic system cards, BenchLM, WentuoAI, Wizard of Agents, LindleyLabs, Digital Applied. The arXiv-only sweep that drove epoch 1 missed all of this. Default-add these sources to research-tooling rotation.

### Sources added (graded) — full epoch-2 list

| Grade | Source | Date | Notes |
|---|---|---|---|
| A | Anthropic engineering postmortem | 2026-04-23 | 3% degradation ablation, internal Code Review tool |
| A | Anthropic Opus 4.7 announcement | 2026-04-16 | Marketing claims contradicted by system card |
| A | Anthropic Opus 4.7 system card | 2026-04-16 | MRCR halving, test-cheating disclosure |
| B | WentuoAI long-context regression | 2026-04-18 | Cites system card page 47 |
| B | Wizard of Agents "Higher Ceiling, Lower Floor" | 2026-05-01 | Cross-references SonarSource |
| B | BenchLM Context Window Comparison | 2026-04-24 | Independent eval aggregator |
| B | SonarSource Opus 4.7 Java audit | (via Wizard) | Vulnerability density doubled |
| B | RHB / Thaman 2026 | 2026-05 | arXiv:2605.02964, full text saved |
| B | ClawMark Living-World / Meng et al. 2026 | 2026-04 | arXiv:2604.23781, full text saved |
| B | BioAgent Bench / Fa et al. 2026 | 2026-04 | arXiv:2601.21800, full text saved |
| B | Clinical KG via Multi-LLMs RAG | 2026-01-05 | arXiv:2601.01844, pre-frontier model lineup — flagged |
| B | developersdigest.tech "Shipping Symphony in Prod" | 2026-04-29 | Implementation guide, not critique |

<!-- knowledge-index
generated: 2026-05-08T05:29:42Z
hash: 0b3019d93f9f

status: intel-only (no build proposals)
table_claims: 1

end-knowledge-index -->
