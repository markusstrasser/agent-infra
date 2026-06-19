---
title: "NousResearch hermes-agent-self-evolution — mechanism teardown vs our RSI loop"
date: 2026-06-19
tags: [rsi, self-evolution, gepa, dspy, skill-graduation, session-mining, prior-art]
status: complete
---

# Hermes Agent Self-Evolution — what it actually is, vs our RSI loop

Source: `github.com/NousResearch/hermes-agent-self-evolution` @ `0a929e3` (cloned 2026-06-19,
shallow). Repo is small: `evolution/` is ~1,700 LOC of real Python; `PLAN.md` is 40KB of
architecture. The gap between the two is the whole story.

**One-line verdict:** A clean **DSPy+GEPA wrapper that treats a `SKILL.md` body as the
optimizable parameter**, plus a genuinely useful **multi-tool session-history importer**
(Claude Code / Copilot / Hermes → eval examples) with secret-scrubbing. Everything past
"produce an evolved skill file and print a diff" is **aspirational** — the PR write-back, the
test-suite gate, the benchmark gate, and the continuous loop are in the README/PLAN but **not
wired into code**. Phases 2–5 are explicitly `🔲 Planned`.

---

## Mechanism (with file citations)

### 1. GEPA optimizer mechanics — THIN; the reflective step is not actually wired

The repo does NOT implement GEPA's trace-diagnosis. It delegates to `dspy.GEPA` and supplies a
metric:

- `evolution/skills/evolve_skill.py:156-165` — the entire optimizer setup:
  ```python
  optimizer = dspy.GEPA(metric=skill_fitness_metric, max_steps=iterations)
  optimized_module = optimizer.compile(baseline_module, trainset=trainset, valset=valset)
  ```
  Candidate generation, the reflective "why did this fail" step, and Pareto selection all live
  **inside the upstream `dspy.GEPA` library**, not here. On any error it silently falls back to
  `dspy.MIPROv2(auto="light")` (`evolve_skill.py:167-176`) — Bayesian few-shot, NOT reflective.
- `evolution/skills/skill_module.py:84-114` — the one real idea: a `SkillModule(dspy.Module)`
  whose `skill_text` (the markdown body) is the parameter GEPA mutates; `forward()` feeds
  `skill_instructions=self.skill_text` + `task_input` through a `ChainOfThought`. Evolved text is
  read back at `evolve_skill.py:183` (`optimized_module.skill_text`).
- **The reflective feedback is built but not used by the optimizer.** `evolution/core/fitness.py`
  has a real `LLMJudge` (`JudgeSignature`, `:41-58`) that scores correctness/procedure/conciseness
  and emits `feedback` text for GEPA's reflection. BUT the metric actually passed to `dspy.GEPA`
  is `skill_fitness_metric` (`fitness.py:107-136`), which is a **keyword-overlap heuristic**
  (`overlap = len(expected_words & output_words) / len(expected_words)`) returning a bare float —
  no feedback, no judge call. Comment at `:121-122` admits it: *"Full LLM-as-judge scoring is
  expensive — use it selectively."* So in the shipped path, GEPA reflects against a **bag-of-words
  proxy**, not the rubric judge. This is a Goodhart trap by construction (cf. our constitution:
  "a bad eval is worse than none").
- Pareto/selection: **not in this repo** — it's whatever upstream `dspy.GEPA` does. The holdout
  comparison (`evolve_skill.py:206-226`) is a post-hoc baseline-vs-evolved average using the *same*
  keyword metric.

### 2. The constraint-gate — partially real, the high-value parts are NOT wired

`evolution/core/constraints.py` (174 LOC) is the most complete file. `ConstraintValidator.validate_all`
(`:30-53`) runs, and these ARE called on the evolved skill (`evolve_skill.py:188`):
- `_check_size` (`:95`) — skill ≤ 15,000 chars; tool_desc ≤ 500; param_desc ≤ 200.
- `_check_growth` (`:119`) — ≤ 20% growth over baseline length.
- `_check_non_empty` (`:136`).
- `_check_skill_structure` (`:150`) — YAML frontmatter has `name:` + `description:`.

A failed constraint hard-stops deploy and writes `evolved_FAILED.md` (`evolve_skill.py:197-204`).
That part is real and clean.

**The gate the README headlines is NOT wired:**
- `run_test_suite` (`constraints.py:55-93`) shells `pytest tests/ -q` in the hermes-agent repo and
  requires returncode 0. **Grep proof: `run_test_suite` is defined but has ZERO callers** in
  `evolution/`. The orchestrator (`evolve_skill.py`) never calls it; `run_tests`/`run_pytest`
  flags thread through config but only ever reach the dataclass field. So the README guardrail
  *"Full test suite — pytest must pass 100%"* does not execute.
- `run_tblite` / `tblite_regression_threshold: 0.02` (`config.py:42-43`) — a benchmark-regression
  gate exists as config fields only; **no code reads them**. The README's "benchmarks" gate and
  PLAN's "Caching compatibility" and "Semantic preservation" guardrails have **no implementation**.

Net gate contract that actually runs: `size ≤ limit AND growth ≤ 20% AND non-empty AND has
frontmatter`. The test/benchmark/semantic gates are vaporware.

### 3. Session-DB ingestion — REAL and the best part of the repo

`evolution/core/external_importers.py` (785 LOC) is genuine, tested
(`tests/core/test_external_importers.py`), and the standout component:
- **Three adapters**, each a static `extract_messages()` returning normalized dicts
  (`source/task_input/[assistant_response]/session_id`):
  - `ClaudeCodeImporter` (`:157`) — reads `~/.claude/history.jsonl`, field `display` = user text.
    **User inputs only** (Claude Code's flat history has no assistant turns).
  - `CopilotImporter` (`:210`) — globs `~/.copilot/session-state/*/events.jsonl`, streams line-by-line
    (100MB+ files), pairs `user.message`/`assistant.message` events (`_parse_copilot_events:273`).
  - `HermesSessionImporter` (`:334`) — `~/.hermes/sessions/*.json`, OpenAI-format message list,
    pairs each user msg with next assistant msg.
- **Secret scrubbing** (`SECRET_PATTERNS`, `:45-70`) — anchored regex for Anthropic/OpenRouter/
  OpenAI/GitHub/Slack/AWS keys, PEM blocks, `password=`/`token=` assignments. Every message dropped
  if it matches. This is a clean, copyable primitive.
- **Two-stage relevance filter** (`RelevanceFilter`, `:422`): (0) drop empty, (1) cheap keyword
  heuristic `_is_relevant_to_skill` (`:121`, ≥2 keyword overlap vs skill name+first-500-chars),
  (2) LLM `ScoreRelevance` signature (`:430`) emits `relevant/expected_behavior/difficulty/category`
  JSON → becomes an `EvalExample`. So raw chat turns get auto-labeled into a graded eval set.
- Output: `build_dataset_from_external(...)` → train/val/holdout JSONL under
  `datasets/skills/<skill>/` (`dataset_builder.py:54-75`).

**Schema/path note for us:** It reads `~/.claude/history.jsonl` (flat user-prompt log), NOT the
per-session transcripts in `~/.claude/projects/.../*.jsonl` and NOT a SQLite session DB. It has no
notion of tool calls, outcomes, or success/failure — it mines *prompts*, then *synthesizes* an
expected-behavior rubric with an LLM. There is no real success signal from the session; the "eval"
is LLM-imagined.

### 4. PR generation — DOES NOT EXIST

- `create_pr: bool = True` (`config.py:47`) is the **only** occurrence of "create_pr" in the codebase
  and it is **never read**. Grep proof: no `gh pr`, `git push`, `git checkout`, `git commit`,
  `git branch`, `create_pull`, or `PullRequest` anywhere in `evolution/` or `generate_report.py`.
- PLAN.md:151 lists `pr_builder.py # Auto-generate PR with metrics, diffs` in the file tree — that
  file **does not exist on disk**.
- What actually happens at the end (`evolve_skill.py:254-289`): writes `evolved_skill.md`,
  `baseline_skill.md`, `metrics.json` to `output/<skill>/<timestamp>/` and prints
  `"Review the diff: diff baseline_skill.md evolved_skill.md"`. The dry-run even prints *"Would
  validate constraints and create PR"* (`:76`) — promising a step with no implementation. The
  write-back loop is a human eyeballing a diff in a temp dir.

### 5. Dependencies — confirmed lightweight, no GPU

`pyproject.toml`: `dspy>=3.0.0`, `openai>=1.0.0`, `pyyaml`, `click`, `rich`. Dev: `pytest`. Optional
`darwinian = ["darwinian-evolver"]` (Phase 4, AGPL, external CLI, unused). **README confirms "No GPU
training required… ~$2-10 per optimization run"** and PLAN.md:17 explicitly excludes DSPy
`BootstrapFinetune` (the only weight-training component). Models default to `openai/gpt-4.1` (GEPA
reflection) + `gpt-4.1-mini` (eval/judge) — **pre-frontier**; treat any quality claim as
validity-uncertain per our frontier-timeliness rule. Verdict: **pure API, no GPU — confirmed.**

---

## What's genuinely novel vs our loop (the steal)

| Component | In our RSI loop? | Steal? |
|---|---|---|
| **Skill body as a DSPy-optimizable parameter** (`SkillModule`, GEPA mutates the markdown) | **No.** Our skill-graduation is workflow→SKILL.md authoring gated on scored evals; we don't run an *optimizer* that mutates an existing skill's text against a metric. | **STEAL the idea, not the code** — and only inside a clear-verifier regime. This is the one mechanism we lack. |
| **Test-suite as a hard constraint gate before deploy** (`run_test_suite`, pytest must pass 100%) | We have gov.py invariants + `just harness-eval` + promote/cut, but **as a deploy gate on an auto-generated skill variant** it's a clean contract. | **Already have the spirit; their impl is unwired.** Borrow the *contract* (variant must pass repo tests + size/growth before it's eligible), not the code. |
| **Multi-tool session importer w/ secret-scrub + 2-stage relevance** | We have agentlogs (richer: cross-vendor SQLite, tool calls, outcomes) + embed-once mining. Theirs is *thinner* (prompts only, no outcomes) but the **secret-scrub regex** and **Copilot/Hermes adapters** are things we don't have. | **SKIP the importer** (agentlogs is strictly better), **maybe steal the `SECRET_PATTERNS` regex** as a scrubbing primitive for any external corpus we ingest. |
| **PR write-back** | We have human-gated promotion to hooks/rules via improvement-log. | **N/A — they don't have it either.** Vaporware. |

The single real steal: **a verifier-gated skill *optimizer*** — given a skill that already
graduated, run GEPA (or any reflective optimizer) to mutate its body against a *real* eval, gate the
result on tests+size, surface the diff for promotion. This extends our skill path from
"author once, graduate" to "author → graduate → periodically re-optimize against measured evals."

## What we already have (don't rebuild)

- **Session ingestion** — agentlogs.db (cross-vendor, tool-call-level, outcome-aware) + embed-once
  semantic mining. Theirs reads a flat prompt log and *invents* expected behavior with an LLM; ours
  has ground-truth outcomes. Ours wins decisively.
- **Constraint/governance gate** — gov.py invariants, `just harness-eval`, promote/cut heuristic,
  single-variable harness commits. Their gate is 4 string checks + an unwired pytest call.
- **Human-gated write-back** — improvement-log `[ ]`/`[obs]` → hooks/rules. Strictly more mature
  than their (nonexistent) PR builder.
- **Scored-eval skill graduation** — our `skillopt-vs-autobrowse-veto` already separates skill
  *optimization* from graduation and gates it on scored evals. **This repo is the thing that veto
  anticipated**: skill optimization is real and separable — but only worth running behind a scored
  eval, which is exactly the gate we pre-registered.

## Steal / skip verdict per component

1. **GEPA reflective optimizer** — **STEAL THE PATTERN, GATED.** A skill-body optimizer is the one
   capability we lack. But adopt it ONLY where a *clear verifier* exists (the constitution's
   regime-1) — NOT against an LLM-judge or keyword proxy. Their shipped metric is a keyword-overlap
   Goodhart proxy; copying that would be net-negative. Wire it to a real eval (an `evals/` harness
   with ground-truth grading) or don't build it. This is precisely what `skillopt-vs-autobrowse-veto`
   already says: gated on scored evals.
2. **Constraint gate** — **SKIP the code, KEEP the contract.** "Variant eligible iff repo tests pass
   + size/growth bounded + structure valid" is a good one-line gate to fold into any future skill
   re-optimizer. We already enforce the equivalent via gov + harness-eval.
3. **Session-DB ingestion** — **SKIP.** agentlogs is strictly richer. Optional micro-steal: the
   anchored `SECRET_PATTERNS` scrub regex for external-corpus hygiene.
4. **PR write-back** — **SKIP (nonexistent).** Our improvement-log promotion path is more mature.

## Skeptic's note (thin/aspirational?)

**Partly aspirational, and the headline guardrails are the unwired parts.** The README flow diagram
("Constraint gates (tests, size limits, benchmarks) → PR against hermes-agent") and the Guardrails
list (test suite, caching compatibility, semantic preservation, PR review) overstate the code:
- `run_test_suite` defined, **0 callers** (`constraints.py:55` vs grep of `evolution/`).
- `run_tblite`/`tblite_regression_threshold` — config fields, **0 readers**.
- `create_pr` — config field, **0 readers**; `pr_builder.py` listed in PLAN.md:151, **absent on disk**.
- GEPA reflects against a keyword-overlap proxy, not the `LLMJudge` rubric it also ships.
- Phases 2–5 (tool descriptions, prompts, code-evolution, continuous loop) all `🔲 Planned`.

What IS real and decent: the `SkillModule` parameterization, the 4 wired structural constraints, and
the 785-LOC tested session importer. So: **one good idea (skill-as-optimizable-parameter), one good
primitive (secret-scrub + multi-tool importer), wrapped in a README that describes a system twice the
size of the code.** Treat PLAN.md as a roadmap, not a description of shipped behavior.
