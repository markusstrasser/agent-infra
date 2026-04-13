## Meta-Harness: End-to-End Optimization of Model Harnesses -- Research Memo

**Question:** How does Meta-Harness optimize the agent harness, what gets optimized, and how do traces/scores feed back?
**Tier:** Standard | **Date:** 2026-03-30
**Ground truth:** Prior ecosystem scans covered AutoHarness (DeepMind, arXiv:2603.03329) and LangChain's harness engineering blog post. This paper is distinct -- Stanford IRIS Lab, not Meta the company.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Uses a coding agent (Claude Code w/ Opus 4.6) as the proposer, not gradient-based or RL | Paper Section 3, "the proposer P is Claude Code with Opus-4.6" | HIGH | [Paper](https://yoonholee.com/meta-harness/paper.pdf) | VERIFIED |
| 2 | Optimizes complete harness code: system prompts, tool definitions, retrieval logic, memory/state management, context construction | Paper Abstract + Section 3 | HIGH | Paper S3 | VERIFIED |
| 3 | Filesystem-based feedback: all prior candidates' source code, execution traces, and scores stored as directories | Paper Section 3, Algorithm 1 | HIGH | Paper S3 | VERIFIED |
| 4 | ~10M tokens/iteration of diagnostic context (vs 0.001-0.026M for prior methods) | Paper Table 1 | HIGH | Paper Table 1 | VERIFIED |
| 5 | #1 among Haiku 4.5 agents on TerminalBench-2 (37.6% vs Goose 35.5%) | Paper Table 7 | HIGH | Paper Table 7, leaderboard | VERIFIED |
| 6 | #2 among Opus 4.6 agents on TerminalBench-2 (76.4% vs ForgeCode 81.8%) | Paper Table 7 | HIGH | Paper Table 7 | VERIFIED |
| 7 | +7.7 points over ACE on text classification with 4x fewer context tokens | Paper Table 2 | HIGH | Paper Table 2 | VERIFIED |
| 8 | +4.7 points average across 5 held-out models on IMO-level math (retrieval harness transfers) | Paper Table 6 | HIGH | Paper Table 6 | VERIFIED |
| 9 | Matches best prior text optimizer's final accuracy in 4 evaluations vs 60 | Paper Figure 1 | HIGH | Paper Figure 1 | VERIFIED |
| 10 | Ablation: full traces >> scores+summary >> scores-only (50.0 vs 34.9 vs 34.6 median) | Paper Table 3 | HIGH | Paper Table 3 | VERIFIED |

---

### Paper Identity

- **Title:** Meta-Harness: End-to-End Optimization of Model Harnesses
- **Authors:** Yoonho Lee, Roshen Nair, Qizheng Zhang, Omar Khattab, Kangwook Lee, Chelsea Finn
- **Affiliations:** Stanford (Lee, Nair, Zhang, Finn), MIT (Khattab), KRAFTON (K. Lee)
- **Status:** Preprint, 2026-03-30 (announced same day as this memo)
- **Project page:** https://yoonholee.com/meta-harness/
- **Artifact repo:** https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact
- **NOT from Meta Platforms** -- "Meta-Harness" is the method name (a meta-level harness that optimizes harnesses). Stanford IRIS Lab paper.

---

### Key Finding 1: How It Optimizes -- Coding Agent as Evolutionary Proposer

The optimization is **neither gradient-based nor RL**. It is closer to **evolutionary search with an agentic proposer**:

1. A coding agent (Claude Code with Opus 4.6) reads a growing filesystem of prior experience
2. The agent proposes a new harness (a single-file Python program)
3. The harness is evaluated on search-set tasks
4. All outputs (source code, reasoning traces, evaluation scores) are logged to the filesystem
5. Loop repeats for N iterations

The critical distinction from prior evolutionary/text optimizers (OPRO, TextGrad, AlphaEvolve, OpenEvolve, GEPA, TTT-Discover): **the proposer has unrestricted filesystem access to all prior history**, not just compressed summaries or scalar scores.

- Prior methods: 0.001-0.026 Mtok/iteration of feedback context
- Meta-Harness: **~10 Mtok/iteration** (400x more)
- The proposer uses `grep`, `cat`, and other terminal tools to selectively inspect prior artifacts
- Median: 82 files read per iteration, referencing 20+ prior candidates per step

**Algorithm (pseudocode from paper):**
```
Initialize population H with seed harnesses
Initialize filesystem D = {}
For each H in initial population:
    Evaluate H, store (code, scores, traces) to D
For t = 1..N:
    Proposer P queries filesystem D (reads selectively via grep/cat)
    P proposes k new harnesses
    For each proposed H:
        If H passes interface validation:
            Evaluate, store to D
Return Pareto frontier from D
```

No parent-selection rule -- the proposer decides what to inspect. No mutation operators -- the proposer writes complete programs. The "search structure" is deliberately minimal; diagnosis and proposal logic lives inside the agent, not the outer loop.

---

### Key Finding 2: What Gets Optimized

The harness is a **stateful program** that wraps a frozen LLM and determines what context the model sees at each step. Concretely optimized components:

**Text Classification domain:**
- Memory update strategies (what labeled examples to store, how to organize them)
- Retrieval programs (filtering, branching, formatting logic for context construction)
- Label presentation and query formatting
- Context budget allocation

**Math Reasoning domain:**
- Retrieval harness over a corpus of prior solutions (BM25-based)
- Example selection, formatting, and insertion into prompts
- The discovered harness operates entirely in code space on top of BM25 -- no dense encoder needed

**Agentic Coding (TerminalBench-2) domain:**
- Environment bootstrapping (the key discovered component)
- Prompt construction and context management
- Completion-checking logic
- Tool-use orchestration

The paper frames the optimization target formally: find H* = argmax_H E[r(tau, x)] where H is the harness, M is the frozen model, tau is the rollout trajectory, and r is the task-specific reward. When multiple objectives matter (accuracy + context cost), Pareto dominance is used.

---

### Key Finding 3: The Feedback Loop -- Filesystem as Memory

This is the core technical contribution. The feedback loop works through a **filesystem interface**:

**What gets stored per candidate harness:**
- Source code (the complete Python harness file)
- Evaluation scores (per-task pass/fail or accuracy)
- Execution traces (prompts sent to the model, model responses, tool calls, state updates)

**How the proposer uses it:**
- The proposer does NOT ingest all history as a single prompt (impossible at 10M tokens)
- Instead, it uses `grep`, `cat`, and other tools to selectively query the filesystem
- It reads broadly first (scanning scores across candidates) then deeply (inspecting specific traces of failures)
- The paper provides file access statistics: ~50/50 split between reading prior source code and execution traces

**Why this matters (ablation evidence):**
The paper's strongest result is Table 3 -- the ablation showing that execution trace access is the critical ingredient:

| Condition | Median Acc | Best Acc |
|-----------|-----------|---------|
| Scores only | 34.6 | 41.3 |
| Scores + LLM summary | 34.9 | 38.7 |
| Full traces (Meta-Harness) | **50.0** | **56.7** |

LLM-generated summaries do NOT recover the missing signal. They may even hurt by compressing away diagnostically useful details. The full Meta-Harness median candidate outperforms the *best* candidate found under either ablation.

**Causal reasoning observed in the proposer:**
The paper provides verbatim proposer logs from the TerminalBench-2 run showing:
- Iteration 1-6: Proposer identifies that control-flow and prompt-template edits cause regressions
- Iteration 7: After 6 consecutive regressions, proposer pivots to purely additive modification (environment bootstrapping) -- "All 6 prior iterations regressed because they modified the completion flow, prompt template, or observation processing"
- Iteration 10: Cross-run transfer -- proposer references results from a separate earlier search run

---

### Key Finding 4: TerminalBench-2 Discovered Harness

The discovered harness builds on Terminus-KIRA and adds **environment bootstrapping**:

Before the agent loop begins, the harness runs a compound shell command to gather:
- Working directory and file listing
- Installed programming languages (Python, Node, Java, Rust, Go)
- Package managers (pip, apt-get)
- Available memory

This eliminates 2-4 exploratory turns that agents typically waste discovering their environment. Gains concentrate on tasks requiring domain-specific tooling (bioinformatics libraries, rendering pipelines, chess engines, cryptographic utilities, CoreWars simulators).

The modification is ~80 lines on top of Terminus-KIRA, with a 15-second timeout and silent failure for robustness.

---

### Key Finding 5: Transfer and Generalization

Three forms of transfer demonstrated:

1. **Cross-dataset (text classification):** Discovered harness generalizes to 9 OOD datasets unseen during search. 73.1% avg vs ACE's 70.2%. Best on 6/9 datasets.
2. **Cross-model (math reasoning):** A single discovered retrieval harness improves accuracy across **all 5 held-out models** by avg 4.7 points. The harness was optimized with one model but transfers to others.
3. **Cross-run (agentic coding):** Proposer references results from separate earlier search runs, demonstrating learning transfer between optimization campaigns.

---

### Comparison to Related Work

| Method | Feedback type | Tokens/iter | Search structure |
|--------|--------------|-------------|-----------------|
| OPRO | (solution, score) pairs | 0.002M | Window of past pairs |
| TextGrad | Textual feedback on current | 0.015M | Last candidate only |
| AlphaEvolve | Program DB + scores | 0.022M | Evolutionary with archive |
| GEPA | Reflective feedback from traces | 0.008M | Rollout summaries |
| OpenEvolve | Programs + scores | ~0.022M | Evolutionary |
| TTT-Discover | Prior solution fragment | 0.026M | PUCT reuse rule |
| **Meta-Harness** | **All logs and scores** | **10.0M** | **Filesystem + agent** |

The paper argues this gap (3 orders of magnitude more context) is the key differentiator. Prior methods make a pragmatic scalability choice to compress feedback, but harness engineering has long-horizon dependencies where compressed feedback removes the diagnostic signal needed.

---

### Relevance to Our Infrastructure

**Direct parallels to our autoresearch.py:**
- Meta-Harness uses an "evolutionary" search over code artifacts with LLM-as-proposer -- structurally identical to autoresearch.py's approach
- The filesystem-as-memory pattern is exactly what we do (skills, traces, scores in files)
- The ablation proving traces >> summaries validates our decision to keep full execution logs

**Transferable patterns:**
1. **Environment bootstrapping for agent tasks** -- cheap, additive, high-value. We could add this to any agent dispatch (gather env snapshot before main task).
2. **Full-history filesystem access vs compressed summaries** -- the 10M token diagnostic footprint is key. Don't summarize prior experience; let the agent selectively inspect raw artifacts.
3. **Pareto frontier over multiple objectives** -- for autoresearch, track accuracy AND token cost, not just accuracy.
4. **Interface validation before evaluation** -- Meta-Harness validates that proposed harnesses pass interface checks before expensive evaluation. Cheap filter.
5. **Minimal outer loop** -- the proposer does the diagnosis. Don't over-engineer the search structure. This aligns with our constitution's "architecture over instructions" principle but applied to optimization loops.

**Key distinction from our autoresearch:**
- Our autoresearch mutates individual functions within a fixed scaffold
- Meta-Harness searches over complete single-file programs
- The paper argues this is important: "searches over full harness implementations rather than a predefined space of context-management procedures"
- We should consider whether expanding autoresearch to mutate complete harness files (not just functions) would be beneficial

---

### What's Uncertain

1. **Compute cost not reported in detail.** ~60 harness evaluations over 20 iterations, each with Claude Code Opus 4.6 as proposer. TerminalBench-2 evaluations are expensive (89 Dockerized tasks, 5 trials each). Total optimization cost likely $500-2000+ per run. [ESTIMATED]
2. **ForgeCode reproducibility claim.** Paper notes ForgeCode (81.8%) beats them on Opus 4.6 but "we were unable to reproduce their reported result from the publicly available code alone." Diplomatic way of suggesting possible leaderboard gaming.
3. **The paper claims the workflow "only became practical recently, following major improvements in coding-agent capabilities around early 2026."** This is a strong claim about capability thresholds -- would be interesting to test with weaker coding agents.
4. **No arXiv ID yet** -- paper announced 2026-03-30, preprint hosted on author's site. May appear on arXiv within days.

---

### Search Log

| Query | Tool | Result |
|-------|------|--------|
| "Meta-Harness optimizing agent harness traces scores TerminalBench" | search_papers (S2) | 0 results -- paper too new |
| "Meta-Harness paper optimizing agent harness yoonholeee" | web_search_exa | Found LangChain/AutoHarness but not target |
| "Meta-Harness end-to-end optimization model harnesses Yoonho Lee" | search_papers (S2) | 0 results |
| "yoonholeee Meta-Harness paper agent harness optimization TerminalBench" | brave_web_search | Found paper URL, project page, Twitter announcement |
| "AutoHarness Google DeepMind improving LLM agents code harness" | web_search_exa | Confirmed AutoHarness is different paper |
| yoonholee.com/meta-harness/ | WebFetch | Full project page details |
| yoonholee.com/meta-harness/paper.pdf | curl + pdftotext | Full paper text extracted (2009 lines) |

<!-- knowledge-index
generated: 2026-03-31T03:04:32Z
hash: a4240c5041a3

table_claims: 10

end-knowledge-index -->
