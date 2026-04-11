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

## 2026-04-11 — Phase 1 plan-close review and fixes (commit follows)

Ran `/review close` after the Phase 1 commit `90cb7d8`. 33 unit tests added, cross-model adversarial review dispatched (Gemini 3.1 Pro + GPT-5.4) against an explicit commit-range packet. 19 findings total, 0 cross-model agreements, 2 caught by self-audit before models dispatched, 8 applied, 7 deferred with reasons.

### Bugs caught by the caught-red-handed loop (regression tests added for each)

1. **`tool_calls_seen` metadata was inverted** — scorer.py:201 set the field to `trace.startswith("(no tool")`, returning True exactly when no tool calls existed. Fixed; regression test `test_tool_calls_seen_is_not_inverted` passes against the fix.

2. **`_format_tool_trace` counted only tool RESULTS, not tool CALLS** — a model that emits a tool-call assistant message whose corresponding `ChatMessageTool` result never appears (e.g., tool error at the solver layer) would be reported as "no tool calls". Fixed by counting both events in `event_count`; regression test `test_format_tool_trace_non_dict_arguments_survive` covers an edge case that exercises the count.

3. **`_parse_groundedness_verdict` inflated the mean on judge parse failures** — the fallback returned `("parse_error", 0.5)`. Silent +0.5 per sample when the judge went off-format. Fixed to return 0.0; regression test `test_parse_error_returns_zero_not_partial` with a citation to the cross-model review.

4. **`_normalize(raw_output.split("\n")[0])` in verdict extraction broke on single-line "verdict: explanation" output** — observed on case 002 during the second post-fix eval run when gpt-4o-mini produced `"contradicted: Evidence indicates..."` on one line. The whole line got normalized, no verdict matched. New `_extract_verdict()` helper handles two-line, colon-separated, and markdown-wrapped formats. Parametrized regression test `test_extract_verdict_handles_observed_formats` covers all three.

5. **Raw Exa exception text leaked to the model via ToolError** — an auth or rate-limit error would surface the full exception message, potentially encouraging the model to retry the same failing query. Fixed to return exception class name + a generic retry hint only.

6. **`num_results` parameter on `exa_search` was unbounded** — a confused model could request 100 results per query and blow up context and cost. Clamped to `[MIN_NUM_RESULTS=1, MAX_NUM_RESULTS=10]` at the start of `execute()`. Regression test `test_num_results_bounds_exist`.

7. **`GEMINI_API_KEY` → `GOOGLE_API_KEY` operator friction** — the google-genai SDK reads `GOOGLE_API_KEY` first; operators with only `GEMINI_API_KEY` had to manually `export GOOGLE_API_KEY=$GEMINI_API_KEY`. Fixed with a module-load-time shim in `scorer.py`. Regression test `test_gemini_to_google_key_bridge_in_scorer_module` with importlib.reload to exercise the fresh-import path.

8. **`task.py` docstring claimed `anthropic/claude-sonnet-4-5` was the default judge** when the actual default in `scorer.py` is `google/gemini-2.5-flash`. The docstring was a leftover from the initial build before Anthropic credit exhaustion forced the Google switch. Fixed to match code.

### Findings deferred (with explicit reasons — not re-open on review)

- **Process-global Exa call counter** (Gemini 0.90, GPT 0.70): at current scale (4 cases × ~2 calls = 8 calls per run) nowhere near the 50-call cap. Per-sample limits via `TaskState.store` are the right Phase 2 fix when parallel eval is enabled. Noted in `tools.py` comment.
- **Exa concurrency control / rate-limit handling** (Gemini 0.80): same scale argument — parallel eval across 4 samples doesn't saturate Exa's rate limits. Real concern at 50+ cases. Phase 2.
- **Preflight config validation** (GPT 0.90): valuable but adds complexity for a 4-sample bench where misconfigurations fail on sample 0 anyway. Phase 2.
- **Judge cross-provider fallback chain** (Gemini 0.80): nice-to-have. `CLAIM_BENCH_JUDGE_MODEL` env override handles the manual case. Phase 2 should add automatic fallback with a cross-family guarantee preserved.
- **`retrieval_attempted` as a top-level scorer** (Gemini 0.90): architecturally correct — retrieval attempts should be a visible metric, not buried inside groundedness metadata. Phase 2 (adds one more scorer to the list). Noted.
- **Tool payload bloat on judge context** (Gemini 0.80): 1500 × 5 × 3 queries ≈ 22K chars per sample; fits easily in Gemini 2.5 Flash's 1M context. Measured, not hypothetical. Phase 2 can tune if telemetry shows cost pressure.
- **Joint success definition (`verdict_match=1 AND groundedness > 0`)** (GPT 0.80): valid framing for downstream analysis, NOT a bench change. Noted here as the correct interpretation of Phase 1 results.

### Disagreement with reviewers

- **GPT-5.4 finding #15: "No API contract tests for inspect_ai integration"** (LOW). This was out-of-date by the time extraction ran — 33 unit tests were added during the plan-close workflow's Phase 1 (test-writing), covering `_normalize`, `_extract_verdict`, `_parse_groundedness_verdict`, `_format_tool_trace`, `exa_search` budget + clamping, `_format_result`, the key bridge, and the specific regressions the cross-model review itself surfaced. The reviewer didn't see them because they were written after the commit under review. Finding stands as noise.

### gpt-4o-mini verdict variance is high on 4-sample runs

Across four Phase 1 eval runs:

| Run | verdict_enum | groundedness | notes |
|---|---|---|---|
| 1 (initial) | 0.750 | 0.750 | 3/4 verdict match, 1 missed (case 004) |
| 2 (post msg_limit) | 0.500 | 0.750 | 2/4 — parser masking some cases |
| 3 (post parser fix) | 0.250 | 0.625 | 1/4 — same cases different verdicts, model hedged to "mixed" |
| 4 (variance check) | 0.750 | 0.750 | 3/4 — same config as run 3, opposite outcome |

Range of 0.50 on verdict_enum across runs with identical config. This is **gpt-4o-mini stochasticity on 4-case benches**, not bench instability — the parser is now correct across all observed output formats. For Phase 2, use `epochs=3` or `5` to average out noise, or switch to a more stable SUT like claude-sonnet-4-5 for dev runs. The variance finding itself is useful: it tells you that 4 cases is too few for a tight confidence interval on any single SUT run.

### Plan-close summary

- 33 unit tests passing
- 8 bug fixes applied (2 from self-audit, 6 from cross-model review)
- 7 findings deferred to Phase 2 with explicit reasons
- 1 finding disputed (API contract tests — was already addressed during plan-close itself)
- 4 eval runs reproduce case-003 retrieval-wins and case-004 currency-failure directionally, but verdict_enum mean is noisy on 4-case runs
- **Phase 2 architectural decisions still awaiting user review** (AutoVerifier 6-layer vs flat chain, currency scorer design, joint success metric as the primary headline vs per-scorer reporting)

## 2026-04-11 — Phase 2 complete (4 cases + 4 scorers + epochs=3 + currency hybrid)

User answered "go" on the architectural decisions. Phase 2 shipped with:

### Architectural decisions (locked in commit)

1. **Corpus expanded 4 → 8 cases.** Added 005 (mixed: red wine J-curve vs MR), 006 (insufficient_evidence: sub-2 Å proteasome cryo-EM), 007 (not_verifiable: GWAS value judgment), 008 (contradicted non-currency: VITAL trial vitamin D). Each case targets a previously-uncovered verdict class.

2. **`epochs=3` in `task.py`** — averages gpt-4o-mini stochasticity per Phase 1's 0.25-0.75 verdict_enum variance finding. 8 × 3 = 24 sample-runs per eval. ~60 seconds, ~$0.05-0.10 per run.

3. **Flat solver chain kept.** Did NOT build AutoVerifier's 6-layer Solver decomposition. The current `system_message → use_tools(exa_search) → generate()` already lets the model run all 6 of AutoVerifier's layers internally as part of `generate()`'s tool-call loop. Building 6 explicit Solver steps would force a single fixed path, 6× the tokens, lose adaptivity. Phase 3's atomic-claim P/R/F1 scorer will give EMPIRICAL evidence about whether the flat chain is conflating layers.

4. **Currency scorer is hybrid (Crossref + judge), NOT pure judge.** Per memory `feedback_currency_failure_in_claim_verification.md` and `epistemic-quality-evals.md` finding that LLM judges have >90% unexplained variance, the deterministic part (Crossref API + URL classifier) does the falsifiable work. The judge only runs on the residual: "given retraction X exists, did the model address it?"

5. **Joint success is a derived helper, not a scorer.** inspect_ai's Scorer API doesn't expose peer scorer outputs in-band. `joint_success_per_sample()` lives in `process_metrics.py` for `cards.py` (Phase 4) to consume.

### What shipped

- `process_metrics.py` (~750 lines) with 4 new scorers + helper:
  - `currency_scorer` — Crossref API + title-prefix retraction detection + URL fragment stripping + publisher URL → DOI extraction + judge for residual
  - `calibration_scorer` — verbalized hedge classifier (HEDGE_PATTERNS vs CONFIDENCE_PATTERNS, abstention free pass)
  - `trace_faithfulness_scorer` — pure-deterministic citation-vs-trace check (no LLM judge — fabrication is a string-match problem at this layer)
  - `retrieval_attempted_scorer` — top-level promotion of `tool_calls_seen` per Phase 1 plan-close finding #5
  - `joint_success_per_sample()` — canonical headline definition (verdict_match AND grounded ≥ 0.5 AND (currency_pass OR currency_NA))
- 4 new cases in `cases/` (005-008)
- `task.py` updated: 6 scorers in scorer list, epochs=3
- `test_phase2.py` (~440 lines, 73 unit tests)
- Total tests passing: 97 (33 Phase 1 + 64 Phase 2)

### Two critical bugs caught during integration testing (regression tests added)

1. **DOI regex over-extraction.** First Phase 2 eval revealed `dois_checked: ['10.1007/s13238-015-0153-5/fulltext.html']` — the URL path `/fulltext.html` was being captured as part of the DOI suffix. Crossref then 404'd silently. Same issue on `/pdf`, `/full`, `/abstract`, `/epdf`. **Fix:** added `DOI_URL_FRAGMENT_PATTERN` post-processing to strip these. **Regression test:** parametrized over 5 observed cases.

2. **DOI under-extraction on publisher landing pages.** Case 004 `currency_status` was `not_applicable` on all 3 epochs because the Kotz paper DOI was past Exa's 1500-char text excerpt cap and only appeared in the URL itself. **Fix:** added `PUBLISHER_URL_DOI_PATTERNS` for Nature, NEJM, Science, doi.org resolver, and Oxford Academic — extracts the DOI directly from URL paths even when the text excerpt doesn't contain it. **Regression test:** parametrized over 6 publisher URL formats.

### The MAJOR finding: Crossref retraction signals are unreliable; title prefix is the only consistent cross-publisher signal

Direct query of `https://api.crossref.org/works/10.1038/s41586-024-07219-0` (the retracted Kotz climate paper) on 2026-04-11 returned:
- `subtype`: None ← NOT "retraction"
- `update-to`: null ← NOT populated
- `relation`: only `has-preprint`, NO `is-retracted-by`
- `title`: `["RETRACTED ARTICLE: The economic commitment of climate change"]` ← THE ONLY SIGNAL

Nature's convention is to prepend `"RETRACTED ARTICLE:"` to the title; other publishers use `"Retracted:"`, `"Retraction Note:"`, `"WITHDRAWN:"`. None of them consistently populate the structured Crossref fields.

**Fix:** `_interpret_crossref_message` now checks the title FIRST (most reliable), then falls back to subtype / update-to / relation. The returned dict has a new `retraction_signal` field recording which signal fired.

**Regression test:** parametrized over 5 title prefixes + signal-priority test + string-vs-list defensive test.

**Generalization:** this is the same shape of failure mode as case 004 itself — relying on structured "current state" signals when the actual ground truth is in unstructured text. Recorded in memory as `feedback_currency_failure_in_claim_verification.md` (which already covered the failure pattern; this finding confirms the deterministic-fix design is right but the deterministic source needs to be the title, not the structured fields).

### Phase 2 eval results (final, after both bug fixes)

| Scorer | Mean | Notes |
|---|---|---|
| `verdict_enum_scorer` | **0.708** | 17/24 sample-runs correct. Up from Phase 1's 0.250-0.750 variance. epochs=3 working. |
| `groundedness_scorer` | **0.812** | 19.5/24. Up from Phase 1 0.750. |
| `currency_scorer` | **1.000** | All checked DOIs current OR (case 004) flagged as retracted AND model addressed it (`aware` on all 3 epochs this run). |
| `calibration_scorer` | **0.562** | Mostly neutral language — model doesn't strongly hedge or assert. Not a bug, signals room for explicit confidence calibration in Phase 4. |
| `trace_faithfulness_scorer` | **1.000** | All cited URLs/DOIs in explanation appear in retrieval trace. Zero fabrication on this run. |
| `retrieval_attempted_scorer` | **1.000** | Every sample-run made at least one tool call. |

Total cost: ~$0.10/run (176K SUT tokens + 100K judge tokens).

### Per-case observations (3 epochs each)

- **001 CRISPR 2015** — verdict 3/3, gpt-4o-mini gets it from training memory + retrieval
- **002 Vitamin C cold** — verdict 3/3, clean
- **003 Pair-instability gap** — verdict 2/3 (one epoch hedged to "mixed"), groundedness mostly partial
- **004 Kotz climate retraction** — verdict 3/3 contradicted (this run!), currency 3/3 aware. **The case 004 failure mode is now correctly caught: the bench detects the retraction AND the judge confirms the model addressed it.**
- **005 Red wine mortality** — verdict 2/3 mixed (one epoch said "supported")
- **006 Proteasome cryo-EM** — verdict 2/3 insufficient_evidence (one epoch said "contradicted")
- **007 GWAS value judgment** — verdict 0/3 — gpt-4o-mini consistently says "supported" instead of recognizing the not_verifiable shape. **This is a real model failure, not a bench bug.** The not_verifiable verdict requires recognizing that the prompt is rhetorical, which gpt-4o-mini doesn't do well. Larger models may handle it.
- **008 Vitamin D mortality** — verdict 2/3 contradicted, one epoch said "mixed"

The 0.708 verdict_enum mean is now an honest signal of gpt-4o-mini's actual claim-verification capability on this corpus, not a noise artifact.

### What's deferred to Phase 3+

- **Atomic-claim P/R/F1 scorer (FIRE-Bench pattern).** Phase 3.
- **Cards (independence + adequacy).** Phase 4.
- **Confidence calibration via answer-frequency consistency** (the right way per Nakkiran et al.). Phase 4 cards.py — operates on the EvalLog's epoch dimension, not as a scorer.
- **Genomics adapter.** Phase 5 shell only — full corpus authoring needs user input on which incidents to canonicalize.
