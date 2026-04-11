# claim-bench Learnings

Append-only log of what we discovered, what failed, and where the schema needed to bend.

## 2026-04-11 — Phase 0 stub created

- Built on `inspect_ai` per `research/claim_verification_package_prior_art_2026-04-11.md` consume verdict.
- Two cross-domain gold cases written: CRISPR (supported), vitamin C / cold (contradicted). Cross-domain on purpose — defer genomics-specific cases until the schema is stress-tested.
- `verdict_enum_scorer()` returns a `Score` with value, answer, explanation, and metadata. Inspect's `Score` type accepts arbitrary metadata dicts so cards can attach later.
- Solver is the bare minimum: `system_message(VERDICT_PROMPT)` + `generate()`. No retrieval, no decomposition. Phase 1 will replace the solver with a real `chain(retrieve, ground, adjudicate)`.

### Open questions for Phase 0 probe run

1. Does the EvalLog metadata structure include enough fields to derive an independence card without pre-processing?
2. Is `Score.metadata` preserved through to the EvalLog, or does it get coerced/lost?
3. How does inspect_ai render multi-class scoring? (Default `mean()` aggregation may be wrong for a 5-class verdict — accuracy or per-class confusion may be better.)
4. Does the `scorer.py` import path work cleanly from `task.py` when the Task is invoked via `uv run inspect eval experiments/claim-bench/task.py`?

These are exactly the questions the probe is supposed to answer. Don't pre-solve them.

## 2026-04-11 — Phase 0 probe run, all four questions answered

**Result:** ✓ Probe ran end-to-end. `mean=1.000` on 2/2 samples in 3 seconds, 412 tokens total via `openai/gpt-4o-mini`. Eval log: `logs/2026-04-11T17-35-55-00-00_claim-verification-probe_*.eval`.

**Q1 — EvalLog metadata structure:** YES, sufficient. `Sample.metadata` is preserved end-to-end. Arbitrary keys work — our `domain`, `claim_type`, `verifiability`, `difficulty`, `gold_sources`, `gold_contradict_sources` all roundtrip cleanly into `log.samples[i].metadata`. `log.eval.task_args`, `log.eval.created`, `log.plan.steps`, and `log.stats.model_usage` (cost) are also available at the top level. Independence + adequacy cards (Phase 4) can derive from these without schema changes.

**Q2 — `Score.metadata` preservation:** YES. Our scorer wrote `{'gold': ..., 'predicted': ..., 'in_enum': bool, 'match': bool}` and all four keys came through intact in `log.samples[0].scores['verdict_enum_scorer'].metadata`. Arbitrary scorer metadata is safe.

**Q3 — Multi-class scoring rendering:** Adequate for Phase 0. Default `mean()` aggregation works correctly for binary 0/1 verdict-match. For Phase 2+ we'll want a custom multi-class metric (per-class precision/recall, confusion matrix) — `inspect_ai.scorer.metric` supports custom metrics. Not a blocker.

**Q4 — Import resolution:** YES. `from scorer import verdict_enum_scorer` (relative bare import) works in `task.py` because `inspect eval` adds the task file's directory to `sys.path` automatically. No `__init__.py` or sys.path manipulation needed. Pyright complains because `experiments/claim-bench/` isn't part of the agent-infra package — false positive, ignore (pattern: `feedback_pyright_unresolvable_imports.md`).

### Net Phase 0 verdict

The inspect_ai abstraction is the right shape. **Nothing in the architecture needs to change.** Phase 1 (real solver + retrieval `@tool` adapters) can start without rework. The 5-class verdict enum maps cleanly onto inspect_ai's `Score.value` (0/1 match) + `Score.answer` (predicted enum string) + `Score.metadata` (gold + match details). Cards will derive from `EvalLog` metadata without schema extensions.

### Surprises

- gpt-4o-mini got both cases right with no retrieval. The CRISPR case is recallable from training data; the vitamin C case is too. Phase 1 needs harder cases that REQUIRE retrieval — otherwise we're testing memorization, not verification. Add at least 2 cases citing post-2024 evidence the model couldn't have seen.
- The default `inspect eval` log directory is `./logs/`. Add to `.gitignore` so eval logs don't pollute the repo.
- `inspect eval --no-sandbox` is not a flag — sandbox defaults are fine for our text-only task. `--sandbox` opts in.

### Next concrete actions for Phase 1

1. Add 2 cases citing 2025-2026 evidence that would not be in gpt-4o-mini training data (e.g., a 2025 retraction, a 2026 trial result)
2. Build `tools.py` with at least one `@tool` wrapper around an existing MCP (start with Exa via the user-scope mcp__exa__web_search_advanced_exa)
3. Replace the `generate()`-only solver with `chain(retrieve_evidence, ground_claim, adjudicate_verdict)`
4. Re-run the probe; confirm it now hits external APIs and the verdict reflects retrieved evidence
5. Add a `gold_source_hit@k` retrieval metric so we can score retrieval independent of verdict
