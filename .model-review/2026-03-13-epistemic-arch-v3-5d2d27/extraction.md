# Extraction + Disposition: Epistemic Architecture v3 Review

**Date:** 2026-03-13
**Models:** Gemini 3.1 Pro (streaming API), GPT-5.4 (reasoning-effort high, streaming)
**Constitutional anchoring:** Yes (CLAUDE.md Constitution + GOALS.md)

---

## Extraction: Gemini Pro

G1. Scope bloat — 13 items across 3 layers in 3 months is enterprise-scale for solo dev
G2. Missing "Autonomy Ratchet" — no mechanical link where good metrics automatically reduce HITL gating
G3. API cost/rate-limit vulnerability — Scite, Kalshi, cross-model evals can shatter $25/day budget
G4. ACC-lite requires data exhaust logging in Phase 1 — Phase 3 is DOA without Phase 1 trace logging
G5. Need standardized trace_logger.py in Phase 1 for behavioral proxy features
G6. Need @fail_open decorator for all measurement hooks — API fragility will stall agents
G7. Model-review anonymization (item 4) is cheap but model-review itself is token-intensive
G8. Supervision decay logic missing — no thresholds for when agent earns autonomy
G9. Consolidate Layer 1 into ONE universal "Disconfirmation Scaffold" with domain-specific prompts
G10. Cheap consensus hallucination alternative: PubMed/ArXiv contradicting query before Scite
G11. Goodhart detection via simple ratios now (token length:reward, tool calls:confidence)
G12. "Show Your Work" trajectories: enforce <draft>/<critique>/<final> XML tags as cheap ACC proxy
G13. Priority: Move data exhaust logging to Phase 1 week 1
G14. Priority: Prune Phase 2 to ONE domain first — prove thesis challenge correlates before expanding
G15. Swap LLM-based reviews for structural proxies (deterministic tool-use boolean checks)
G16. Constitutional alignment: "Maximize autonomy" FAILED — plan measures but doesn't mechanically reduce supervision
G17. "Lazy disconfirmation" risk — frontier models find weak strawmen, not real counterarguments

## Extraction: GPT-5.4

P1. Only ~5/13 items are domain-specific (Layer-1) despite Principle 1 saying measure domain damage first
P2. Agent confirmation bias claimed as biggest threat but only 2 items directly measure it (#5, #11)
P3. "Measure before enforcing" conflicts with structural forcing — need shadow-mode → validate → enforce
P4. Sparse scite coverage creates false confidence — every monitor needs coverage/abstain/confidence output
P5. Architecture is ahead of measured recurrence — promote only patterns with measured frequency
P6. Single-path routing too coarse for mixed projects (biotech investing, scientific engineering)
P7. ACC-lite positioned as architecture before Q1 is answered — treat as experiment, not commitment
P8. Goodhart detection at n≥8 is statistically weak (need |r|~0.71 for p<.05) — raise to n≥20-30
P9. Citation-impact Gini measures prestige concentration, not evidence quality — replace metric
P10. ROI ranking: #4 (anonymize) → #9 (routing) → #1 (scite) → #3 (KalshiBench) as top 4
P11. Build replay harness from archived sessions before live rollout of Phase 3 items
P12. Every monitor needs explicit coverage/abstain/confidence output for fail-open behavior
P13. Replace proxy-heavy metrics (Gini, n≥8 correlations) with outcome-linked ones
P14. Need supervision KPIs: SLI (supervision load index), AIR (alert intervention rate), AGR (autonomy gain rate)
P15. Shadow-mode promotion/kill criteria for every new metric before enforcement
P16. Constitutional composite score: 6.0/10 — main miss is autonomy KPI
P17. Impact Gini R² with correction rate likely <0.05 — weak predictor
P18. Fold detector may be underrated if compaction is a frequent real failure
P19. n≥8 Goodhart alerts predicted >25% FP rate

---

## Disposition Table

| ID | Claim | Disposition | Reason |
|----|-------|-------------|--------|
| G1 | Scope bloat for solo dev | INCLUDE | Valid — both models flag this. Prune to essentials. |
| G2, P14, P16 | Missing autonomy ratchet / supervision KPIs | INCLUDE — Tier 1 | Both models independently. SLI/AIR/AGR concrete. Gap is real. |
| G3 | API budget vulnerability | INCLUDE | Valid but mitigated: Scite is user-scope MCP (no API cost), Kalshi is 5 queries (trivial). Flag for monitoring. |
| G4, G5, G13 | Data exhaust logging needed in Phase 1 for ACC-lite | INCLUDE — Tier 2 | Valid dependency. Move trace feature logging earlier. |
| G6, P4, P12 | @fail_open + coverage/abstain semantics | INCLUDE — Tier 1 | Both models. Critical architectural gap. |
| G7 | Model-review is token-intensive | DEFER | Item 4 (anonymize) is 30min prompt edit, not a new LLM judge pipeline |
| G8 | Supervision decay thresholds missing | MERGE WITH G2/P14 | Same finding — the autonomy ratchet |
| G9 | Universal Disconfirmation Scaffold | INCLUDE — Tier 2 | Elegant: one mechanism, domain-parameterized. Simpler than 3 separate implementations. |
| G10 | Cheap consensus hallucination via existing search | DEFER | Scite is already available at zero cost (user-scope MCP). PubMed keyword search less precise than scite stance classification. |
| G11 | Simple Goodhart ratios now | INCLUDE | Good — cheaper than n≥20 correlation. Tool calls:confidence is directly observable. |
| G12 | <draft>/<critique>/<final> XML as ACC proxy | DEFER | Interesting but adds structural forcing to agent output format — may interfere with normal operation. Experiment later. |
| G14 | Prune Phase 2 to ONE domain first | INCLUDE — Tier 1 | Both models. Focus on trading (most measurable feedback via market outcomes). |
| G15, P13 | Structural proxies over LLM-judged reviews | INCLUDE | Deterministic tool-use booleans are cheaper and more reliable. |
| G16 | Constitutional "maximize autonomy" failed | MERGE WITH G2/P14 | Same finding |
| G17 | Lazy disconfirmation risk | INCLUDE | Real concern. Measure disconfirmation quality (did it find actual contradictions?) not just presence. |
| P1 | Only 5/13 items are Layer-1 | INCLUDE | Valid observation. Rebalance toward domain-specific measurement. |
| P2 | Confirmation bias undertreated (only 2 items) | INCLUDE | Aligned with own Principle 2 — add counterevidence coverage primitive. |
| P3 | Shadow-mode before enforcement | INCLUDE — Tier 1 | Directly implements "measure before enforcing" + "bad scaffolding worse than none." |
| P5 | Architecture ahead of measured recurrence | DEFER | Valid caution but the 25+ memos ARE the recurrence evidence — just documented differently. |
| P6 | Single-path routing too coarse | INCLUDE | Add multi-label override in project .claude/ config. Cheap fix. |
| P7 | ACC-lite as experiment, not commitment | INCLUDE | Correct framing. Relabel as experiment. |
| P8, P19 | n≥8 statistically weak | INCLUDE | GPT correct on the math. Raise to n≥20 or use Bayesian estimates. |
| P9, P17 | Impact Gini is wrong metric | INCLUDE | Replace with evidence-type diversity or contradiction coverage. |
| P10 | ROI ranking: #4→#9→#1→#3 | INCLUDE | GPT's ranking is well-justified. Adopt as execution order. |
| P11 | Replay harness before live rollout | INCLUDE — Tier 2 | High-leverage: test Phase 3 items offline using archived sessions. |
| P15 | Shadow-mode kill criteria per metric | MERGE WITH P3 | Same pattern |
| P18 | Fold detector may be underrated | DEFER | Need data — check compaction frequency in existing transcripts first |

---

## Coverage
- Total extracted: 36 items (17 Gemini, 19 GPT)
- After merge: 30 unique
- INCLUDE: 22
- DEFER: 5
- MERGE: 4 (merged into INCLUDEs)
- REJECT: 0
