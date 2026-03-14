# Cross-Model Review: Epistemic Architecture v3
**Mode:** Review (convergent)
**Date:** 2026-03-13
**Models:** Gemini 3.1 Pro (streaming API), GPT-5.4 (reasoning-effort high)
**Constitutional anchoring:** Yes (CLAUDE.md Constitution + GOALS.md)
**Extraction:** 36 items extracted, 22 included, 5 deferred, 4 merged, 0 rejected

---

## Verified Findings (adopt)

### Tier 1 — Both models converge, high confidence

| IDs | Finding | Verification |
|-----|---------|-------------|
| G2, P14, P16 | **No supervision KPI.** Plan measures errors but has no mechanical link to declining supervision. Need SLI (supervision load index), AIR (alert intervention rate), AGR (autonomy gain rate). | Verified: constitution says "measured by declining supervision" but plan has zero supervision metrics. |
| G6, P4, P12 | **No fail-open semantics.** Measurement hooks lack coverage/abstain/confidence output. API failures (scite, Kalshi) will either crash or create false confidence. | Verified: no fallback mechanism specified for any Layer 1/2 check. |
| G14, G1 | **Prune Phase 2 to ONE domain.** 13 items across 3 domains is scope bloat for solo dev. Pick trading first (market feedback = measurable ground truth). | Verified: constitution says measure before enforcing; parallel domain buildout skips validation. |
| P3, P15 | **Shadow-mode before enforcement.** Every new metric needs shadow run → validate → then enforce. Prevents "bad scaffolding worse than none" (our own Principle 3). | Verified: Girolli 2026 proves this empirically. Plan currently jumps from design to deployment. |

### Tier 2 — One model found, verified against code/logic

| IDs | Finding | Verification |
|-----|---------|-------------|
| G4, G5 | **ACC-lite requires data exhaust logging NOW.** Phase 3 trajectory calibration needs behavioral proxy features (tool-call churn, backtracking, self-correction) logged in Phase 1 JSONL. | Verified: we already have JSONL transcripts but don't extract structured features from them. Simple addition to session pipeline. |
| G9 | **Universal Disconfirmation Scaffold > 3 separate domain checks.** One mechanism parameterized by project path. Trading: "3 data points contradicting thesis." Research: "2 papers refuting mechanism." Engineering: "2 distributional shifts that break this." | Not verified against code (doesn't exist yet). Architecturally sound — simpler and more maintainable. |
| P11 | **Replay harness for Phase 3 items.** Test ACC-lite, belief drift, Goodhart detection offline using archived session transcripts before live deployment. | Verified: ~200+ session transcripts exist in ~/.claude/projects/. Replay is feasible and cheap. |
| P10 | **ROI execution order: #4 → #9 → #1 → #3.** GPT's quantitative ROI ranking is well-justified. | Verified: #4 (anonymize, 30min) and #9 (routing hook, 2hrs) are highest ROI. #1 (scite, 2.5hrs) and #3 (KalshiBench, 2hrs) follow. |

### Other Verified Findings

| IDs | Finding | Verification |
|-----|---------|-------------|
| P8 | **n≥8 Goodhart detection is statistically weak.** Need |r|~0.71 for p<.05 at n=8. Raise to n≥20 or use Bayesian. | Math checks out. n≥8 is too noisy. |
| P9 | **Impact Gini measures prestige, not quality.** Replace with evidence-type diversity or contradiction coverage. | Valid: a review citing 10 journals of equal impact factor scores well on Gini but could still miss contradictions. |
| P2 | **Confirmation bias undertreated.** Claimed as biggest threat but only 2/13 items measure it. | Verified against plan: only #5 (thesis challenge) and #11 (missed negative rate). |
| G15 | **Structural proxies > LLM-judged reviews.** Deterministic tool-use booleans are cheaper. | Valid: "did agent call contrasting search API? yes/no" is free and reliable. |
| G17 | **Lazy disconfirmation risk.** Agent may find weak strawmen instead of real counterarguments. | Real concern — measure disconfirmation QUALITY not just presence. |
| P6 | **Single-path routing too coarse.** Add multi-label override for mixed-domain projects. | Valid: biotech investing spans trading + research. Add .claude/epistemic-domain override file. |
| P7 | **ACC-lite is experiment, not commitment.** Relabel in plan. | Correct framing given Q1 is unanswered. |
| G11 | **Simple Goodhart ratios now.** Track tool_calls:confidence. If confidence rises while tool calls drop to zero → Goodharting. | Cheap, observable today with existing transcripts. |

---

## Deferred (with reason)

| IDs | Finding | Why Deferred |
|-----|---------|-------------|
| G10 | Cheap consensus hallucination via keyword search | Scite is already zero-cost (user-scope MCP). Scite stance classification is more precise than "contradicts" keyword search. |
| G12 | <draft>/<critique>/<final> XML tags as ACC proxy | Interesting but adds structural burden to output format. Experiment after ACC-lite viability is assessed. |
| P5 | Architecture ahead of measured recurrence | Valid caution but 25+ research memos documenting the same failure modes IS recurrence evidence. |
| P18 | Fold detector may be underrated | Need compaction frequency data first. Check transcripts. |
| G7 | Model-review is token-intensive | Item 4 is a 30-min prompt edit to remove model labels, not a new judge pipeline. Misread of the plan. |

---

## Where I Was Wrong

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|---------------|
| Plan serves constitutional principle of declining supervision | Plan has ZERO supervision metrics — only error metrics. Measurement without an autonomy ratchet is dashboard vanity. | Both (G2, P14) |
| n≥8 is sufficient for Goodhart detection | Statistically weak — need |r|~0.71 at n=8 for significance. False positive rate likely >25%. | GPT (P8) |
| Impact Gini captures citation bias | Measures prestige concentration, not evidence quality. Wrong proxy. | GPT (P9) |
| 13-item phased plan is realistic | Scope bloat for solo dev. Prune to ONE domain first, validate, then expand. | Both (G1, G14) |
| Phase 1-3 sequencing is correct | Phase 1 needs data exhaust logging to unblock Phase 3 ACC-lite. Currently missing. | Gemini (G4) |

---

## Gemini Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| "Scite API costs will shatter $25/day budget" | Scite is a user-scope MCP server — no per-query API cost. Gemini assumed commercial API pricing. |
| "Item 4 (anonymize) = LLM-as-a-judge" | Item 4 is removing model labels from review prompts (30 min edit), not building a new judge pipeline. Misread. |
| "Cheap PubMed keyword search as scite alternative" | Keyword search for "contradicts" is far less precise than scite's 1.6B classified citation stance data. |

---

## GPT Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| "Composite constitutional score: 6.0/10" | Fabricated weighted scoring. The weights (0.35, 0.25, 0.20, 0.10, 0.10) and per-principle scores are GPT inventions — no methodology provided. The *findings* behind the scores are valid; the *numbers* are not. |
| "#2 Fold detector ROI rank 7" | GPT likely underweights fold detection because it doesn't know compaction is frequent in our sessions. Rank depends on actual compaction frequency. |
| "SLI formula: manual review minutes + 5*hard stops + 2*overrides" | Weights (5, 2) are fabricated. The concept (supervision load metric) is valid; the formula needs empirical tuning. |

---

## Revised Plan (incorporating review findings)

### Changes to Epistemic Architecture v3

1. **Add supervision KPIs to Layer 2** (G2/P14): Track manual review minutes/session, alert intervention rate, and autonomy gain rate. These are the constitutional north star, not error counts.

2. **Add fail-open + coverage semantics** (G6/P4): Every Layer 1/2 check outputs `{result, coverage, confidence}`. On API failure: `{result: null, coverage: 0, confidence: 0}` → agent proceeds with warning, not crash.

3. **Prune Phase 2 to trading only** (G14): Build thesis challenge metric. Run 20 sessions. Prove it correlates with outcome quality. THEN expand to research and engineering.

4. **Shadow-mode all new checks** (P3): New metrics run in advisory mode for 2 weeks before any enforcement. Kill metric if FP rate >30%.

5. **Add data exhaust logging to Phase 1** (G4): Extract structured features from JSONL per session: tool_call_count, failure_count, backtrack_count, query_reformulation_count, disconfirmation_phase_duration. Saves to epistemic-metrics.jsonl. Unblocks ACC-lite in Phase 3.

6. **Replace Impact Gini with contradiction coverage** (P9): Measure `contrasting_citations_found / total_synthesis_claims` instead of journal prestige distribution.

7. **Raise Goodhart threshold to n≥20** (P8): Add simple tool_calls:confidence ratio check now (G11) as a cheap interim.

8. **Relabel ACC-lite as experiment** (P7): Not a Layer 0 commitment until Q1 is answered with replay data.

9. **Add multi-label domain routing override** (P6): `.claude/epistemic-domain` file for mixed projects.

10. **Universal Disconfirmation Scaffold** (G9): One parameterized mechanism instead of 3 separate domain implementations.

11. **Build replay harness** (P11): Test Phase 3 items offline before live deployment.

### Revised Execution Order (per GPT ROI analysis)

**Week 1:** #4 anonymize (30min) → #9 routing hook (2hrs) → data exhaust logging (4hrs)
**Week 2-3:** #1 scite in Phase 4 (2.5hrs) → #3 KalshiBench canaries (2hrs) → fail-open decorator (2hrs)
**Month 2:** Trading thesis challenge only → 20 sessions → validate
**Month 3:** Replay harness → ACC-lite experiment → supervision KPIs
