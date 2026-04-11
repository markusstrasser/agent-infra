# Handoff — claim-bench, Phase 1 entry

**For:** the next agent session continuing this build.
**Written:** 2026-04-11 by the Phase 0 session.
**Context:** you are the second session on this project. Phase 0 probe is done and successful. You are starting Phase 1. Your job is to replace the placeholder solver with a real retrieval → ground → adjudicate chain, add 2 post-training-cutoff cases, and wire in a groundedness scorer. Stop and check in with the user after Phase 1 exits — do not continue to Phase 2 without review.

---

## TL;DR — 60 seconds

1. You are in `~/Projects/agent-infra/experiments/claim-bench/` building a claim-verification benchmark on top of `inspect_ai` (UK AISI, MIT). We consume inspect_ai, we do not rebuild it.
2. Phase 0 proved the harness shape works: `task.py` + `scorer.py` + 2 JSON cases ran end-to-end against `openai/gpt-4o-mini`, scored 2/2 with `mean=1.000`. Nothing in the architecture needs to change.
3. Your next concrete job is Phase 1: real solver with retrieval, 2 post-cutoff cases, and a groundedness scorer. Five specific actions below.

---

## Authoritative reading order

Read these in order. Do not skim — each answers a question you will otherwise re-derive.

1. **`PLAN.md`** (this directory) — the full build plan. Phases 0-6, vetoed approaches, open gaps, what lives where, when to extract a package. This is the canonical contract.
2. **`LEARNINGS.md`** (this directory) — append-only log of what the Phase 0 probe revealed. Contains the four questions I had going in and how the probe answered them. Also contains the surprise that motivates action #1 below.
3. **`README.md`** (this directory) — orientation + run instructions.
4. **`~/Projects/agent-infra/research/claim_verification_package_prior_art_2026-04-11.md`** — why we consume inspect_ai + FIRE-Bench instead of building a new framework. The three-paragraph "Bottom Line" is enough; skim the tables if you need per-framework verdicts.
5. **`~/Projects/agent-infra/research/agent_harness_scientific_truth_review_2026-04-10.md`** — the Feb-Apr 2026 paper scan. Read the section on FIRE-Bench (atomic-claim P/R/F1 pattern you will use in Phase 3) and AutoVerifier (the 6-layer verification shape).
6. **`~/Projects/agent-infra/research/factual-verification-systems.md`** — what's known about SAFE/FActScore/VeriScore/FINCH-ZK/Claimify. Don't re-research.
7. **`~/Projects/agent-infra/research/epistemic-quality-evals.md`** — SeekBench's Groundedness/Recovery/Calibration triple. This is the template for your Phase 2 process metrics.

Skip `benchmarking-science-2026.md` unless you hit a meta-validity question in Phase 4 (cards).

---

## You are here (state at 2026-04-11)

**Phase 0 DONE.** Commits in agent-infra:
- `01eed63` — prior-art research memo
- `fe4d561` — relocated Apr 10 paper scan from genomics
- `6bc4be0` — Phase 0 probe scaffold + 2 cases

**Phase 0 probe ran successfully:**
```
claim_verification_probe (2 samples): openai/gpt-4o-mini
total time:             0:00:03
openai/gpt-4o-mini      412 tokens
verdict_enum_scorer
mean                 1.000
```

**What exists:**
- `task.py` — inspect_ai `@task` with `system_message(VERDICT_PROMPT)` + `generate()` solver. No retrieval yet.
- `scorer.py` — `verdict_enum_scorer()` returning a `Score` with `{gold, predicted, in_enum, match}` metadata.
- `cases/001_supported_crispr_2015.json` — CRISPR-2015 paper. Verdict: supported.
- `cases/002_contradicted_vitamin_c_cold.json` — Cochrane meta-analysis on vitamin C / cold prevention. Verdict: contradicted.

**What does NOT exist yet:** `tools.py` (retrieval @tool wrappers), `process_metrics.py` (groundedness/calibration/trace faithfulness), `cards.py` (independence + adequacy cards), any genomics adapter.

**Critical surprise from Phase 0:** gpt-4o-mini got both cases right **with no retrieval**. Both cases are recallable from training data. This means the Phase 0 probe did NOT exercise retrieval or verification — it measured memorization. Phase 1 **must** add cases where the model cannot win from training alone, otherwise you are scoring the wrong axis.

---

## Phase 1 — Next 5 concrete actions

Do these in order. Each has a defined exit. Do not merge them — they are sequenced so each failure mode is isolated.

### Action 1 — Add 2 post-cutoff cases (before any code)

Write 2 new cases citing evidence the current frontier models could not have seen. Target window: 2025-06 through 2026-04. Name them:
- `cases/003_supported_<slug>.json`
- `cases/004_contradicted_<slug>.json`

**Why first:** without these, every subsequent retrieval/solver change is unfalsifiable. You cannot tell if the model won because retrieval worked or because it memorized. Gate the rest of Phase 1 on having these cases.

**Sources to draw from:**
- 2025-2026 Cochrane review updates (search cochranelibrary.com, date filter)
- 2025-2026 retractions (pubpeer.com, retractiondatabase.org)
- 2025-2026 trial readouts (clinicaltrials.gov → completed → published after training cutoff)
- Recent papers in this agent-infra corpus that cite post-cutoff findings

**Rule:** each case must cite at least one DOI or arXiv ID published ≥ 2025-10. The claim text itself can reference anything, but the *gold evidence* must be post-cutoff.

**Exit:** 4 cases total in `cases/`. Re-run the probe without retrieval (just `generate()`) and confirm the new cases are harder — mean should drop. If gpt-4o-mini still hits 4/4, the cases aren't hard enough.

---

### Action 2 — Build `tools.py` with one retrieval tool

Start with one tool only: `@tool exa_search()`. Wrap the user-scope Exa MCP (`mcp__exa__web_search_advanced_exa`). Do NOT wrap all five (Exa/scite/S2/Perplexity/Brave) — one is enough to prove the adapter pattern works.

**Signature:**
```python
from inspect_ai.tool import tool, Tool

@tool
def exa_search() -> Tool:
    async def execute(query: str, max_results: int = 5, start_date: str | None = None) -> str:
        """Search the web via Exa. Returns top-k results as a JSON string."""
        # Implementation — call the Exa MCP or exa-py directly (exa-py is in pyproject)
```

**Gotcha:** `exa-py` is already in `pyproject.toml` (line 9). Use it directly instead of going through the MCP layer — MCPs are for interactive tool use, not adapter code. See `mcp-usage.md` rule in `~/Projects/agent-infra/.claude/rules/` if it exists, or use the pattern from `research/search-api-integration-landscape.md`.

**Cost guardrail:** set a hard budget on Exa calls per eval run. 20 results × 4 cases × 5 queries each = 400 calls worst case at ~$0.005/call = $2. Acceptable for dev. Add a counter and assertion.

**Exit:** `tools.py` exists, `@tool exa_search()` returns valid JSON for a manual test query.

---

### Action 3 — Replace the placeholder solver with `chain(retrieve → ground → adjudicate)`

Edit `task.py`. The solver becomes a chain of three solvers:

```python
from inspect_ai.solver import chain, use_tools, generate, system_message

solver=[
    system_message(VERDICT_PROMPT),
    use_tools(exa_search()),
    generate(),  # model now has access to exa_search tool
]
```

`generate()` with `use_tools()` makes the model call the tool autonomously. No manual chain needed at this stage — inspect_ai handles the tool loop.

**For Phase 1 this is enough.** AutoVerifier's 6-layer decomposition (extract → intra-doc → cross-source → corroborate → matrix) is Phase 2+ territory. Don't pre-build it.

**Exit:** re-running `uv run inspect eval experiments/claim-bench/task.py --model openai/gpt-4o-mini` shows tool calls in the EvalLog and the post-cutoff cases score higher than they did without retrieval.

---

### Action 4 — Add a groundedness scorer

Write a second `Scorer` in `scorer.py` (or split into `process_metrics.py` now — your call):

```python
@scorer(metrics=[mean()])
def groundedness_scorer() -> Scorer:
    """Score whether the model's verdict is actually supported by the
    retrieved evidence it cited, not hallucinated.
    
    This is an LLM-judge scorer — use cross-family (GPT or Gemini) to
    judge Claude outputs, never Claude-on-Claude.
    """
```

**Mechanism:** given the Sample, the model's predicted verdict + explanation, and the tool-call results from the EvalLog, ask a *different-family* judge model: "Does the cited evidence actually support this verdict?"

**Model routing for this scorer:** see the §Model routing section below. If the Task runs with `--model openai/gpt-4o-mini` as the solver, the groundedness judge should be `anthropic/claude-sonnet-4-6` or `google/gemini-3-flash-preview`. Never same-family.

**Exit:** `groundedness_scorer` runs alongside `verdict_enum_scorer` on the 4 cases. Hand-grade 4 cases on groundedness and confirm the scorer agrees on ≥ 3/4.

---

### Action 5 — Commit Phase 1 and STOP

Single commit message: `[claim-bench] Phase 1 — retrieval + post-cutoff cases + groundedness`. Body should list: the 2 new cases (with DOIs/dates), the `tools.py` addition, the solver chain change, the groundedness scorer.

Append to `LEARNINGS.md` a new section dated today:
- What the post-cutoff cases proved about retrieval
- What groundedness scoring revealed (agreement rate, any disagreements with hand-grading)
- Any gotchas the next session should know about

**Then stop and check in with the user.** Phase 2 (calibration + trace faithfulness scorers) and Phase 3 (atomic-claim P/R/F1) require architectural decisions you should not make unilaterally. Specifically: the user should decide whether to implement AutoVerifier's 6-layer decomposition as nested `Solver` chains vs keeping it flat.

---

## Model routing for this project

Three distinct model roles. Do not collapse them.

### Role A — Subject Under Test (SUT)

The model being evaluated. This is whatever model the `--model` flag passes to `inspect eval`. For Phase 1 dev runs: use `openai/gpt-4o-mini` — cheap, fast, clearly below frontier so failures are informative. When running real benchmark sweeps later, iterate across:
- `anthropic/claude-opus-4-6`
- `anthropic/claude-sonnet-4-6`
- `openai/gpt-5.4`
- `google/gemini-3.1-pro-preview`

Do NOT run full sweeps across all 4 in Phase 1. Dev runs on one cheap model only. Full sweeps are a Phase 4+ concern after cards exist to interpret the results.

### Role B — Judge / model-graded scorers

The models implementing `groundedness_scorer`, eventually `faithfulness_scorer`, `calibration_scorer`. **These must be cross-family from the SUT** per FINCH-ZK (+31pp cross-family accuracy, vs 62% same-family on FELM response-level). Same-family self-review is ~60% correlated in errors per Kim et al. ICML 2025 — it provides almost no adversarial pressure.

**Concrete routing:**
| SUT family | Judge family (first choice) | Judge family (second choice) |
|---|---|---|
| Anthropic (Claude) | Google (Gemini 3.1 Pro) | OpenAI (GPT-5.4) |
| OpenAI (GPT-5.x / gpt-4o-mini) | Google (Gemini 3.1 Pro) | Anthropic (Claude Sonnet 4.6) |
| Google (Gemini) | OpenAI (GPT-5.4) | Anthropic (Claude Sonnet 4.6) |

**Defaults when in doubt:** `google/gemini-3-flash-preview` for cheap judge calls, `google/gemini-3.1-pro-preview` for groundedness on contested cases. Gemini Flash is $0.50/$4 per MTok — affordable for a scorer that runs on every sample.

**Gemini gotchas** (from `model-guide` skill):
- Keep temperature at 1.0 (lowering causes looping)
- Query at the END of the prompt, not the beginning
- Default `maxOutputTokens` is only 8192 — you must raise it explicitly for groundedness explanations
- Few-shot examples matter more for Gemini than Claude/GPT
- Add `"Remember it is 2026"` — Gemini benefits from date anchoring

**Never:** use `gpt-4o-mini` to judge `gpt-4o-mini` outputs. Same-family → no adversarial pressure → the scorer approves its own verdict 94% of the time regardless of correctness.

### Role C — The agent session reading this handoff (you)

Default to **Claude Sonnet 4.6** for this build. Reasons:
- 79.6% SWE-bench at ~60% of Opus cost (per `model-guide` skill)
- 1M context — enough to hold PLAN.md + LEARNINGS.md + prior-art memo + inspect_ai docs simultaneously
- "The Workhorse" — GDPval 1633 (actually beats Opus on expert preference)
- Better speed/intelligence ratio than Opus for subagent-scale coding tasks

Reserve Opus 4.6 for:
- Synthesis after Phase 1 completes (comparing the 4 cases against frontier model sweep)
- Cross-project design decisions (e.g. when/whether to extract to top-level `claim_bench/` package)
- Legal/professional analysis on ambiguous cases

Do NOT use GPT-5.4 as the coding agent here — no reason to switch families mid-project, and same-family consistency on project state helps.

---

## Environment & commands

```bash
cd ~/Projects/agent-infra
uv sync                                                              # install deps
uv run python -c "import inspect_ai; print(inspect_ai.__version__)"  # verify install (expect 0.3.205+)

# Run the Phase 0 probe as a sanity check before you start Phase 1:
uv run inspect eval experiments/claim-bench/task.py --model openai/gpt-4o-mini

# View the latest eval log:
uv run python -c "
from inspect_ai.log import read_eval_log
from pathlib import Path
log = read_eval_log(sorted(Path('logs').glob('*.eval'), key=lambda p: p.stat().st_mtime)[-1])
print('samples:', len(log.samples or []))
for s in (log.samples or []):
    print(s.id, s.scores['verdict_enum_scorer'].value, s.scores['verdict_enum_scorer'].answer)
"
```

**Required env vars:**
- `OPENAI_API_KEY` — for openai/gpt-4o-mini runs
- `ANTHROPIC_API_KEY` — for Claude judge calls
- `GOOGLE_API_KEY` — for Gemini judge calls
- `EXA_API_KEY` — for retrieval (check `~/.env` or `.env.local`)

**Gitignored directories** (don't commit these):
- `experiments/claim-bench/runs/` — eval outputs
- `logs/` — inspect_ai default log dir
- `.claude/plans/` — use `experiments/claim-bench/PLAN.md` instead (tracked)

---

## Landmines learned in Phase 0

1. **`.claude/plans/` is gitignored in this repo.** The plan file lives at `experiments/claim-bench/PLAN.md`, not under `.claude/plans/`. If you write plan updates, write them here or they disappear on clone.

2. **Pyright complains about `inspect_ai` imports in `experiments/claim-bench/`.** False positive — `experiments/claim-bench/` isn't part of the agent-infra package so Pyright doesn't resolve its dependencies. Ignore. See the existing `feedback_pyright_unresolvable_imports.md` genomics memory pattern.

3. **`inspect_ai` 0.3.0 requires `openai>=2.26.0`.** The agent-infra pyproject had `openai` pinned older from a prior install. Phase 0 added both. If you see `openai version too old`, bump the lower bound in `pyproject.toml`.

4. **3+ claude sessions run in parallel in this environment.** Use `git -C ~/Projects/agent-infra` for cross-repo operations. Commit after every logical edit (per `feedback_commit_immediately_multiagent.md`). Never `git add -A`.

5. **The genomics epistemic_scope memo (`genomics/docs/research/epistemic_scope_2026-04-03.md`) stays in genomics.** It documents what the genomics interpretation system specifically can defend. When Phase 5 adds the genomics adapter, that memo becomes the source for verdict-language translation (`supported` → `compatible with`, etc.). Don't duplicate it.

6. **gpt-4o-mini gets both Phase 0 cases right with no retrieval.** Both are memorizable (CRISPR-2015, Cochrane-vitamin-C). This is why Action 1 comes first — without post-cutoff cases, Phase 1 is unfalsifiable.

7. **`inspect eval --no-sandbox` is NOT a flag.** Sandbox defaults are fine for text-only tasks. `--sandbox` opts in, doesn't opt out.

8. **Score.metadata is preserved through EvalLog.** Phase 0 verified this with `{gold, predicted, in_enum, match}`. You can attach arbitrary metadata to your new scorers' Score objects and it roundtrips cleanly.

---

## Open gaps (not blockers for Phase 1)

These are Phase 2+ concerns. Don't pre-solve them; note them when they affect your decisions.

1. **Multi-class scoring metric.** Default `mean()` aggregation works for binary 0/1 verdict-match. For a real 5-class confusion matrix you'll want a custom `metric` decorator. Phase 2 concern.
2. **AutoVerifier's 6 layers in inspect_ai Solver chains.** Untested — the mapping is plausible (`chain(retrieve, extract, intra_doc_check, cross_source, corroborate, matrix)`) but nobody has run it. Your Phase 1 chain is only 3 steps deep; don't deepen until Phase 2.
3. **Exgentic/IBM Unitxt comparison.** Didn't evaluate deeply. If inspect_ai hits a blocker on enterprise features (cost tracking, SLAs, run registries), Exgentic is the backup. Apache 2.0.
4. **VeRO paper repo.** The Feb 2026 paper claims release but the repo wasn't located. Not critical; Meta-Harness covers that space.
5. **Atomic-claim Subject-Predicate-Object decomposition (Phase 3).** FIRE-Bench ships the scoring pattern, AutoVerifier the decomposition. You'll borrow both. Not Phase 1.
6. **Independence card heuristics.** BenchBrowser (arXiv:2603.18019) is the reference for content/convergent validity diagnosis. Phase 4 concern.

---

## Before you commit Phase 1 — checklist

- [ ] 4 cases exist, 2 of them cite post-cutoff evidence (≥2025-10 DOIs/dates)
- [ ] Probe without retrieval shows the 2 new cases are harder than the CRISPR/vitamin-C baseline
- [ ] `tools.py` exists with at least `@tool exa_search()`, tested manually
- [ ] Solver is `[system_message, use_tools(exa_search()), generate()]`, no longer bare `generate()`
- [ ] EvalLog for the new run contains tool-call events proving retrieval fired
- [ ] `groundedness_scorer()` exists and uses a cross-family judge (NOT same family as SUT)
- [ ] Groundedness scorer agrees with hand-grading on ≥ 3/4 cases
- [ ] `LEARNINGS.md` has a new dated section with Phase 1 findings
- [ ] `just lint` / `ruff check experiments/claim-bench/` passes (or note why not)
- [ ] Commit message lists the 2 new case DOIs inline for grep-ability
- [ ] You have NOT started Phase 2 (calibration, trace faithfulness scorers) — stop and check in

---

## If you get stuck

- **inspect_ai docs:** `https://inspect.aisi.org.uk/` — Tasks, Solvers, Scorers, Tools, Evals
- **inspect_ai scorer reference:** `https://inspect.aisi.org.uk/scorers.html`
- **inspect_ai GitHub:** `https://github.com/UKGovernmentBEIS/inspect_ai` (1,856 stars, MIT, very active)
- **FIRE-Bench for the scoring pattern:** `https://github.com/maitrix-org/FIRE-Bench` (Phase 3 reference, not Phase 1)
- **When Exa returns too much data:** set `contextMaxCharacters: 3000`, `numResults: 5` — see the Exa gotcha in `research/claim_verification_package_prior_art_2026-04-11.md` search log
- **When a subprocess call hangs:** don't retry. Read `.claude/rules/` for process-hygiene rules. The rule pattern that keeps showing up: "fix or replace the transport layer, don't delete the capability it delivers."
- **When unsure about model routing:** default to Sonnet 4.6 for code you write, Gemini 3 Flash for judge calls, openai/gpt-4o-mini for Phase 1 dev SUT runs. Never same-family for judges.

Good hunting.
