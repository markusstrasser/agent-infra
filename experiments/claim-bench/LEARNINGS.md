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

## 2026-04-11 — Phase 1 complete (retrieval + post-cutoff cases + groundedness)

**What shipped:**

- 2 new post-cutoff cases (`cases/003_supported_pair_instability_gap_gwtc4.json` citing DOI `10.1038/s41586-026-10359-0` / arXiv:2509.04151 both post-May-2025; `cases/004_contradicted_kotz_climate_19pct.json` citing DOI `10.1038/s41586-025-09726-0` retraction dated 2025-12-03). Both verified by direct publisher HTML fetch.
- `tools.py` with `@tool exa_search()` wrapping `exa_py.AsyncExa` directly (not the MCP layer, per handoff guidance). Hard budget cap of 50 calls/process, `start_published_date`/`end_published_date` args, trimmed to 1500 chars/result. Manual test query returned the CRISPR 2015 paper correctly at 1 call.
- `task.py` solver chain replaced: `[system_message, use_tools(exa_search()), generate()]`, message_limit=40. Prompt updated to instruct retrieval use and date filtering. `generate()` auto-loops on tool calls with no manual chain needed — confirmed.
- `scorer.py` adds `groundedness_scorer()` — cross-family LLM judge (`google/gemini-2.5-flash` by default, override with `CLAIM_BENCH_JUDGE_MODEL`). Extracts tool-call trace from `state.messages` (walks `ChatMessageAssistant.tool_calls` and `ChatMessageTool` results), prompts judge with claim + verdict + trace, parses into `grounded` / `partial` / `ungrounded`.
- Google provider dependency added (`uv add google-genai`) to enable Gemini judge — required `GOOGLE_API_KEY` at runtime (session has `GEMINI_API_KEY`; Gemini SDK reads `GOOGLE_API_KEY` first).

**Phase 1 eval results (4 cases, openai/gpt-4o-mini SUT, google/gemini-2.5-flash judge):**

| Case | Verdict | Match | Groundedness | Tool calls | Note |
|---|---|---|---|---|---|
| 001 CRISPR 2015 | supported | ✓ | partial (0.5) | 1 | Judge flagged "first use" as unconfirmed |
| 002 vitamin C cold | contradicted | ✓ | grounded (1.0) | 1 | Clean success |
| 003 pair-instability gap | supported | ✓ | **grounded (1.0)** | 2 | Retrieval found Tong et al. 2026 Nature paper — confabulated without retrieval, grounded with it |
| 004 Kotz climate retraction | supported (WRONG — gold: contradicted) | ✗ | partial (0.5) | 1 | Failure mode: model retrieved the pre-retraction PDF, missed the retraction notice |

`verdict_enum_scorer` mean 0.750, `groundedness_scorer` mean 0.750. Total 28s, 17K SUT tokens (vs 956 pre-retrieval), 15K judge tokens.

**Groundedness agreement with hand-grading: 3/4 (exit criterion met).** Disagreement on case 004 — judge said partial, hand says ungrounded (the model cited specific numerical details like "38 trillion" that were present in the retrieval trace, so the judge was technically defensible, but the deeper failure is that the retrieved source is a pre-retraction PDF, not a current-state-of-record).

**Critical findings:**

1. **Case 003 validates the retrieval value story.** Without retrieval, gpt-4o-mini said "supported" with generic hedge text (confabulating). With retrieval, it found the actual Tong et al. 2026 Nature paper and cited the 44 M_sun number. This is the clearest demonstration that retrieval + groundedness together measure something verdict-match-alone cannot. **The bench is now falsifiable on the retrieval axis.**

2. **Case 004 exposes a currency failure.** The model ran one query (`"Kotz Levermann Wenz 2024 Nature paper The economic commitment of climate change"` with `start_published_date=2024-01-01`), got the pre-retraction PDF hosted at pik-potsdam.de, confidently said "supported". It did NOT run a second query for "retraction" because the claim text deliberately doesn't mention retraction — which is precisely what real-world inherited misinformation looks like. **The retrieval pushed gpt-4o-mini from honest abstention (insufficient_evidence without retrieval) to confident overclaim (supported with retrieval)** — a net regression under strict verdict-match, a net win under the argument that "the model is at least reading a primary source now". This is the Currency scorer gap Phase 2 should address.

3. **Case 003 without retrieval was still a false positive (lucky guess).** Verdict-match alone is a noisy signal when claims assert plausible-sounding facts — the model can hedge toward "supported" and be right by accident. Groundedness catches this: pre-retrieval = no trace = ungrounded. Verdict + groundedness as a joint metric is strictly more informative than either alone.

4. **Exa's `start_published_date` filter works as expected** but does nothing for claims whose challenge is about the CURRENT status of an older paper. Filtering by date narrows the corpus but doesn't prioritize "latest update about X" — that requires either a second query targeting retractions or a different ranking signal.

5. **Google provider env var is `GOOGLE_API_KEY`**, not `GEMINI_API_KEY`. The google-genai SDK actually reads both but prefers `GOOGLE_API_KEY`. For scheduled runs we should `export GOOGLE_API_KEY=$GEMINI_API_KEY` or patch the settings.

6. **Pyright false-positive pattern still applies** — `experiments/claim-bench/` isn't part of the agent-infra package, so Pyright cannot resolve `inspect_ai`, `exa_py`, or the sibling imports. Expected; ignore. Add to `pyproject.toml` exclude or leave as-is.

**Deferred to Phase 2:**
- **Currency/provenance scorer.** Check whether retrieved sources are the current state of record (e.g., flag pre-retraction articles, flag superseded guidelines). The case 004 failure mode directly motivates this.
- **Retrieval recall metric** (`gold_source_hit@k`). Did the agent actually retrieve the gold source? Orthogonal to verdict and groundedness.
- **Calibration scorer.** Is the model's confidence well-calibrated to its actual accuracy?
- **Trace faithfulness scorer.** Do the agent's stated citations match what's actually in the trace?
- **AutoVerifier 6-layer decomposition.** Current chain is 3-step (system → tools → generate). Extending to `extract → intra_doc → cross_source → corroborate → matrix` requires architectural decisions the user should make.
- **Multi-query retrieval policy.** Case 004 failed because the model ran one query. A default "run at least 2 queries with different angles" policy may help but needs validation.

**Gotchas next session should know:**

- Run the eval with `GOOGLE_API_KEY="$GEMINI_API_KEY"` prefixed, or export it — inspect_ai's google provider reads `GOOGLE_API_KEY`.
- Anthropic credit balance was exhausted at Phase 1 start; Google Gemini is the working judge. If both are unavailable, the cross-family rule blocks you — don't fall back to `openai/gpt-4o-mini` as its own judge.
- `message_limit=40` in the Task handles tool-call loop caps without custom code. Adjudication fits in <20 turns in practice.
- `scorer=[verdict_enum_scorer(), groundedness_scorer()]` (list) works — inspect_ai runs multiple scorers per sample and reports each as its own metric column.
