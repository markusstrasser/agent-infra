---
title: "Oeberst & Imhoff Bias Framework — Coverage Audit of Agent Tooling"
date: 2026-04-11
tier: standard
ground_truth: agent-failure-modes.md, anti-sycophancy-process-supervision.md, causal-reasoning-evidence.md
---

# Oeberst & Imhoff Bias Framework — Coverage Audit of Agent Tooling

**Question:** Does our agent tooling avoid or correct for the biases Oeberst & Imhoff (2023) unify under belief-consistent information processing? Which gaps are real?

**Tier:** Standard | **Date:** 2026-04-11

**Related:** `research/domain-specific-agent-biases.md` (2026-03-21) catalogs trading/research/engineering-domain biases empirically. This memo is the complementary *framework* view — a single unifying mechanism (BCIP) audited against our tooling.

## Paper

Oeberst, A., & Imhoff, R. (2023). *Toward Parsimony in Bias Research: A Proposed Common Framework of Belief-Consistent Information Processing for a Set of Biases.* Perspectives on Psychological Science, 18(6), 1464–1487. [doi:10.1177/17456916221148147](https://doi.org/10.1177/17456916221148147)

**Core claim.** 17+ named biases reduce to **belief-consistent information processing (BCIP)** — i.e., confirmation bias — applied to 6 fundamental default beliefs. People actively seek and favor information consistent with these priors and discount disconfirming evidence.

**The 6 fundamental beliefs** (and biases each generates):

| # | Belief | Biases |
|---|--------|--------|
| 1 | "My experience is a reasonable reference" | spotlight effect, illusion of transparency, illusory transparency of intention, false consensus effect, social projection |
| 2 | "I make correct assessments of the world" | bias blind spot, hostile media bias |
| 3 | "I am good" | better-than-average effect, self-serving bias |
| 4 | "My group is a reasonable reference" | ethnocentric bias, in-group projection |
| 5 | "My group is good" | in-group/partisan bias, ultimate attribution error, linguistic intergroup bias, intergroup sensitivity effect |
| 6 | "People's attributes (not context) shape outcomes" | fundamental attribution error, outcome bias |

**Sole prescribed debiasing:** *"consider the opposite"* — deliberately search for information inconsistent with the underlying belief. The authors argue this single strategy can reduce multiple biases because it attacks the shared BCIP mechanism, not the surface symptoms.

[SOURCE: https://pmc.ncbi.nlm.nih.gov/articles/PMC10623627/] [SOURCE: https://journals.sagepub.com/doi/10.1177/17456916221148147]

A 2025 follow-up integrates BCIP with Thagard's coherence-based reasoning. [SOURCE: https://onlinelibrary.wiley.com/doi/10.1002/ejsp.70006]

## Translation to Agents

Oeberst & Imhoff studied human cognition. The beliefs translate straightforwardly to an agent's default priors:

| Belief | Agent analog |
|--------|--------------|
| 1. My experience is a reasonable reference | Training-time knowledge = current world; user shares agent's frame |
| 2. I make correct assessments | Selective reading confirms priors; contradicting tool output = "flaky test / wrong docs" |
| 3. I am good | Premature termination; capability abandonment; self-serving attribution of ambiguous outcomes |
| 4. My group is a reasonable reference | Drift toward training-distribution majority patterns vs. project conventions |
| 5. My group is good | Same-model review is charitable to same-model outputs (debate-as-martingale) |
| 6. Attributes not context shape outcomes | "Test failed → code wrong" (vs. "my test assumption wrong"); judging process by outcome |

## Coverage Audit

| # | Belief | Coverage | Enforcement mechanism |
|---|--------|----------|-----------------------|
| 1 | Experience-as-reference | **Partial** | Rule 1 "does this already exist"; Rule 13 "verify vendor claims"; `Frontier Timeliness`; `pretool-read-discipline`; `postwrite-frontier-timeliness.sh` |
| 2 | Correct assessments | **Partial, mostly instructional** | `<epistemic_discipline>` #5 *blind first-pass* is literally "consider the opposite". `postwrite-source-check`, `stop-research-gate`, cross-model review principle. CLAUDE.md (line 120) explicitly flags blind-first-pass as *unhookable* |
| 3 | I am good | **Strongest coverage** | `stop-verify-plan`, `stop-uncommitted-warn`, `stop-knowledge-check`, `posttool-plan-review-gate`, Rule 14 "fix all confirmed findings, not top N", session-analyst post-hoc, Failure Mode 9 (Premature Termination) in `agent-failure-modes.md` (11.8% recurrence) |
| 4 | Group-as-reference | **Weak** | `.claude/rules/*` project overrides; `native-patterns.md`. No detector for "drifting toward the GitHub mean" |
| 5 | Group is good | **Principled, not enforced** | Constitution Principle 12 "Cross-model review"; `research/compiled/agent-scaffolding-safety.md`; "Debate or Vote" in `agent-failure-modes.md:155`. Enforcement is workflow-dependent |
| 6 | FAE / outcome bias | **Gap** | Decision journal + blind first-pass partially. No tooling catches FAE-style self-attributions in agent reflections |

**Strongest:** belief 3 ("I am good") — because premature termination was painful enough to hook it hard (`stop-*` family). Matches the paper's prediction that self-serving bias is the highest-frequency manifestation.

**Weakest:** belief 6 (FAE / outcome bias) has zero coverage. Belief 2 (bias blind spot) relies entirely on an instruction the constitution itself flagged as unhookable — so under Principle 1 ("instructions run 0% reliably, per EoG") it's not reliably enforced.

**The headline finding:** the single intervention the paper endorses — *consider the opposite* — is the one our constitution explicitly conceded resists hookification. That makes belief 2 the interesting target, not belief 3.

## Biases Outside the Framework That Matter More for Agents

Oeberst & Imhoff studied human cognition. Agents have additional bias sources from training objectives that the framework doesn't cover:

1. **Sycophancy / RLHF drift.** 58.19% base rate per SycEval (AAAI 2026, `agent-failure-modes.md:244`); 45pp above humans on social sycophancy per ELEPHANT (ICLR 2026). Listed as instruction-mitigated-only in the constitution "Known Limitations." This is the *dominant* agent bias and it is **not** BCIP — it's a training objective, not a cognitive shortcut. `technical_pushback` rules target it but EoG → 0% reliability. [SOURCE: DOI:10.1609/aies.v8i1.36598]

2. **Automation bias.** Over-trusting tools/subagents the agent itself called. Inverse of the paper's "hostile media bias": humans *under*-trust media they didn't choose, agents *over*-trust tool output they initiated. Partially covered by `stop-subagent-synthesis-gate`, `subagent-epistemic-gate.sh`, `posttool-verify-before-expand.sh`.

3. **Anchoring.** First number/path/solution sticks. **Zero coverage.** Relevant when the agent estimates complexity, picks a file structure, or commits to a debugging hypothesis early.

4. **Availability bias toward in-context content.** The agent over-weights files currently in its context window. `pretool-read-discipline` / `posttool-dup-read` address the *cost* side but not the *weighting* side.

5. **Planning fallacy.** Global CLAUDE.md sidesteps rather than fixes: "Avoid giving time estimates." Correct call under EoG but worth naming as avoidance, not correction.

## What We Already Cover Well

- Belief 3 via the `stop-*` hook family + Premature Termination failure-mode catalog
- Source grading (belief 1, partial belief 2) via `postwrite-source-check.sh` at the architecture level
- Cross-model adversarial pressure (belief 5) as a named principle with workflow support
- Verify-before-expand (automation bias) via `posttool-verify-before-expand.sh`

## Gaps Worth Building For

1. **Belief 6 — outcome-bias / FAE in retrospectives and commit messages.** No current tooling. Detectable as a regex predicate on completion text (success verbs without pre-action prediction language). Cheapest win.
2. **Belief 2 — partial hookification of "consider the opposite".** The constitution said unhookable, but there is a narrow hookable sub-case: when the agent is about to form a judgment on a topic where a prior memo exists, inject a reminder to read new evidence first. Not semantic judgment, just a lookup against `research-index.md`.
3. **Anchoring (not in framework).** Hard. Needs a probe-before-committing pattern, not a blocker hook. Possibly a skill rather than a hook.

Gaps that are NOT worth building:
- Belief 4 (ethnocentric / group-as-reference): existing `.claude/rules/*` project overrides already break the default. Adding "drift detector" duplicates `native-patterns.md`.
- Belief 5 (group is good): enforcement is via routing (Gemini/GPT for review), not predicate — this is a workflow thing, not a hookable thing.
- Sycophancy: structurally unhookable per EoG + Known Limitations. Session-analyst post-hoc detection is the current ceiling.

## Revisions

### 2026-04-11 — Cross-model review + execution

Ran `/review model` on the initial plan (`.model-review/2026-04-11-bias-tooling-plan-4ba85d/`). Gemini 3.1 Pro + GPT-5.4 high converged on several sharp critiques that forced a plan rewrite before any code was written. Core lessons:

1. **Original Tier 1.1 (outcome-bias check in `commit-check-parse.py`) was construct-invalid.** Cross-model agreement: commit messages are pre-hoc authorial documentation; FAE and outcome bias are post-hoc reasoning errors. The regex would detect short commit style, not bias. GPT-5.4 quantified plausible PPV at 8–45%. Rejected before implementation.

2. **Original Tier 1.2 (`/consider-opposite` as standalone skill) had a skill-recursion failure.** Invocation depended on the agent noticing it should consider the opposite — the exact meta-cognition the skill was supposed to supply. Converted to required `## Counterevidence sought` section in `decisions/.template.md` (committed e23bd1c) — a deterministic caller (the template) replaces the self-referential vibes.

3. **Correct surface for belief-6 is Stop/retro/session-analyst, not commit-message parsing.** Both reviewers agreed. Plan rewritten to: (a) session-analyst taxonomy labels (commit 097553e), (b) `FM25: Belief-6 Attribution Errors` added to `agent-failure-modes.md` (e5a53d3), (c) `stop-unsupported-completion.sh` shadow-mode hook at the Stop surface (skills@c0b3f71 + meta settings bc51cb5).

4. **Tier 1 didn't touch primary failure modes.** My initial framing optimized for "where coverage is thinnest" (belief 6) when the right objective is "where marginal hook dollars reduce measured recurring failures" (belief 3 territory, despite already being the strongest-covered). Framing error on my part — the Stop-surface hook is closer to the 11.8% premature-termination recurrence than any commit hook would have been.

5. **Self-invented probe gate ("3 real cases in 90 days") contradicted Constitution Principle 6's "2+ sessions" rule.** Dropped — use the constitutional rule consistently.

6. **`selection-rationale.md` was vaporware.** Both review models referenced it as if it existed. Neither verified. I didn't verify either until execution probe. The constitution names it as a pattern but there is no template file — `decisions/.template.md` is the real artifact. Lesson: cross-model review can converge on a hallucinated target if the source text exists. Verify existence of named files before adopting recommendations.

7. **Deferred: cross-model drift verifier on governance-file edits.** Both reviewers endorsed this, but my `improvement-log.md` grep for "agent edited CLAUDE.md/GOALS.md in ways that drifted from intent" found zero incidents. Rule 1 (does this already exist / has this problem occurred) says: no incident history → hypothetical → don't build. Added to `ideas.md` as a watch item — build if ≥2 sessions of confirmed governance drift recur.

8. **Multi-agent commit hygiene failure.** During execution, commit `bc51cb5` swept up an unrelated `meta → agent-infra` path rename from another active agent-infra session's uncommitted working tree. Amended with disclosure. Lesson: `git diff --staged` before committing when `pgrep -c claude >= 2`, not just `git status`.

Execution artifacts:
- `e23bd1c` decisions template counterevidence section (wording fixed in `3bdc82e`)
- `097553e` session-analyst belief-6 detection labels (citation fixed in `de4dbfc`)
- `e5a53d3` agent-failure-modes FM25 (scope clarified in `3bdc82e`)
- `bc51cb5` meta settings.json Stop chain wiring (bundled rename disclosed, not split)
- `2d66999` first revisions round
- `53bbd99` deferred governance-drift verifier + 14-day review watch item (updated in `3bdc82e`)
- `~/Projects/skills/hooks@e3b89c0` shadow hook (post plan-close fix; initial buggy commit c0b3f71)
- `~/Projects/skills/hooks@4525d2c` 12-case pytest harness

### Plan-close caught-red-handed loop (2026-04-11, findings at `.model-review/2026-04-11-bias-plan-close-89878c/`)

Second cross-model review pass, this time on the implementation as committed. 19 findings, 3 with cross-model agreement at HIGH severity. Caught-red-handed outcomes:

1. **Predicate construct bug:** initial hook used `success_hits >= 2` AND `len(msg) < 20` exclusion — blocked the dominant form (single-verb terse claims like "Fixed."). Both reviewers caught it. Fixed in skills@e3b89c0. Caught-red-handed validation: the 12-case pytest harness fails 6/12 against HEAD~1 and passes 12/12 post-fix.

2. **Evidence/prediction pattern list was mixing three different things:** evidence markers, pre-action prediction, and weak hedging. `should`/`would`/`likely`/`\bran\b`/`\bjust test\b` were all wrong. `\bran\b` false-matched "I ran out of time"; `\bjust test\b` was overfit to local workflow; `should`/`would`/`likely` are not evidence at all. Split into `EVIDENCE_PATTERNS` (pytest/stdout/stderr/exit code/trace/numeric results/etc.) and `PREDICTION_PATTERNS` (expected/hypothesiz/predict/before/previously) with weak suppressors deleted.

3. **Silent failure mode:** `2>/dev/null` hid all Python errors during the shadow period, corrupting precision measurement. Now redirected to `~/.claude/unsupported-completion-errors.jsonl` with structured error records. Shadow log reliability now measurable.

4. **Documentation-implementation gap:** header comment claimed "without recent tool-trace evidence" but the implementation is lexical-only over `last_msg`. Header rewritten with explicit `LEXICAL-ONLY` banner. Hook scope narrowed in documentation to cover only `UNSUPPORTED_OUTCOME_CLAIM` (manifestation 1 of FM25).

5. **Wrong constitution citation.** I cited "Principle 6" for the "≥2 sessions" recurrence rule. Principle 6 is phase-state artifacts; the recurrence rule lives in the "Self-Improvement Governance" section. Fixed in session-analyst.md at `de4dbfc`. Commit messages for e5a53d3 and 53bbd99 retain the miscitation because splitting/rewriting history would conflict with another active session's work.

6. **Template wording was temporally post-hoc.** Original `## Counterevidence sought` said "what would falsify the chosen option" — implying the decision was already made. Fixed to "the *leading candidate* option" with explicit "fill before writing the Decision section" instruction. Pre-decision by construction.

7. **Promotion criterion ignored recall entirely.** Original criterion was ≥60% precision + <10% trigger rate — but a narrow detector can hit that while missing most real cases. Added ≥50% recall floor (sampled from skipped sessions), zero-error-log requirement, and raised trigger rate headroom to 15% since lowering `success_hits` threshold will raise base rate.

**Explicit disagreement with reviewers:** both models prescribed splitting `bc51cb5` via interactive rebase to isolate the swept-up rename. I kept the bundled commit. Rationale: (a) local-only, never pushed; (b) the rename hunk is the correct state — reverting would restore broken `meta/` paths; (c) rebasing would conflict with another active agent-infra session that still has uncommitted rename work across many files. The disclosure in the commit message documents the taint; history surgery would cost more than the tainted audit trail saves. Noted as accepted-disclosure/rejected-surgery.

**Deferred findings (not fixed this pass, recorded for later):**
- Tool-only stop flows where the final assistant message is empty — hook currently skips these because lexical scope is `last_msg` only. Would need transcript tool-output fallback. Defer until shadow data shows how many real cases this branch would catch. (Finding 16)

Fix commit artifacts:
- `~/Projects/skills/hooks@e3b89c0` predicate/pattern/error-logging fixes
- `~/Projects/skills/hooks@4525d2c` 12-case pytest harness (7/12 would fail against HEAD~1)
- `de4dbfc` session-analyst citation
- `3bdc82e` FM25 scope table + template wording + ideas.md recall floor

<!-- knowledge-index
generated: 2026-04-11T19:47:16Z
hash: 90210c290e96

title: Oeberst & Imhoff Bias Framework — Coverage Audit of Agent Tooling
cross_refs: decisions/.template.md, research/compiled/agent-scaffolding-safety.md, research/domain-specific-agent-biases.md

end-knowledge-index -->
