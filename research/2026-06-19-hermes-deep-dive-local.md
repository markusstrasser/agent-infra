---
title: "Hermes self-evolution — second-order LOCAL code dive"
date: 2026-06-19
tags: [rsi, skill-opt, gepa, self-evolution, hermes, second-order]
status: complete
---

# Hermes self-evolution — second-order dive on LOCAL code

Prior teardown: `research/2026-06-19-hermes-self-evolution-pattern.md` (web-fetch level).
That pass established: ONE steal = skill-body-as-optimizable-param; SKIP GEPA keyword-overlap
fitness; PR write-back unwired.

This dive: read every file under `evolution/` + `tests/`, hunt for a SECOND-order steal the
web-fetch would have missed. Evidence = file:line.

## Status: COMPLETE

## Ground-truth: tests + the GEPA path is dead-on-arrival

- **Tests: 145 passed** (`uv run --no-project --with pytest --with dspy ... -m pytest -q` → `145 passed, 11 warnings in 25.68s`).
  But ALL 145 are unit tests of `constraints`, `external_importers`, `skill_module`, `config` — **none exercise the GEPA
  optimization path** (no test imports `dspy.GEPA`, no test calls `evolve()`). The "real" part is the importer + parsers;
  the optimizer is untested.
- **THE killer finding the web-fetch could not get (probe, not opinion):** the installed `dspy==3.2.1` `GEPA.__init__`
  signature is `[metric, auto, max_full_evals, max_metric_calls, reflection_minibatch_size, candidate_selection_strategy,
  reflection_lm, ...]`. **There is NO `max_steps` parameter.** The repo calls
  `dspy.GEPA(metric=skill_fitness_metric, max_steps=iterations)` (`evolve_skill.py:156-159`). That raises `TypeError` →
  the bare `except Exception` at `evolve_skill.py:166` **always catches** → **the shipped path always falls back to
  `dspy.MIPROv2(auto="light")`** (`:169-176`). So in this clone against current dspy, **GEPA never runs at all.** The
  whole "GEPA reflective evolution" headline executes Bayesian few-shot bootstrapping instead, every time.
- **Second nail:** `dspy.GEPA` 3.2.1 requires `reflection_lm` (default `None`) for the reflective step; the repo never
  passes it. And the metric `skill_fitness_metric` returns a **bare float** (`fitness.py:136`), never a
  `dspy.Prediction(score=, feedback=)`, so GEPA would have no textual feedback to reflect on even if it instantiated.
  The reflection is unwired three ways over (no max_steps→no GEPA, no reflection_lm, no feedback in metric).

**Verdict on the prior teardown:** CONFIRMED and then some. The first pass said "GEPA reflects against a keyword-overlap
proxy." The local probe shows it's worse — **GEPA does not execute; MIPROv2 does**, against the keyword proxy. There is
no GEPA reflection prompt in this repo to steal because GEPA is never reached.

---

## 1. GEPA reflection prompt — WORSE THAN OURS (there is no reflection prompt)

**Finding: there is no custom reflection prompt anywhere in the repo, and the path that would have used one is dead.**

- The only optimizer construction is `evolve_skill.py:156-176`. `dspy.GEPA(metric=skill_fitness_metric, max_steps=...)`
  → TypeError → MIPROv2 fallback. No `reflection_lm`, no `instruction_proposer`, no custom proposer prompt is supplied —
  all of GEPA's reflection would be dspy-internal defaults, and none of it runs.
- The closest thing to a "diagnose why a trace failed" prompt is `LLMJudge.JudgeSignature` (`fitness.py:41-58`), which
  emits a `feedback` OutputField: *"Specific, actionable feedback on what could be improved."* That is a generic
  one-line instruction — **far thinner** than our `/observe` diagnosis, which mines real `agentlogs.db` tool-call
  outcomes (not LLM-imagined rubrics) and routes findings through the constitution's self-improvement governance
  (recurs-2+-sessions, checkable-predicate-or-architecture). And critically, `LLMJudge` is **never wired to the
  optimizer** — `skill_fitness_metric` is the metric passed, not `LLMJudge.score`. The judge feedback dead-ends.
- **BETTER-THAN-OURS? No. WORSE.** Our `/observe` → improvement-log diagnosis grounds in ground-truth session outcomes;
  theirs (a) doesn't run, (b) if it ran would reflect on a bag-of-words scalar, (c) the rubric-judge that could produce
  real feedback is disconnected. Nothing to steal here.

## 2. Pareto / selection logic — WORSE THAN OURS (not in this repo + the one hint is dead config)

- `config.py:21` declares `population_size: int = 5`. **Grep proof: ZERO readers** outside its own definition. It is a
  vestigial field. There is no frontier, no archive, no multi-objective selection in `evolution/`.
- All actual selection lives inside upstream `dspy.GEPA` / `dspy.MIPROv2` — and per finding above, only MIPROv2 ever
  runs (greedy-ish Bayesian search over few-shot demos, single scalar objective). The "holdout comparison"
  (`evolve_skill.py:206-226`) is a post-hoc average of baseline-vs-evolved on the **same keyword metric** — a single
  scalar, no Pareto front, no multi-objective tradeoff surface.
- The one *latent* multi-objective idea is `FitnessScore.composite` (`fitness.py:24-31`): a fixed-weight blend
  `0.5*correctness + 0.3*procedure + 0.2*conciseness − length_penalty`. That is a **scalarization**, not a frontier —
  and it's also unwired (the metric that runs is the keyword proxy, not `composite`).
- **BETTER-THAN-OURS? No.** Our skill-graduation gating on scored evals + promote/cut is already a selection gate; this
  repo has strictly less (a dead `population_size` int and a scalarized weight blend that never executes). No
  multi-objective idea worth stealing — the conciseness-as-explicit-dimension is mildly interesting but it's just a
  length penalty, which our gov size-shrink (`gov-report`) already does deterministically.

## 3. constraints.py contract — SAME / SLIGHTLY-WORSE (clean shape, but the load-bearing gate is unwired)

- The contract shape is genuinely clean: `validate_all(artifact_text, artifact_type, baseline_text=None) ->
  list[ConstraintResult]` where each `ConstraintResult(passed, constraint_name, message, details)` is a typed,
  human-readable verdict (`constraints.py:15-53`). Four wired checks: `_check_size` (≤15k/500/200 by type),
  `_check_growth` (≤20% over baseline), `_check_non_empty`, `_check_skill_structure` (frontmatter has name+description).
  This IS a tidy "candidate declares what it must pass" surface.
- **But the high-value gate is unwired (confirmed by grep):** `run_test_suite` (`:55-93`, shells `pytest tests/ -q` in
  the hermes repo, requires rc 0) has **ZERO callers**. `run_tblite`/`tblite_regression_threshold` (`config.py:42-43`)
  have **ZERO readers**. So the contract that actually executes is `size ∧ growth ∧ non-empty ∧ structure` — four string
  checks. The "variant must pass the repo's own test suite" gate — the thing that would make this a real verifier — is
  defined and abandoned.
- **BETTER-THAN-OURS? No — SAME at best.** Our equivalent is gov.py invariants + `just harness-eval` (~43s: hooks-smoke,
  drift, prior-context, orient tests) + single-variable harness commits + human-gated promote/cut. The ONE shape worth
  borrowing if we ever build a skill re-optimizer: the typed `ConstraintResult` list as the eligibility contract
  ("variant eligible iff harness-eval green ∧ size-bounded ∧ growth-bounded ∧ structure-valid"). That's a packaging
  nicety, not a capability we lack. Their `_check_growth` (% over baseline) is a cleaner single-number framing than our
  ad-hoc size discussion — minor steal at most.

## 4. skill_module.py — CONFIRMED STEAL (the one real idea); extracted mechanics below

This is the only genuinely-better-than-nothing component, and the prior teardown already named it. The concrete how
(so we could implement against our SKILL.md files):

- **Parse** (`skill_module.py:15-55`, `load_skill`): split on `raw.split("---", 2)` → `frontmatter = parts[1]`,
  `body = parts[2]`. Pull `name:`/`description:` by line-prefix scan. Returns a dict
  `{path, raw, frontmatter, body, name, description}`. **Note the fragility: naive `"---".split(..,2)` breaks if the
  body itself contains a `---` horizontal rule before the frontmatter close** — fine for their skills, a real bug for
  ours (our SKILL.md bodies use `---` separators). We'd use a proper frontmatter parser (the global frontmatter
  convention) not this split.
- **Wrap as tunable param** (`:84-114`): `SkillModule(dspy.Module)` stores `self.skill_text = body` and builds
  `self.predictor = dspy.ChainOfThought(TaskWithSkill)` where the signature is
  `skill_instructions(InputField) + task_input(InputField) -> output(OutputField)`. **The body is fed as a normal
  InputField, so DSPy's optimizer treats it as the mutable instruction string.** `forward(task_input)` just calls the
  predictor with `skill_instructions=self.skill_text`. The optimizer reads the evolved body back via
  `optimized_module.skill_text` (`evolve_skill.py:183`).
- **Re-serialize** (`:117-123`, `reassemble_skill`): `f"---\n{frontmatter}\n---\n\n{evolved_body}\n"` — frontmatter
  preserved verbatim, only body replaced. Clean and correct.
- **The mechanism in one sentence:** *treat the SKILL.md body as a string-valued InputField on a single-signature DSPy
  module, let a prompt-optimizer mutate it against an eval, re-glue the original frontmatter.* That is the whole steal,
  and it is ~40 lines.
- **BETTER-THAN-OURS? YES, for the narrow capability we lack** — we author/graduate skills but do not run an *optimizer
  loop* over an existing skill body. CAVEAT (load-bearing, from constitution + `skillopt-vs-autobrowse-veto`): adopt the
  *parameterization*, NOT their metric. Wire it to a **clear-verifier** eval (an `evals/` harness with ground-truth
  grading), never the keyword proxy or an LLM-judge — a scalarized LLM-judge metric is the Goodhart trap our constitution
  forbids ("a bad eval is worse than none"). This is exactly what our pre-registered veto already says: skill
  optimization is real and separable, gated on scored evals.

## 5. dataset_builder.py + external_importers.py — WORSE THAN OURS (agentlogs strictly richer), with 3 NEW micro-primitives the first pass missed

- **Dataset construction is strictly weaker than agentlogs.** Their eval set is *LLM-imagined*: `RelevanceFilter`
  (`external_importers.py:422-543`) takes raw chat turns and asks an LLM to emit `{relevant, expected_behavior,
  difficulty, category}` (`ScoreRelevance`, `:430-443`) — i.e. the "expected behavior" is **synthesized, not observed**.
  There is no success/failure signal, no tool-call outcome, no ground truth. agentlogs.db has cross-vendor tool-call-level
  outcomes; embed-once gives angle-agnostic mining for free. Ours wins decisively on signal quality.
- `SyntheticDatasetBuilder` (`dataset_builder.py:89-169`): an LLM reads the skill and invents `(task_input,
  expected_behavior)` pairs. Pure synthetic, same Goodhart risk. The train/val/holdout split (50/25/25) is standard.
- **THREE micro-primitives the web-fetch pass did NOT surface** (all real, all tested, all copyable in isolation):
  1. **`SECRET_PATTERNS` anchored scrub regex** (`:45-70`) — Anthropic/OpenRouter/OpenAI/GitHub/Slack/Notion/AWS keys +
     PEM + `password=`/`secret=`/`token=` assignments, applied to *every* message before it enters a dataset. We ingest
     external corpora (research memos, web sources) and have **no equivalent scrub primitive**. This is a clean ~25-line
     steal for any external-corpus hygiene path. (Prior teardown mentioned secret-scrub existed but not as a callable
     primitive worth lifting; this confirms it tested + standalone.)
  2. **Brace-balanced JSON extractor** (`_parse_scoring_json`, `:546-600`) — handles LLM output that wraps/fences JSON,
     does depth-counting with in-string/escape tracking instead of the naive `r'\{[^}]+\}'` regex that breaks on nested
     braces. We parse LLM JSON in several places (extraction, critique); this is a more robust pattern than a flat regex.
     Minor but genuinely better than a naive parser.
  3. **LLM error-rate reporting** (`:535-541`) — counts `errors/total_scored` and prints the % when an LLM judge
     misbehaves, instead of silently dropping. A small observability primitive aligned with our "fail loud" P8 face.
- **BETTER-THAN-OURS? No on the dataset approach** (agentlogs richer, ground-truth vs imagined). **Partial micro-steals**:
  the secret-scrub regex (real gap for us), the brace-balanced JSON parser (robustness upgrade), error-rate reporting
  (minor). None are RSI-loop capabilities — they're hygiene/parsing utilities.

---

## VERDICT: is there a SECOND steal beyond skill-body-as-param?

**No second *capability* steal. Yes, three small *primitive* steals (none RSI-loop-level), and one strong NEGATIVE
finding that hardens the first steal's gate.**

| # | Component | Verdict | Steal? |
|---|---|---|---|
| 1 | GEPA reflection prompt | WORSE — doesn't exist + path is dead | No |
| 2 | Pareto/selection | WORSE — `population_size` is dead config; only MIPROv2 runs | No |
| 3 | constraints.py contract | SAME — clean typed shape, but real gate (`run_test_suite`) unwired | Borrow the `ConstraintResult` eligibility-list shape if we build a re-optimizer; not a capability |
| 4 | skill_module.py (body-as-param) | BETTER (narrow) — confirmed first steal | YES — ~40-line mechanism extracted above; gate on a CLEAR verifier, never their metric |
| 5 | dataset_builder + importers | WORSE — LLM-imagined evals vs agentlogs ground truth | 3 micro-primitives only: SECRET_PATTERNS scrub, brace-balanced JSON parser, LLM error-rate report |

**The sharpest new fact (probe-grade, not derivable from a web-fetch):** against the pinned `dspy==3.2.1`, the
`dspy.GEPA(..., max_steps=...)` call **raises TypeError and silently falls back to MIPROv2 every run** — GEPA never
executes in this clone. Combined with the missing `reflection_lm` and the bare-float metric, the "GEPA reflective
self-evolution" is triply unwired. This *strengthens* our prior verdict: the ONLY thing to take is the
SKILL-body-as-optimizable-parameter abstraction (finding 4), and it must be wired to a ground-truth verifier — adopting
their optimizer/metric/selection would import a Goodhart proxy that doesn't even run.

**Recommended action if we ever build the skill re-optimizer (gated, per `skillopt-vs-autobrowse-veto`):** lift the
~40-line `SkillModule`/`load_skill`/`reassemble_skill` parameterization (using a real frontmatter parser, not their
`split("---",2)`), point the DSPy metric at a `~/Projects/evals` ground-truth harness, and gate the candidate on
`just harness-eval` green + size/growth bounds expressed as a `ConstraintResult` list. Optionally fold in the
`SECRET_PATTERNS` scrub for any external-corpus ingestion. Skip everything else in this repo.
