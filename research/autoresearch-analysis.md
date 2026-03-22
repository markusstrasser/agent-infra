---
title: Autoresearch Analysis — Evolutionary Code Search with LLM-as-Mutator
date: 2026-03-08
---

# Autoresearch Analysis — Evolutionary Code Search with LLM-as-Mutator

**Date:** 2026-03-08
**Source:** [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (7K stars, 2 days old)
**Cross-model review:** `.model-review/2026-03-08-autoresearch-adaptation-50b6d5/`

## Core Pattern

Agent loop: edit code → train/eval (fixed budget) → keep (metric improved) or discard (git reset) → repeat. ~12 experiments/hour, ~100 overnight. Human edits `program.md` (the research org), agent edits `train.py` (the code).

**Four conditions for viability:**
1. Cheap, fast, unambiguous fitness function
2. Constrained search space (one file, but full code — not knobs)
3. Free reversibility (git reset)
4. Zero external consequences

**Key insight:** The LLM is not doing random search. It brings domain literature as a prior, reasons about why things failed, combines techniques. This is qualitatively different from Bayesian optimization or grid search. The search space is "all valid programs," not a predefined parameter grid.

## What's Genuinely Deep

1. **Simplicity criterion** creates evolutionary pressure toward elegance: "removing something for equal results is a win." Without this, you get a ball of mud. With it, the codebase stays clean.

2. **Git-as-experiment-tracker.** The branch IS the chain of improvements. Each kept commit's diff IS the explanation. No MLflow, no W&B. The version control system IS the experiment tracker.

3. **5-minute feedback loop.** Fast enough for the agent to develop conditional intuition. Long feedback loops kill exploration because the cost of a bad idea is high.

4. **Human = meta-optimizer, agent = optimizer.** Clean separation. The human's job is to write better `program.md`, not to do the research. This is the "instructions → tools → infrastructure" compression endpoint.

## Cross-Model Review Findings

Reviewed by Gemini 3.1 Pro + GPT-5.4 (reasoning-effort high). Both agreed on:

1. **Results ledger/telemetry should be Phase 0** — can't trust a loop you can't observe
2. **First application should be meta-native** (task-proposal ranker, stall detection) — not ARC-AGI. Benchmarks don't move the autonomy metric.
3. **Worktree isolation mandatory** — git reset in working checkout destroys human work
4. **Failed experiments must be archived** — git reset destroys discarded diffs, but those diffs contain learning
5. **Two-tier eval required** — dev metric for speed, holdout for promotion
6. **LLM-as-judge on small eval sets is statistically useless** — 1 item = 5% swing on 20 items
7. **Cost estimates underestimated 2-5x** for prompt optimization and intel applications

## Applicability to Our Domains

| Domain | Fit | Why |
|--------|-----|-----|
| ARC-AGI symbolic solver | Good | Deterministic metric, CPU-feasible, constrained space |
| Genomics variant filtering | Good | F1 on truth set, CPU-bound, one script |
| Meta-native (stall detection, proposal ranking) | Best | Directly moves autonomy metric, replay data exists |
| Prompt/skill optimization | Conditional | Only with objective scoring (exact match, schema), not LLM judges |
| Intel signal quality | Poor today | Needs retrospective eval set, noisy metrics, expensive |

## Implementation

Built `scripts/autoresearch.py` — standalone engine with:
- Worktree isolation per run
- JSONL + TSV experiment ledger
- Patch archival before git reset
- LEARNINGS.md summarization every 10 experiments
- Two-tier eval (dev + holdout)
- Stall detection (consecutive discard streak)
- Progress visualization

Validated on toy-scorer experiment (10 experiments in-session): baseline 0.7625 → 0.925 dev accuracy. 3 keepers (stemming, word-length weighting, acronym expansion), 7 discards. Key finding: targeted lexical fixes give 3-8pp each; scoring formula tweaks give 0pp; remaining ceiling requires semantic knowledge beyond keyword methods.

**Workflow validated:** The Karpathy-style loop (read state → edit → commit → eval → keep/discard → log) works in a single Claude Code session. The `/loop` command can automate this. Worktree isolation is NOT needed for the in-session case because the agent manages its own state — it's only needed for the subprocess-orchestrated case where `git reset` in main checkout would destroy unrelated work.

## Revisions

- **2026-03-08:** Removed "blocked on API credits" — validated end-to-end using Claude Code subscription (in-session loop, no subprocess orchestrator needed). Updated implementation status.

<!-- knowledge-index
generated: 2026-03-22T00:15:42Z
hash: 1f58856e0f58

title: Autoresearch Analysis — Evolutionary Code Search with LLM-as-Mutator

end-knowledge-index -->
