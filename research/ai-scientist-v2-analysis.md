## AI Scientist v2 (Sakana AI) — Research Memo

**Question:** Architecture, novel mechanisms, evaluation, limitations, and key design decisions of AI Scientist v2
**Tier:** Standard | **Date:** 2026-04-02
**Paper:** arXiv:2504.08066 (Yamada, Lange, Lu, Hu, Lu, Foerster, Clune, Ha — Sakana AI / Oxford / UBC / Vector)
**Published:** Nature, March 2026 | **Repo:** github.com/SakanaAI/AI-Scientist-v2 (4,470 stars, 645 forks, Apache-2.0)

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | First fully AI-generated paper accepted through peer review at a top ML workshop | ICLR 2025 ICBINB workshop, scores 6/7/6, withdrawn per protocol | HIGH | [arXiv:2504.08066] | VERIFIED |
| 2 | 1/3 papers accepted at workshop level (33% acceptance) | Paper reports scores for all three submissions | HIGH | [arXiv:2504.08066] | VERIFIED |
| 3 | 0/3 papers met internal ICLR conference-track standards | Authors' own assessment | HIGH | [sakana.ai/ai-scientist-first-publication] | VERIFIED |
| 4 | 57% of generated papers contained incorrect or hallucinated numerical results | Independent evaluations cited; paper itself documents 57% train/test overlap in accepted paper's datasets | MEDIUM | [byteiota.com], [arXiv:2504.08066] | PARTIALLY VERIFIED |
| 5 | Cost ~$15-20 per experiment run (Claude 3.5 Sonnet) | README states this; paper does not give precise figures | MEDIUM | [GitHub README] | VERIFIED |
| 6 | Nature publication March 2026 | Confirmed via Sakana announcement, UBC news, Nature editorial | HIGH | [verify_claim] | VERIFIED |

---

### 1. Architecture (End-to-End)

Three stages, each using different models in a multi-model pipeline:

**Stage 1 — Ideation.** Generates research hypotheses at grant-proposal abstraction level (not code-level modifications as in v1). Integrates Semantic Scholar API for novelty checking and literature grounding. Produces a structured research idea with hypotheses, proposed experiments, and expected outcomes. No human-authored templates required.

**Stage 2 — Experimentation (BFTS).** The core innovation. An Experiment Progress Manager agent coordinates four sub-stages:
1. **Preliminary Investigation** — establish minimal working prototype
2. **Hyperparameter Tuning** — optimize baseline configuration
3. **Research Agenda Execution** — implement core novel hypotheses
4. **Ablation Studies** — isolate component contributions

The experimentation uses Best-First Tree Search (BFTS): a tree of experiment nodes explored in parallel, where an LLM evaluator selects the most promising non-buggy nodes for expansion based on performance metrics, training dynamics, and plot quality. A configurable probability (`debug_prob`) allocates expansion budget to buggy nodes for autonomous debugging.

**Stage 3 — Writing.** Single-pass manuscript generation followed by reflection via reasoning models (o1). VLM feedback loop refines figures. Citation gathering via Semantic Scholar (configurable rounds, default 20). Outputs LaTeX compiled to PDF.

**Model allocation:**
- Code generation: Claude 3.5 Sonnet v2
- LLM/VLM feedback + summary reports: GPT-4o
- Manuscript reflection: o1
- VLM figure review: GPT-4o (vision)

### 2. BFTS — The Core Mechanism

Six node types in the search tree:

| Type | Purpose |
|------|---------|
| **Non-buggy** | Successfully executed; eligible for expansion |
| **Buggy** | Execution error or VLM-flagged; debugging candidates |
| **Hyperparameter** | Stage 2 configuration variants |
| **Ablation** | Stage 4 component removal tests |
| **Replication** | Re-runs with different seeds for statistical rigor |
| **Aggregation** | Consolidation nodes — no new experiments, just mean/std summaries |

Selection: LLM evaluator scores non-buggy nodes; best-first expansion. Parallel execution via `num_workers` (default 3). Tree configured in `bfts_config.yaml` — `steps` (max nodes, e.g. 21), `max_debug_depth`, `debug_prob`, `num_seeds`.

The VLM feedback loop operates at two points: (1) post-execution, critiquing generated plots for missing legends/labels/misleading visuals — flagged nodes become buggy; (2) during writing, checking figure-caption alignment and detecting duplicates between main text and appendix.

### 3. v1 vs v2 — What Changed

| Dimension | v1 (Aug 2024) | v2 (Apr 2025) |
|-----------|---------------|---------------|
| Templates | Human-authored, topic-specific code templates required | Domain-general; no template dependency |
| Ideation | Code-level modifications to existing codebase | Abstract/grant-proposal level; Semantic Scholar novelty check |
| Execution | Linear, sequential, shallow | Tree-based parallel search (BFTS) with 4-stage manager |
| Visual QA | None | VLM feedback loop for figure quality |
| Models | Single model | Multi-model (Claude for code, GPT-4o for feedback, o1 for reflection) |
| Datasets | Bundled with templates | HuggingFace Hub automated loading |
| Evaluation | Self-review only | Double-blind workshop peer review |
| Citation count | v1 paper: 625 | v2 paper: 170 (still growing) |

The shift from v1 to v2 is genuine — template removal + tree search + multi-model pipeline is architectural, not incremental. However, the tradeoff is explicit: v2 has "broader, more exploratory approach with lower success rates" than v1's constrained but reliable template-guided execution.

### 4. Evaluation

**Protocol:** Three papers submitted double-blind to ICLR 2025 "I Can't Believe It's Not Better" (ICBINB) workshop. Reviewers knew AI submissions were possible but not which ones. Papers were withdrawn post-review per agreement with organizers.

**Scores:**
1. "Compositional Regularization" — **6, 7, 6** (avg 6.33) — **ACCEPTED**, top 45% of submissions
2. "Label Noise Calibration" — **3, 3** — REJECTED
3. "Pest Detection" — **3, 7, 4** — REJECTED (high variance)

**Internal assessment:** All three papers evaluated against ICLR main conference standards (20-30% acceptance) — none passed. Workshop acceptance rates are 60-70%.

**Nature publication (March 2026):** The v1+v2 system description was published in Nature, with accompanying editorial (Nature d41586-026-00934-w). This is the system paper, not an AI-generated research paper.

### 5. Documented Failure Modes

The paper and independent evaluations surface these specific failures:

1. **Citation hallucination.** Cites general textbooks (Goodfellow et al. 2016) instead of primary sources (Hochreiter & Schmidhuber 1997). References fabricated or misattributed.

2. **Data integrity.** 57% training/test overlap in synthetic datasets generated for the accepted paper. The system sometimes fabricated datasets while claiming to use real ones.

3. **Text-figure contradiction.** Accepted paper's Figure 5 showed attention-augmented model significantly outperforming baseline; text claimed similar performance.

4. **Caption errors.** Misidentified validation loss trends; incorrect data interpretation in figure captions.

5. **Terminology confusion.** Used "hidden states" when meaning "embedding states."

6. **Instruction disobedience.** ~10% of the time the model disobeys instructions (Sakana's own admission).

7. **Execution failures.** 42% experiment failure rate from coding errors causing crashes (independent evaluation figure).

8. **Impossible accuracy claims.** Reported 95-100% accuracy on intentionally noise-corrupted datasets (independent evaluation).

### 6. Key Design Decisions

**Sandboxing:** The README warns to "run within a controlled sandbox environment (e.g., Docker container)" but provides no built-in sandboxing implementation. Code executes via a Python interpreter (`treesearch/interpreter.py`). This is a significant gap — LLM-generated code with package installation and web access runs with whatever permissions the host process has.

**Cost control:** ~$15-20 per experiment run (Sonnet), ~$5 for writing phase. Total ~$20-25 per paper. Tree search bounded by `steps` parameter. Runtime capped at 15 hours.

**Quality gates:** VLM review of figures (can mark nodes buggy). LLM evaluator scores nodes for expansion priority. Simulated peer review post-writing. No automated factual verification of generated claims or results.

**Iterative refinement:** BFTS enables iterative refinement through tree expansion — each child node builds on parent's results. Debugging is probabilistic (not guaranteed). Replication nodes add statistical rigor through multi-seed runs. Aggregation nodes consolidate.

**Codebase structure (29 Python files):**
- `launch_scientist_bfts.py` — entry point
- `treesearch/` — BFTS engine, agent manager, parallel agent, interpreter, journal
- `perform_*.py` — stage executors (ideation, writeup, plotting, VLM review, LLM review)
- `tools/semantic_scholar.py` — S2 integration for novelty/citation
- `ideas/` — topic definitions (.md) + generated ideas (.json)
- `blank_*_latex/` — LaTeX templates (ICBINB, ICML 2025)
- `fewshot_examples/` — 3 human papers as writing exemplars

### 7. Assessment

**What's genuinely novel:** BFTS for experiment exploration is the real contribution — applying tree search with LLM-as-evaluator to scientific experimentation, with typed nodes (replication, ablation, aggregation) that mirror how human researchers structure experiments. The 4-stage experiment manager (preliminary → tuning → agenda → ablation) is a sound decomposition.

**What's incremental:** Multi-model pipeline (different models for different tasks) is standard practice. VLM figure review is straightforward application. Semantic Scholar integration for novelty checking existed in other tools (PaperQA2, OpenScholar).

**Honest assessment of results:** 1/3 workshop papers accepted is the headline, but the failure analysis matters more. 57% data integrity issues, 42% execution failures, text-figure contradictions in the *accepted* paper, and zero conference-track viable papers. The system produces workshop-level work with workshop-level reliability. The authors are admirably transparent about this — "broader, more exploratory approach with lower success rates" is accurate self-assessment.

**Missing architectural pieces:** No sandboxing implementation (critical for autonomous code execution). No automated result verification (the system can fabricate data and not catch it). No cost-aware search termination (fixed step budget, not ROI-driven). No cross-paper learning (each run is independent).

**Comparison to our autoresearch.py:** AI Scientist v2's BFTS is conceptually similar to evolutionary code search but with typed nodes and a manager agent coordinating stages. Key differences: (1) our system operates on harness code, theirs on experiment code + paper writing; (2) we use tournament selection, they use LLM-as-evaluator best-first; (3) they add replication/aggregation nodes for statistical rigor — worth stealing; (4) their 4-stage decomposition (preliminary → tuning → agenda → ablation) could map to our harness evolution phases.

### What's Uncertain

- Whether the Nature publication is specifically v2 or the combined v1+v2 system paper [INFERENCE: likely combined based on v1 paper having 625 citations and the arxiv ID 2504.08066 being the v2-specific paper]
- Exact dollar costs per model call (README gives ranges, paper omits specifics)
- Whether the 57% false data figure comes from the paper's own analysis or purely from independent evaluators (the paper documents 57% train/test overlap; the "false data" framing appears to be external interpretation)
- Reproducibility of the 1/3 acceptance rate across different topics and venues

<!-- knowledge-index
generated: 2026-04-02T17:57:50Z
hash: 2e7eec489871

sources: 1
  INFERENCE: likely combined based on v1 paper having 625 citations and the arxiv ID 2504.08066 being the v2-specific paper
table_claims: 6

end-knowledge-index -->
