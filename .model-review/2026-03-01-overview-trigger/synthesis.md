# Cross-Model Review: Overview Trigger Mechanism

**Mode:** Review (critical)
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (CLAUDE.md Constitution + GOALS.md)
**Extraction:** 22 items extracted, 17 included, 2 deferred, 1 rejected, 2 merged

## Verified Findings (adopt)

| ID | Finding | Source | Verified How |
|----|---------|--------|-------------|
| G1, P1, P2 | LOC is a bad proxy for arch significance | Both | Obviously true — 1-line schema change vs 500-line formatting |
| G3, P5, P10 | Per-overview-type triggering needed | Both | 1 trigger = 3 overviews is a 3x cost multiplier for no reason |
| G4, P8, P15 | Measure before deploying thresholds | Both | Constitutional: "Log every hook trigger to measure false positives" |
| G6 | Path-based scoping via git diff --name-only | Gemini | Deterministic, zero-cost, enables per-overview routing |
| G8 | Shadow mode first (log decisions, don't generate) | Gemini | Best path to constitutional compliance |
| P9 | Composite trigger: structural signals + LOC | GPT | Fixes core gap — renames, file adds are low-LOC high-impact |
| P11 | Preview gate: skip test/docs/formatting | GPT | Low-cost FP reduction |
| P12 | Time decay via cron, not SessionEnd | GPT | Solves genomics bursty-quiet pattern |
| P14 | Testable metrics spec for logging | GPT | Implementation spec for measurement phase |

## Deferred (with reason)

| ID | Finding | Why Deferred |
|----|---------|-------------|
| G5 | LLM router (Flash as semantic judge) | Flash sycophancy risk (G11). Adds LLM dependency to trigger. Only evaluate if deterministic signals prove insufficient after logging phase |
| G7 | AST/structural diffing (difftastic) | Tool dependency. Evaluate if LOC + structural signals insufficient |

## Rejected (with reason)

| ID | Finding | Why Rejected |
|----|---------|-------------|
| G10 | Drop time decay entirely | GPT's cron point (P12) is stronger — bursty projects (genomics: weeks quiet, then burst) need a staleness cap. Without it, overview stays stale forever during quiet periods after a burst |

## Where I Was Wrong

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|
| "Lines-changed threshold is the sweet spot" | LOC is a broken proxy — misses renames, config, and feature flags; over-triggers on formatting | Both models |
| "Time decay via SessionEnd" | SessionEnd doesn't fire during quiet periods — need cron for actual guarantee | GPT |
| "One trigger fires all 3 overviews" | Per-overview scoping cuts cost 2-3x with zero staleness penalty | Both models |
| "50 lines is a reasonable threshold" | Magic number without data violates "measure before enforcing" | Both models |

## Gemini Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| "Drop time decay entirely" | Wrong — ignores the quiet-after-burst case. Gemini's reasoning ("if untouched, architecture unchanged") is circular: the burst may have changed architecture, and no sessions fire to trigger detection |
| Flash LLM router recommendation | Interesting but premature — adds complexity and LLM dependency. The sycophancy risk Gemini self-flagged is real |

## GPT Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| Quantitative cost-benefit numbers | All synthetic — acknowledged. Framework is sound but specific numbers ($0.197/wk etc.) are fabricated. Don't use for threshold selection |
| "Material change rate" estimates per project | Guessed from qualitative descriptions. Need actual logs |

---

## Revised Recommendation

### Architecture: Two-Stage Deterministic Trigger

**Stage 1: Route (free, instant)**
```
git diff --name-only <marker>..HEAD
  → classify each file into overview scope:
    - src/**          → SOURCE_ARCH
    - scripts/*, hooks/*, *rc, bb.edn, *.config.* → DEV_TOOLING
    - file adds/deletes/renames (any scope)        → PROJECT_STRUCTURE
    - test/*, *_test.*, docs/*, *.md               → SKIP (no overview impact)
```

**Stage 2: Per-scope composite trigger**
For each scope that has changes:
```
REGENERATE if ANY of:
  - files_added + files_deleted + renames >= 1  (structural change)
  - dependency/config file touched               (tooling change)
  - LOC_changed > T                              (volume threshold, TBD from data)
```

**Stage 3: Execute**
- Generate ONLY the overview types whose scope was triggered
- Background, async, non-blocking (nohup from SessionEnd)
- Use Flash model (cheap/fast), not Pro

**Staleness safety net:**
- Daily cron (or orchestrator tick): check each repo for changes since last overview > 7 days
- If stale + any changes exist → regenerate in background

### Implementation Order

1. **Shadow mode (week 1-2):** Log trigger decisions to JSONL without generating. Metrics per P14: repo, timestamp, diff_lines, diff_files, diff_renames, paths_hit, which_overviews_would_fire. This satisfies constitutional "measure before enforcing."

2. **Tune thresholds (end of week 2):** Plot FPR/FNR vs LOC threshold. Pick Pareto point. Validate structural signals (renames, adds) catch the surgical-change cases.

3. **Enable generation (week 3+):** Switch from logging to actual generation. Per-overview-type. Flash model.

4. **Evaluate LLM router (future):** Only if deterministic signals show persistent FP/FN gaps that LOC + structural signals can't fix.

### Key Design Decisions

- **No LLM in the trigger path** (for now). Deterministic signals are cheaper, faster, more predictable. LLM router deferred until data shows it's needed.
- **Per-overview scoping is the single biggest win.** Both models independently identified this. Cuts generation cost 2-3x with zero staleness penalty.
- **Measurement first is constitutionally required.** The 50-line threshold was a guess. 2 weeks of logging will produce the actual number.
- **Cron for staleness, not SessionEnd.** SessionEnd only fires when sessions happen. Quiet projects (genomics) need an independent check.
