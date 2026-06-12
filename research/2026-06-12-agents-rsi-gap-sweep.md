---
title: Agents + RSI Gap Sweep — window delta, weight-level, goal-learning, harness optimization
date: 2026-06-12
tags: [rsi, self-improvement, governance, harness-optimization]
status: active
---

# Agents + RSI Gap Sweep — 2026-06-12

**Question:** What agent/RSI work exists that our corpus doesn't already cover? Four axes:
(1) new work in window 2026-05-27 → 2026-06-12; (2) weight-level self-improvement;
(3) goal/constitution learning from operator feedback; (4) harness optimization beyond AutoAgent.
**Tier:** Deep (4 parallel researcher dispatches, epoch pattern). **Date anchor:** 2026-06-12.
**Ground truth (not repeated):** `rsi-verification-bound.md` (2026-06-03),
`self-evolving-governance-architecture.md` (2026-05-29), `autoagent-self-optimizing-agents.md`,
`agent-self-modification.md`, `meta-harness-deep-dive-2026-03.md`,
`hutter-evolver-architecture-2026-06`, 4-week compiled brief through 2026-05-27.

**Axis detail files (full claims tables + provenance live there):**
- `research/scratch/2026-06-12-rsi-gap-axis1-window.md` — 15 verified new items in window
- `research/scratch/2026-06-12-rsi-gap-axis2-weights.md` — SEAL/DGM/TTT/continual-learning, 13 claims
- `research/scratch/2026-06-12-rsi-gap-axis3-goals.md` — 18 graded claims on amendable specs
- `research/scratch/2026-06-12-rsi-gap-axis4-harness.md` — 11 claims, transfer/Goodhart evidence

---

## The cross-axis synthesis (one paragraph)

All four axes converge on the same shape, which **sharpens** (not just confirms) our
verification-bounded-RSI thesis: self-improvement works exactly where there is a hard accept-gate
(regression replay against held-out tasks, sequential-hypothesis-test commit gates, human
ratification) and fails predictably where acceptance is greedy or self-judged. And the layer that
actually improves and transfers is **structure** — harness code, tools, memory architecture,
externalized state — while the two adjacent layers fail: **weights** (catastrophic forgetting +
cost wall; nothing weight-level works at frontier scale as of 2026-06) and **prompt text**
(overfits the optimizing model; PromptBridge "Model Drifting", Prompt Genotyping R²=0.86 synthetic
→ −0.13 real). The sharpening: PACE formalizes WHY greedy self-improvement drifts — the acceptor
is an uncontrolled adaptive multiple-testing procedure (self-p-hacking), producing 30–42% false /
10–33% harmful commits; the fix is an anytime-valid statistical gate, i.e. **the accept-gate is
the load-bearing component of any RSI loop, not the proposer.**

## Highest-signal new results

| Finding | Source | Why it matters here |
|---|---|---|
| **PACE**: greedy "keep if score up" = self-p-hacking; 30–42% false commits; e-process/testing-by-betting gate controls false-commit probability under optional stopping | arXiv:2606.08106 [PREPRINT] | Most load-bearing RSI-safety result of the window. Read full text before the next self-improvement-loop design decision (hutter Grinder/Dreamer, /improve loops). Toy-scale models (Qwen2.5 0.5B–3B) but the statistics are scale-independent method. |
| **Self-Harness**: agent self-edits own harness, regression-gated; held-out Terminal-Bench-2.0 +15–21pp across 3 model families | arXiv:2606.09498 [PREPRINT] | Spiritual successor to Harness-1; the self-edit + regression-gate combo is our Grinder pattern published. |
| **Weight-level verdict**: SEAL lineage (incl. SCoL successor arXiv:2605.07076) works at 1B–7B toy scale only; catastrophic forgetting author-confirmed; the frontier continual-learning results (JitRL arXiv:2601.18510, 30× cheaper than weight-RL; ATLAS) are deliberately **gradient-free** | axis-2 file, claims 1–4, 11–12 | The field is voting against deployment-time weight updates. DGM/HGM/Live-SWE-agent reach frontier numbers but are frozen-model harness evolution — weight-level RSI remains unsolved, consistent with verifier-bound thesis. |
| **HGM "Metaproductivity-Performance Mismatch"**: current benchmark score is a poor predictor of self-improvement potential; clade-aggregated descendant performance (CMP) beats DGM's score-greedy expansion at lower cost | arXiv:2510.21614, ICLR 2026 Oral | Direct critique of greedy selection in self-improving trees; pairs with PACE as the two acceptor-design results. |
| **Harness optimization is now a named sub-field**: survey (Code as Agent Harness, arXiv:2605.18747, 42 authors), benchmark+toolkit (VeRO/VeRO-Bench, Scale AI, arXiv:2602.22480), ~6 systems (Meta-Harness, AHE, Self-Harness, MOSS, AEvo, ABSTRAL) | axis-4 file | Convergent design across labs: coding-agent proposer + filesystem trace access + regression-gated promotion. Matches our git-bus/clean-verifier design. VeRO-Bench is the reference benchmark if we ever measure our loop externally. |
| **Transfer is conditional on the edited layer**: structural/tool/memory edits transfer cross-model (AHE +5.1–10.1pp cross-family; Meta-Harness +4.7pt over 5 held-out models; HGM cross-model+cross-benchmark); prompt-text edits overfit | axis-4 file §(b); AHE numbers Grade B+ (verify arXiv:2604.25850 before quoting) | Validates `state-externalization-lens` empirically and argues against prompt-level meta-tuning as a standing loop. |
| **Goal/constitution learning validates our composite**: amendable rule-sets from accumulated evidence (COCOA EMNLP 2025, MAC, CCAI, Claude's own amendment clause), case-law layer (Case Repositories arXiv:2311.10934, Case Law Grounding), text-spec-over-learned-reward (Gao/Skalse Goodhart + spec-gaming worsens with reasoning RL, arXiv:2605.02269) | axis-3 file, 18 claims | The full composite we run (human-owned goals + agent-proposed amendments + recurrence-gated promotion ladder + git provenance) is **unpublished** — a genuine novelty pocket. Claude's constitution practicing "guidelines = cached derivations, explicable by reference upward" is amortized governance in the wild — directly relevant to this session's goal-vs-constitution discussion. |
| **Self-amendment drift is measured, and the prescribed fix is our design**: "Layered Mutability" identity-hysteresis 0.68 — reverting self-description after memory accumulation fails to restore baseline; amendment activity (not initial authoring) is where drift silently accumulates; mitigation = external-trigger gates | arXiv:2604.14717 [VERIFIED]; georgesamuelson.com 2026-05-14 [SECONDARY, C] | The strongest endorsement of human-ownership + recurrence gate + git audit trail arrives as the *disconfirmation* literature of auto-amending systems. |
| **Vendor convergence on async memory consolidation**: Anthropic "Dreaming" (Managed Agents; Harvey ~6× completion, self-reported) and OpenAI "Dreaming" (ChatGPT memory) both shipped in-window | claude.com + openai.com [VENDOR] | Between-session memory consolidation is now a shipped pattern, not research. Note: we vetoed native memory pruning (`autodream-disabled-append-only-conflict`) — the vendor version consolidates a *separate* store without mutating input, which is a different design than the one we vetoed; worth a look before dismissing. |
| **Anthropic Institute "When AI builds itself"**: >80% of merged production code Claude-authored (self-reported); calls for verifiable global pause mechanism | Anthropic blog [VENDOR] | Vendor-internal datapoint quantifying coding-loop closure; follow-up to (not repeat of) our verifier-bound corpus. Verify the 80% figure at the primary blog before citing. |

## Disconfirmation coverage (healthy across all axes)

- **Fluent Reflection, No Correction** (OpenReview, 8 frontier LLMs): reflection adds only +0.216
  pass rate on open-ended rule-constrained generation; second passes repeat near-identical prior
  violations. Frontier-tested — passes our timeliness bar. Self-correction estimates from
  closed-ended tasks are inflated.
- **Tail Knowledge Collapse** (TailSkills, OpenReview): recursive rewriting of skill artifacts into
  shorter/standardized variants preserves common-case utility while degrading rare exception
  handling (208 oracle-verified exception tasks). **Direct caution for our skill-rewrite and
  "slim the rule file" instincts** — pairs with "Guarded Delta Patches" (store deltas, not
  rewrites) as mitigation candidate.
- **CAI model collapse** (arXiv:2504.04918): self-critic-on-self-output recursion degrades smaller
  models (−9.8% helpfulness). We avoid this class: amendments are human-ratified text, not
  recursive training data.
- **Diversity collapse under RLVR** (arXiv:2509.07430): Pass@1 up, Pass@k down + forgetting —
  pathology of the exact reward signal SEAL-style loops use.
- **When Gradients Collide** (ACL 2026 wksp): multi-objective prompt optimization failed to beat
  the initial prompt in 6/10 configs — multi-criteria harness objectives are a failure surface.

## Quiet areas (searched, nothing found)

- No new theoretical RSI convergence/safety bound beyond the commit-gate framing (PACE) and
  physical-skill verification (VASO arXiv:2606.05395).
- No in-window follow-ups citing AutoAgent / CORAL / Harness-1 / SlopCodeBench / CAID by name.
- Meta (FAIR): no agent-RSI release in window.
- "Amortized governance" / "principles as cached derivations" as a named thesis: unpublished
  (substance exists scattered — Claude's constitution, case-law alignment papers).

## Deferred alternatives surfaced (per policy — flagged, not adopted)

1. **Active preference elicitation** (GATE arXiv:2310.11589, ADAPT, PAHF arXiv:2602.16173): agents
   that proactively ask taste/goal-disambiguating questions at uncertainty boundaries, vs our
   passive `#f` absorption. Deferring because: must stay inside the `feedback_question_scope`
   boundary (taste/intent/risk only), and doesn't yet clear the recurs-2+ governance bar. The
   `interview-prompt` skill already covers part of this surface manually.
2. **Amendment-time drift check**: a structure-fit/baseline-diff check fired specifically on
   constitution/rule *amendments* (the documented silent-drift surface per Layered Mutability +
   Recursive Governance Vulnerability). Hookable. Deferring: no observed drift incident here yet;
   log this as the pre-registered trigger — first observed governance-amendment drift incident
   promotes this to a hook.
3. **AHE "falsifiable contract" pattern**: every self-improvement edit ships with a self-declared
   prediction verified next round. Cheap, adoptable in the hutter Grinder loop and /improve.
   Deferring to the next hutter design session — read AHE (arXiv:2604.25850, verify ID) and PACE
   full texts first.
4. **PACE-style e-process accept-gate** for any standing self-improvement loop we run. Same next
   step: full-text read before design adoption.

## What's uncertain

- All percentage figures across axes are abstract/blog-reported, not reproduced; OpenReview items
  are anonymous ACL ARR submissions under review.
- AHE's numbers (arXiv:2604.25850) are Grade B+ — abstract via Exa only, ID not curl-verified.
- Vendor metrics (Harvey 6×, Anthropic >80%) are self-reported.
- scite stance checks are uninformative on Feb–Jun 2026 preprints (too recent for polarity
  classification) — directional claims rest on primary-paper reading.
- The recurrence-gate threshold ("recurs 2+ sessions") has no published analog and is empirically
  untested — we don't know 2 is right.
