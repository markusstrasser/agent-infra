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

*None yet.*

<!-- knowledge-index
generated: 2026-04-11T19:07:52Z
hash: f2e58b6c6f94

title: Oeberst & Imhoff Bias Framework — Coverage Audit of Agent Tooling
cross_refs: research/compiled/agent-scaffolding-safety.md, research/domain-specific-agent-biases.md

end-knowledge-index -->
