# Meta-Harness: Leverage Brainstorm

**Source:** Lee et al. 2026, arXiv:2603.28052 — "Meta-Harness: End-to-End Optimization of Model Harnesses"
**Corpus:** `64cd8a551607d5d004e37bb0c6cbd6d65241fbfb`

## Paper in One Paragraph

"Harness" = the code wrapping an LLM that controls what information is stored, retrieved, and presented. Meta-Harness uses Claude Code (Opus 4.6) as an agentic proposer that reads raw execution traces, prior harness source code, and scores via filesystem — then proposes harness edits. Population-based search over harness code, Pareto frontier selection. Three domains: text classification (+7.7pts over SOTA, 4x fewer tokens), math reasoning (+4.7pts, generalizes across 5 held-out models), agentic coding (TerminalBench-2 #2). Critical ablation: raw traces → 50.0% median; scores-only → 34.6%; LLM-generated summaries → 34.9%.

## Framework Mapping

| Paper concept | Our system | Status |
|---|---|---|
| Harness code | CLAUDE.md + rules/ + hooks + skills + MCP configs + startup injection | ✓ exists |
| Evaluation benchmark | Session quality metrics (corrections, build-then-undo, fold rate) | Partial — session-features.py extracts but doesn't close the loop |
| Proposer agent | Session-analyst + design-review + human steering | ✓ exists, less systematic |
| Raw execution traces | JSONL transcripts (`~/.claude/projects/*/UUID.jsonl`) | ✓ exists, not indexed by failure mode |
| Compressed summaries | improvement-log.md entries | ✓ exists — and the paper says this is the WRONG input |
| Scored history per variant | session-receipts.jsonl + runlogs.db | **Gap: no harness version linkage** |
| Population of variants | Single harness (current config) | **Gap: no competing variants** |
| Pareto frontier | None | **Gap** |
| Proposer context budget | ~10M tokens (full filesystem) | We give session-analyst compressed transcripts (~50K). 200x less. |

## Key Findings × Our System

### 1. Raw traces >> summaries (the money result)

The ablation: 50.0% vs 34.6-34.9%. Summaries destroy the causal signal the proposer needs to form hypotheses about WHY something failed.

**Our current cycle:**
```
raw JSONL → session-analyst (Gemini, compressed) → improvement-log entry → human/agent reads entry → harness change
```

The paper says the compression step (→ improvement-log entry) is where we lose the most value. The improvement-log entry says "build-then-undo occurred in session X." But the raw trace shows the SEQUENCE: which tool call triggered it, what the agent was thinking, what context was missing, what correction the user made. That causal chain is what the proposer needs.

**Nuance:** Our cycle aggregates across different tasks (pattern detection), while Meta-Harness debugs the same task with different harnesses. So compression is less harmful for cross-session patterns. But for debugging specific failure modes — "why does the agent keep over-engineering in genomics?" — the raw trace is essential.

**Implication:** Session-analyst should feed Gemini 3.1 Pro MORE raw trace, not less. With 1M context, we can fit 5-10 full session transcripts. Currently we compress first and send summaries. The paper says this costs us ~15 percentage points of diagnostic quality.

### 2. Environment bootstrapping = highest single-intervention ROI

The TerminalBench winning harness: inject OS info, installed languages, package managers, directory listing before the agent loop. Eliminates 2-4 exploratory turns discovering available tools.

**We already do this.** The startup hook injects codebase structure overview. CLAUDE.md provides reference data. Rules/ provide operational context. This validates our approach.

**But we could do more.** Things NOT currently front-loaded:
- Recent git activity (`git log --oneline -5`) — would orient on in-progress work immediately
- Active plan state (`.claude/plans/` contents) — currently relies on checkpoint.md
- Recent session-analyst findings — would prime for known failure modes in THIS project
- Current hook state — which hooks are active, recent trigger counts
- Cross-agent state — what selve/genomics agents are working on (beyond just PIDs)

Each of these eliminates discovery turns. The paper says this category of change has the highest marginal return.

### 3. No parent selection needed — smart agent + full history > optimization algorithm

Meta-Harness doesn't use tournament selection, crossover, or any structured search. The proposer autonomously decides what to inspect and how to modify. This beats AlphaEvolve and OPRO (which use structured optimization) on the same benchmarks.

**Implication for us:** Don't build a formal optimization loop. Keep the current approach: smart agent (session-analyst/design-review) with access to rich history. The leverage is in the HISTORY QUALITY, not the optimization algorithm. Invest in better trace storage and richer context for the analyst, not in search procedures.

### 4. The proposer's causal reasoning trajectory

TerminalBench iterations 1-2: bundled structural + prompt changes → regression. Iteration 3: proposer identifies the confound explicitly ("prompt changes caused agent to delete necessary state"). Then isolates variables.

**This is our build-then-undo pattern.** The paper shows it's a natural phase of harness search — not a bug but a feature, IF the proposer can diagnose the confound. The critical requirement: the proposer must have access to the TRACE of what went wrong, not just "score went down."

### 5. 400x context budget

Meta-Harness uses 10M tokens per iteration. OPRO uses 2K. The claim: you can't compress away the causal signal. More context = better proposals.

**Our session-analyst currently uses ~50K tokens of compressed transcript per session.** The paper suggests this is 200x less than optimal. Even moving to 500K (10 full sessions raw) could significantly improve diagnostic quality.

### 6. Discovered harnesses are readable and transfer across models

The math harness (4-route lexical router) generalized across 5 held-out models. The text classification harness (draft-then-verify) is a clean, interpretable pattern.

**Implication:** Our harness improvements (rules, hooks) should also transfer across model versions. When Opus 4.7/5.0 ships, our harness should still work — it's about information flow, not model-specific quirks. This is a good sign for harness investment durability.

## Ideas Evaluated

### Tier 1 — High leverage, low cost, build now

**1a. Harness version provenance**

Add `harness_hash` to session receipts — SHA256 of concatenated CLAUDE.md + rules/ + hooks config + startup hook output. Stored at session start.

Why: Without this, we can't correlate harness changes with session quality. It's the join key for everything else. The paper's entire methodology depends on knowing which harness produced which outcome.

Cost: ~20 lines in receipt generation. One new column in sessions.db.
Leverage: Enables all harness-outcome analysis. Zero ongoing maintenance.

**1b. Richer startup context injection**

Expand the SessionStart hook to inject:
- `git log --oneline -5` (recent activity)
- Active plans from `.claude/plans/`
- Last 3 improvement-log findings for this project
- Hook trigger summary (last 24h)

Why: Paper proves environment bootstrapping is the #1 ROI category. Each item eliminates 1-3 discovery turns per session.

Cost: ~50 lines of shell in startup hook. Adds ~500 tokens to every session start.
Leverage: Direct session quality improvement, measurable via turn-count-to-first-productive-action.

**1c. Higher-fidelity trace input for session-analyst**

When session-analyst dispatches to Gemini for analysis, send 3-5 raw session transcripts (up to 800K tokens) instead of pre-compressed summaries. Let Gemini do the compression.

Why: The ablation. 50% vs 34.9%. The model doing the analysis should see the raw data, not our summary of it. Gemini 3.1 Pro has 1M context — we're severely underusing it.

Cost: Modify session-analyst skill to concat raw JSONL instead of pre-compressing. ~30 lines.
Leverage: Potentially +15pp improvement in diagnostic quality (extrapolating from paper's ablation). This is the single biggest expected gain.

### Tier 2 — Good, build after Tier 1 is validated

**2a. Harness-outcome correlation dashboard**

Once we have harness_hash (1a), build a SQLite view joining session receipts to session quality scores. Answer: "which rule changes correlated with fewer corrections?"

Why: Closes the feedback loop. Currently we add rules based on session-analyst findings (qualitative). This makes it quantitative.

Cost: SQLite view + dashboard.py section. ~100 lines.
Prerequisite: 1a (harness provenance) + 30 days of data.

**2b. Trace-indexed failure pattern library**

Extend improvement-log entries with structured pointers: `{session_uuid, tool_call_index, line_range}` into raw JSONL. When a failure mode recurs, the analyst can pull up the EXACT sequence from multiple sessions.

Why: The paper's proposer reads 82 files median per iteration. Our session-analyst reads compressed summaries. A failure pattern library indexed into raw traces gives the analyst comparable diagnostic depth.

Cost: Extend session-analyst output format + index script. ~200 lines.
Prerequisite: 1c (analyst already reading raw traces).

**2c. Harness changelog with before/after scores**

When a rule/hook change is committed, auto-capture the last 10 sessions' quality scores as "before." After 10 more sessions, capture "after." Append to a harness changelog.

Why: Makes harness improvement measurable. Currently we add rules and hope. This is the scored iteration loop the paper uses, adapted for our sample sizes.

Cost: Post-commit hook + scheduled comparison. ~150 lines.
Prerequisite: 1a + 2a.

### Tier 3 — Interesting, defer

**3a. Multi-variant harness A/B testing**
Maintain 2-3 competing configurations, randomly assign sessions. DEFERRED: ~5-10 sessions/day across projects → weeks for statistical significance. The per-session variance in task type would dominate any harness effect at this sample size.

**3b. Skill-level Meta-Harness loop**
Run population-based search over SKILL.md variants. DEFERRED: requires per-skill benchmarks. The paper uses standardized benchmarks (LawBench, IMO problems). We'd need to create evaluation sets. High cost, unclear leverage until we have a skill with a clean metric.

**3c. Advanced task-type routing**
Detect session type (research/coding/review) and load different rule subsets. DEFERRED: path-scoping already handles the main cases. The marginal gain over current mechanism is unclear.

**3d. Cross-project harness transfer measurement**
Formally test whether rule improvements in meta transfer to selve/genomics. DEFERRED: shared hooks already provide the transfer mechanism. Formal measurement adds value only after we have harness provenance (1a) running across projects.

## The General Principle (Confirmed)

The paper shows harness gains in text classification, math reasoning, and agentic coding — fundamentally different domains. The common thread: **model performance is bounded by information flow, and harness code controls information flow.** This is universally applicable:

- **Any agent system** (our projects): rules/hooks/skills = harness → bounds autonomy and accuracy
- **Any RAG system**: retrieval + presentation = harness → bounds answer quality
- **Any API wrapper**: prompt construction = harness → bounds task completion
- **Any multi-agent system**: orchestration logic = harness → bounds coordination quality

The paper's strongest claim: a harness improvement that works is MODEL-INDEPENDENT (the math harness transferred across 5 models). This means harness investment survives model upgrades — it's more durable than fine-tuning, RLHF, or model-specific prompt engineering.

For us specifically: we're running one of the most capable models available (Opus 4.6). **The bottleneck is not model capability — it's harness quality.** Every improvement to rules/hooks/skills/context-loading is a harness improvement. The paper gives us a formal framework and empirical validation for this claim.

## What NOT to Build

- **Formal optimization loop** (genetic algorithm, tournament selection). The paper shows a smart agent with full history beats structured optimization. Our session-analyst approach is correct.
- **Separate harness optimizer agent**. We ARE the proposer. The meta project's self-improvement cycle is already a Meta-Harness loop — just a less rigorous one. The fix is better inputs (raw traces, provenance), not a new agent.
- **Benchmark suite for our harness**. Our benchmark is real work. Synthetic benchmarks would diverge from actual usage patterns. Use session quality scores as the proxy metric.

## Recommended Sequence

1. **1a** (harness provenance) — unlocks everything, near-zero cost
2. **1b** (startup expansion) — immediate quality gain, proven #1 ROI
3. **1c** (raw traces for analyst) — biggest expected diagnostic improvement
4. Collect 30 days of provenance-tagged sessions
5. **2a** (correlation dashboard) — first quantitative harness evaluation
6. **2b/2c** as findings warrant

## Revisions

(None yet — initial memo)

<!-- knowledge-index
generated: 2026-04-08T03:37:51Z
hash: d7c5c77db551


end-knowledge-index -->
