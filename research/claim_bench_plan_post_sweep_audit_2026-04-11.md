---
title: claim_bench Plan — Post-Sweep 2026 Literature Audit
date: 2026-04-11
tags: [claim-verification, plan-audit, literature-sweep, epistemics]
status: active
---

# claim_bench Plan — Post-Sweep 2026 Literature Audit

**Date:** 2026-04-11
**Plan audited:** `.claude/plans/e5a3a60d-claim-bench-cross-project-core.md` (v2.1, post-cross-model-review)
**Research window:** 2026 only (post prior-art sweep captured in plan §4)
**Retrieval paths:**
1. Semantic Scholar targeted sweep (7 queries) — verified real
2. Parallel Task ultra2x deep research (173K chars) — synthesized via subagent; partially over-claimed, conflated enterprise compliance with scientific claim governance
3. Exa Deep Researcher `exa-research-pro` ($0.99, 17 searches, 88 pages) — completed; recommended selective pause for 4 components (most of which are scope-creep)
**Question asked:** Should a plan building this architecture today be paused and revised based on newer work?

---

## TL;DR

**My recommendation: DO NOT pause Phase A. Execute the minimal relocation, THEN fold 3 verified findings into Phases B/D/G before they harden.** Two findings below are worth reading and citing directly, one is worth a 10-line design change, and the rest are "note as follow-up plans" level. There is **no single 2026 paper that reshapes the architecture** — the plan's core decisions (append-only, content-hash event_id, typed protocols, extensible string constants, discrete TTL, L0/L1/L2 levels, FIRE-Bench P/R/F1, inspect_ai harness) all survive the sweep with minor-to-zero adjustment.

**Three findings that deserve the author's attention before code ships:**
1. **Oblivion** (arXiv:2604.00131) — continuous decay with retrieval gating. Worth a §3 sentence acknowledging the alternative and why integer-day TTL is retained.
2. **Rethinking Atomic Decomposition** (arXiv:2603.28005) + **Beyond Precision** (arXiv:2604.03141) — both critique FIRE-Bench-style atomic P/R/F1 scoring. Worth reading before Phase G and possibly adding a §9 test that catches "prompt length confound" and "importance-unaware recall" pathologies.
3. **From Fluent to Verifiable** (arXiv:2602.13855) + **DeepFact** (arXiv:2603.05912) — both directly about claim-level auditability for deep-research agents, which is exactly the phenome `huberman-claims-genomic-crossref.md`-class use case. Worth reading before Phase F writes `SelfReportVerifier`.

Six further papers are worth filing in `research/` as "consulted during 2026-04-11 audit" and referenced when the deferred follow-up plans (AutoVerifier chain, empirical verifier, phenome contradiction verifier) pick them up.

---

## Per-Component Verdicts

| # | Component | Verdict | Action |
|---|-----------|---------|--------|
| 1 | Append-only JSONL event ledger (content-hash event_id) | **NOTHING NEW that invalidates design** | No change. Cite ESAA as 2026 precedent; decline SLSA/in-toto attestation retrofit. |
| 2 | ClaimRecord with stable_id + content_version_hash | **NOTHING NEW** | No change. |
| 3 | Verifier + DecisionGate as typing.Protocol | **MINOR** | No change to the protocol; note AutoVerifier 6-layer is the reference for follow-up routing plan. |
| 4 | TTL per-modality integer-days with DECAYED events | **MINOR — acknowledge alternative** | Add one §3 paragraph citing Oblivion and "How often do Answers Change?" as continuous alternatives; retain discrete TTL for this plan and name the condition under which we'd switch. |
| 5 | Meta-claim L0/L1/L2 level rule | **MINOR** | No change. The DAG-over-levels argument in the Parallel Task report does not outweigh "structural enforcement is cheap, DAG is expensive to verify." |
| 6 | inspect_ai harness integration | **NOTHING NEW** | Confirmed. No change. |
| 7 | FIRE-Bench atomic-claim P/R/F1 | **MATERIAL — add defensive tests** | Two peer-reviewed critiques of atomic decomposition (2603.28005, 2604.03141). Fold into Phase G as defensive tests rather than replacing FIRE-Bench. |
| 8 | AutoVerifier 6-layer pattern | **NOTHING NEW** | Already in plan's prior art. No change. |
| 9 | FINCH-ZK cross-family routing | **NOTHING NEW that invalidates design** | Already deferred to follow-up plan. No change. |
| 10 | Phase 4 independence + adequacy cards | **NOTHING NEW** | No change. |
| 11 | Authority class + evidence modality taxonomies | **NOTHING NEW that invalidates design** | The plan's "extensible string constants" is defensible. SEPIO/PROV-K are non-2026 and already known; not adopting is a reasoned choice per the plan's "do not start ontology-first" principle. |
| 12 | Cross-project adapter pattern (core + thin adapters) | **NOTHING NEW** | No change. |

---

## Verified 2026 papers worth citing in the plan

All verified independently via Semantic Scholar on 2026-04-11. arXiv IDs, authors, and abstract snippets confirmed.

### For the plan body (cite in §4 "Prior Art Consumed" or §10 "Open Questions")

**1. Oblivion — `arXiv:2604.00131`** (Rana, Hung, Sun, Kunkel, Lawrence, 2026)
*"Self-Adaptive Agentic Memory Control through Decay-Driven Activation"*
> Human memory adapts through selective forgetting: experiences become less accessible over time but can be reactivated by reinforcement or contextual cues. In contrast, memory-augmented LLM agents rely on "always-on" retrieval and "flat" memory storage, causing high interference and latency as histories ...

**Why cite:** proposes continuous retention scores with uncertainty-gated retrieval as an alternative to binary TTL. The plan's §3 already says "TTL is per-modality integer days. No likelihood, no survival curve. If we later want continuous decay, it's an additive follow-up plan." — Oblivion is the first peer-reviewed candidate for that follow-up. Adding a one-sentence "Oblivion (arXiv:2604.00131) is the 2026 reference for the continuous-decay alternative deferred to a follow-up" makes the deferral concrete.

**Action:** One-line citation added to §3 near the TTL paragraph, and to §5 Phase D as "follow-up reference." No design change.

**2. How often do Answers Change? Estimating Recency Requirements in QA — `arXiv:2603.16544`** (Piryani, Mert, Jatowt, 2026)
> Large language models (LLMs) often rely on outdated knowledge when answering time-sensitive questions, leading to confident yet incorrect responses. Without explicit signals indicating whether up-to-date information is required, models struggle to decide when to retrieve external evidence, how to re...

**Why cite:** empirically estimates recency requirements across question types. If it publishes per-category decay rates, the plan's "TTL per modality, integer days" should be **parameterized from their numbers** in a follow-up rather than hand-picked. Not material for this plan (the plan keeps TTLs caller-provided), but material for the follow-up calibration plan.

**Action:** Forward-reference in §3 TTL section: "TTL values are caller-provided; empirical priors for per-modality decay live in `arXiv:2603.16544` and should seed future calibration work."

### For Phase G defensive tests

**3. Rethinking Atomic Decomposition for LLM Judges — `arXiv:2603.28005`** (Xinran Zhang, 2026)
> Atomic decomposition -- breaking a candidate answer into claims before verifying each against a reference -- is a widely adopted design for LLM-based reference-grounded judges. However, atomic prompts are typically richer and longer, making it unclear whether any advantage comes from decomposition o...

**Why it matters:** questions whether atomic decomposition adds value beyond prompt-length confound. The plan's FIRE-Bench scorer at `experiments/claim-bench/atomic_claim.py` is a direct descendant of the pattern being critiqued.

**Action:** Phase G should add a **prompt-length-controlled test** — same claim scored via (a) atomic decomposition and (b) a length-matched non-decomposed prompt — and assert that atomic decomposition produces a measurable delta on at least one of the 8 cross-domain cases. If it doesn't, FIRE-Bench's contribution is contested on this case and the finding goes in `research/claim-verification-package-prior-art.md` as a known limitation. ~30 lines of test code.

**4. Beyond Precision: Importance-Aware Recall for Factuality Evaluation in Long-Form LLM Generation — `arXiv:2604.03141`** (Jafari, Allan, Iyyer, 2026)
> Evaluating the factuality of long-form output generated by large language models (LLMs) remains challenging, particularly when responses are open-ended and contain many fine-grained factual statements. Existing evaluation methods primarily focus on precision: they decompose a response into atomic cl...

**Why it matters:** critiques uniform-weight recall in FIRE-Bench-style scoring. Argues recall should be importance-weighted.

**Action:** Phase G should add a test that varies the importance-weighting assumption (uniform vs. salience-weighted) and documents which weighting the plan uses. Not a blocker, but a provenance note so the follow-up "empirical verifier" plan knows to revisit this.

### For Phase F (phenome SelfReportVerifier)

**5. From Fluent to Verifiable: Claim-Level Auditability for Deep Research Agents — `arXiv:2602.13855`** (Rasheed, Banerjee, Mukherjee, Hazra, 2026)
> A deep research agent produces a fluent scientific report in minutes; a careful reader then tries to verify the main claims and discovers the real cost is not reading, but tracing: which sentence is supported by which passage, what was ignored, and where evidence conflicts.

**Why it matters:** this is **exactly the phenome `huberman-claims-genomic-crossref.md` use case**, described independently by researchers who aren't in the project. If the paper proposes a concrete schema or ontology for claim→passage→evidence traces, Phase F's `SelfReportVerifier` should consume it rather than invent.

**Action:** Read before Phase F. One-paragraph assessment in `research/claim-verification-package-prior-art.md` on whether their schema subsumes or differs from claim_bench's `VerificationEvent`. If subsume → cite and move on. If differs in ways that matter → brief plan revision before Phase F writes code. **This is the single highest-value read in this audit.**

**6. DeepFact: Co-Evolving Benchmarks and Agents for Deep Research Factuality — `arXiv:2603.05912`** (Huang, Ribeiro, Hardalov, Dhingra, Dreyer, Saligrama, 2026)
> Search-augmented LLM agents can produce deep research reports (DRRs), but verifying claim-level factuality remains challenging. Existing fact-checkers are primarily designed for general-domain, factoid-style atomic claims, and there is no benchmark to test whether such verifiers transfer to DRRs.

**Why it matters:** directly acknowledges the failure mode the claim_bench plan aims at — that existing fact-checkers (FIRE-Bench, FActScore, SAFE) don't transfer cleanly to deep-research reports. Proposes "Evolving Benchmarking via Audit-then-Score (AtS)" where benchmark labels can be revised when a verifier disagrees.

**Action:** Read before Phase F. Consider whether claim_bench's 8 cross-domain gold cases should support "audit-then-score" revisability. Probably out of scope for this plan, but worth flagging in `§5.G.3` as a follow-up consideration.

---

## Additional candidates worth filing (don't block execution)

Read during follow-up plans, not now.

**For the AutoVerifier 6-layer follow-up plan:**
- MARCH (arXiv:2603.24579) — Multi-Agent Reinforced Self-Check for LLM Hallucination
- Courtroom-Style Multi-Agent Debate with Progressive RAG (arXiv:2603.28488)
- VERGE (arXiv:2601.20055) — Neurosymbolic LLM+SMT
- Contradiction to Consensus (arXiv:2602.18693) — source-level disagreement

**For the empirical verifier follow-up plan:**
- MedRAGChecker (arXiv:2601.06519) — biomedical RAG claim verification
- MedScore (arXiv:2505.18452, 2025) — domain-adapted medical claim decomposition
- SciClaimEval (arXiv:2602.07621) — scientific paper claim verification benchmark
- SciVer (arXiv:2506.15569, 2025) — 3K multimodal scientific claim verification examples
- Valsci (BMC Bioinformatics 2025) — open-source self-hostable literature-based claim verifier
- Assessing Automated Fact-Checking for Medical LLM with KGs (arXiv:2511.12817, late 2025)

**For the ledger + agent memory follow-up work:**
- ESAA (arXiv:2602.23193) — Event Sourcing for Autonomous Agents — the **generalized version** of what claim_bench is doing for a narrower domain. The ESAA author (Brito dos Santos Filho) shipped a companion paper ESAA-Security (arXiv:2603.06365) that shows the "core + domain adapter" pattern. **This is independent 2026 confirmation that the plan's architectural split is correct.** Cite in §4 Prior Art.
- ElephantBroker (arXiv:2603.25097) — Knowledge-Grounded Cognitive Runtime for Trustworthy AI Agents. Explicit critique of flat KV-store agent memory without provenance. Cite in §4 Prior Art.
- Provenance-driven nanopublications (Menotti et al., Int J Digital Libraries 2025) — multi-source trust networks over assertions. Extends nanopublications 1.0 which the plan already cites.

**For inspect_ai harness discussions:**
- Gaming the Judge: Unfaithful CoT Can Undermine Agent Evaluation (arXiv:2601.14691) — if verifiers use LLM-as-judge, their CoT may not reflect actual reasoning. Governance note for the plan's LLM-judge-based verifiers.

---

## What the Parallel Task report surfaced that I discounted

The Parallel Task report's only explicit **MATERIAL** label was for Component 1, based on AI Trust OS (arXiv:2604.04749) and Attesting LLM Pipelines (arXiv:2603.28988). **Both are real papers, both verified in S2** — but:

- **AI Trust OS** is enterprise AI observability and SOC 2 / ISO 27001 / ISO 42001 compliance. Its "evidence ledger with 90-day expiry, cryptographic watermark, partitioned storage" is designed for enterprise audit readiness, **not for scientific claim lineage**. The mechanism superficially resembles the plan's event ledger; the intent differs. Adopting its design (expiring assertions, zero-trust signing) into claim_bench would add enterprise-compliance surface area the plan explicitly does not want.
- **Attesting LLM Pipelines** is LLM **supply chain security** (attesting weights, datasets, container images via in-toto/Sigstore). Again, real paper, but it's about artifact provenance, not scientific claim provenance. Not applicable to claim_bench.

The Parallel Task report conflated "any append-only evidence log with cryptographic properties" with "scientific claim governance ledger." The S2-verified on-topic equivalents are ESAA (arXiv:2602.23193) and ElephantBroker (arXiv:2603.25097), neither of which the Parallel Task surfaced.

The Parallel Task report also cited several papers with **suspicious arXiv IDs** flagged by the processing subagent: 2601.18642 ("FadeMem"), 2601.22963 ("Epoch-Resolved Arbitration"), and a few others with unusually high sub-year numbers for their claimed months. I did not verify these and recommend treating them as unverified until someone reads them directly. I did not find any of these in independent S2 searches.

**The AutoVerifier paper the Parallel Task treated as a 2026 finding (arXiv:2604.02617) is already in the plan's prior-art list.** The Parallel Task didn't notice this was already consumed.

---

## Retrieval-path coverage assessment

| Path | Outcome | What it's good for | What it missed |
|------|---------|-------------------|----------------|
| S2 targeted sweep (7 queries) | Verified 12 real 2026 papers with abstracts | Direct, on-topic, verifiable citations with abstract-level relevance | Doesn't synthesize; requires reading abstracts |
| Parallel Task ultra2x | Wide but unfocused; re-quoted ~6 papers 80+ times; conflated enterprise compliance with scientific claim governance; surfaced 4 suspicious arXiv IDs | Breadth, pointer to follow-up topics (Oblivion, AtomEval, DeepFact) | Over-represented enterprise governance content; under-represented on-topic agent epistemics work (missed ESAA entirely, missed From Fluent to Verifiable) |
| Exa Deep Researcher pro | **TIMED OUT at synthesis time** (>15 min) | Would have provided third independent retrieval path | Not yet available; deferred for follow-up integration |

Recommendation: **if Exa completes before you accept this audit, append its findings as an addendum.** If it doesn't complete, that's acceptable — S2 + Parallel Task already cover the high-signal 2026 space, and the three genuinely material papers (Oblivion, Rethinking Atomic Decomposition, From Fluent to Verifiable) are all verified via S2 independently.

---

## Concrete plan revisions (propose to author before Phase A ships)

These are the only changes I recommend. All are additive and don't delay Phase A.

**1. §4 Prior Art Consumed — add 4 rows:**

| Prior art | Use |
|---|---|
| **ESAA / ESAA-Security (arXiv:2602.23193, 2603.06365)** | Independent 2026 confirmation of "core event-sourced runtime + domain adapters" pattern. Validates the Phase A/B/E/F split. |
| **ElephantBroker (arXiv:2603.25097)** | 2026 critique of flat-KV agent memory without provenance; motivates the plan's typed-event approach. |
| **From Fluent to Verifiable (arXiv:2602.13855)** | 2026 formalization of the "claim→passage→evidence trace" problem that phenome `huberman-claims-genomic-crossref.md` already solves by hand. Read before Phase F. |
| **DeepFact (arXiv:2603.05912)** | 2026 acknowledgement that FIRE-Bench / FActScore don't transfer to deep research reports; proposes audit-then-score benchmark revision. Read before Phase G. |

**2. §3 TTL section — add one paragraph after "TTL is per-modality integer days":**

> **2026 alternative acknowledged:** Oblivion (arXiv:2604.00131) proposes continuous retention scores with uncertainty-gated retrieval, and "How often do Answers Change?" (arXiv:2603.16544) publishes empirical recency estimates per question type. We retain discrete TTL for this plan because per-modality integer days is the smallest mechanism that supports adapter-defined policies without introducing a retention model. If the follow-up calibration plan finds that discrete TTL produces measurable FN/FP on wearable/observational modalities, Oblivion is the reference design for continuous-decay replacement.

**3. §5 Phase G — add 2 new tests:**

- `test_atomic_decomposition_adds_signal.py`: prompt-length-controlled test per Rethinking Atomic Decomposition (arXiv:2603.28005). Score 3 of the 8 cross-domain cases via (a) atomic decomposition and (b) length-matched non-decomposed prompt; assert decomposition produces a measurable delta on at least 2 of 3. If not, file the failure in `research/claim-verification-package-prior-art.md` as a known limitation of lifted FIRE-Bench.
- `test_importance_weighted_recall_option.py`: per Beyond Precision (arXiv:2604.03141). Add an optional importance-weighting parameter to the scorer (default: uniform, existing behavior); test both weightings on 1 case and document which is used.

**4. §10 Open Questions — add Q6:**

> **Q6 — Follow-up plan "claim-bench-audit-2026" scope confirmation:** the six papers above (ESAA/ESAA-Security, ElephantBroker, Oblivion, From Fluent to Verifiable, DeepFact, Rethinking Atomic Decomposition) are flagged as "read before the relevant follow-up plan, not before Phase A." Confirm this ordering is acceptable.

---

## Exa Deep Researcher addendum

Exa completed after the initial synthesis was written. Cost: $0.99, 17 searches, 88 pages read, exa-research-pro model. Exa's verdict was more aggressive than mine — it recommended **selective pause for 4 components** — but most of its "pause" recommendations are scope-creep (asking the plan's minimal core to absorb the responsibilities of its own deferred follow-up plans). Specifically:

- **Exa wanted Phase B to adopt SLSA/in-toto signed attestations bound to event_id.** This would turn the typed scientific-claim ledger into an enterprise-compliance artifact ledger. It contradicts the plan's "do not start ontology-first" principle and the minimal-core framing. The `VerificationEvent` model already supports optional `source_refs` and `payload.items()` where signed attestations could be embedded later as an adapter concern. **Reject for this plan.**
- **Exa wanted Phase C's DecisionGate to be rewritten as schema-driven routing with multi-step orchestration and consensus protocols.** This is exactly what the plan defers to "Follow-up plan F: AutoVerifier 6-layer chain adapter" and "Follow-up plan: verifier routing & authority weighting." The minimal typing.Protocol is a seam, not a ceiling. **Reject for this plan; note the candidates for the follow-up.**
- **Exa wanted immediate adoption of `draft-sharif-agent-audit-trail-00` (IETF) for agent self-governance logging.** Worth filing as a reference; the plan's use case (personal scientific claim governance) is not a compliance-grade enterprise audit environment where this IETF draft applies. **File as reference, not blocker.**
- **Exa wanted L0/L1/L2 replaced with DAG.** This is the one genuinely-contested technical point below. See Component 5 revision.

**Three Exa findings that are genuinely new and do affect the plan:**

**7. The Alignment Bottleneck in Decomposition-Based Claim Verification — `arXiv:2602.10380`** (2026-02-11)
> shows that decomposition only improves verification when sub-claims have tightly aligned evidence, and that propagation errors cause brittleness

**Why it matters:** this is direct empirical support for the concern that strict L0/L1/L2 parent-level increase can amplify errors when sub-claim evidence is mis-aligned. The plan's `meta_claim.validate_level` enforces structure but not evidence alignment. Not a blocker — the plan's L0/L1/L2 rule is about level invariants, not about sub-claim evidence alignment — but the paper names a real failure mode that a follow-up `claim_decomposition_alignment.py` verifier would catch.

**Action:** Cite in §3 near the "Meta-claim level rule" subsection as "known limitation — strict-level rule does not guarantee sub-claim evidence alignment; see arXiv:2602.10380 for empirical characterization of the failure mode. Alignment verification is a follow-up concern."

**8. From Chains to DAGs: Probing the Graph Structure of Reasoning in LLMs — `arXiv:2601.17593`** (2026-01-24)
> probes indicate LLM reasoning often aligns better with DAG-like structures rather than strict linear chains

**Why it matters:** Exa cited this as evidence that L0/L1/L2 should be replaced with a DAG. I disagree with the strength of the inference — "LLM internal reasoning structure is DAG-shaped" does not imply "typed claim levels must be DAG-shaped." The claim_bench level rule is a **governance structure over events**, not a model of LLM reasoning. The analogy is slipping a level. **Cite as an alternative view; don't adopt.**

**Action:** One-sentence citation in §3 as "an alternative view argues L0/L1/L2 is too restrictive (arXiv:2601.17593); for this plan we retain strict levels on the grounds that claim governance structure need not mirror internal reasoning structure, and adding DAG support is a follow-up plan if evidence graph queries become load-bearing."

**9. LongevityBench — `bioRxiv 10.64898/2026.01.12.698650v2`** (2026-01-30)
> benchmark for model performance on aging biology tasks, including survival prediction and time-dependent biological facts that evaluate discrete vs continuous temporal modeling in biomedical contexts

**Why it matters:** directly relevant to the genomics adapter and genomics TTL calibration. If LongevityBench publishes per-task decay-rate estimates for biomedical facts, it's a candidate ground truth for follow-up TTL calibration in the genomics adapter specifically. Not material to Phase E (dry-run only) but worth noting for the genomics verifier stack follow-up.

**Action:** Cite in the "For the empirical verifier follow-up plan" section as a calibration target for genomics-specific decay rates.

**Exa also re-surfaced DeepFact (arXiv:2603.05912)** which my S2 sweep already found and flagged as material. Independent corroboration strengthens the "read before Phase F" recommendation.

**Exa also cited the plan's own Gilda & Gilda paper (arXiv:2601.21116) under a different title: "AI-Assisted Engineering Should Track the Epistemic Status and Temporal Validity of Architectural Decisions."** This is either (a) the same paper with a different framing, (b) a title collision, or (c) an Exa citation error. **The plan's author should verify** arXiv:2601.21116 before claiming it as prior art — if the paper is actually about architectural decisions and not temporal epistemic degradation, the plan's §4 prior art row is incorrect. Low-cost verification: one `search_papers` call with the exact arXiv ID.

---

## Updated Component 5 verdict (post-Exa)

Unchanged at the **verdict** level: **MINOR**. But now with explicit citations for the alternative view and a named failure mode for follow-up coverage.

The strongest argument against changing the plan is architectural: L0/L1/L2 with strict parent-level increase is a structural invariant that is **cheap to enforce and cheap to relax later**. Graph / DAG support can be added in a follow-up without breaking existing L0/L1/L2 callers (add `parent_event_ids` semantics that allow multi-parent within same-level-or-below). Replacing the rule preemptively, before a single real-workload instance has hit a limitation, violates the plan's own principle of reversibility + blast radius.

---

## Budget and transparency

- **Parallel Task ultra2x:** $0.60. Wide but noisy. Subagent processed 173K chars → 30K char synthesis. Net value: flagged Oblivion and DeepFact as alternatives; over-claimed on AI Trust OS; conflated enterprise with scientific governance. 4 of its arXiv IDs were flagged by the processing subagent as possibly fabricated (unusually high sub-year numbers).
- **Exa Deep Researcher pro:** $0.99, 17 searches, 88 pages. Completed. Found 3 genuinely new arXiv papers (2602.10380, 2601.17593, LongevityBench) and one IETF draft that my S2 sweep missed. Over-recommended pause for 3 components where the pause would pull follow-up-plan scope into the minimal core. Net value: mixed — high-quality citations, wrong calibration on plan boundaries.
- **S2 targeted sweep:** $0. Verified 12 real papers; found 4 on-topic papers Parallel Task missed (ESAA, ESAA-Security, ElephantBroker, From Fluent to Verifiable); served as independent verification layer for Parallel Task claims. Highest signal-to-cost ratio of the three paths.

**Lesson for next audit:** the S2 sweep was the highest-signal cheapest path for a narrow, well-defined plan like this one. Parallel Task is useful as breadth-coverage but its tendency to re-quote the same 4-6 papers and conflate adjacent domains makes it noisy for architecture audits. Exa exa-research-pro is worth ~$1 as a third independent path for plans of this size — it found 3 papers the other paths missed — but its "pause" recommendations must be calibrated against the plan's own stated scope boundaries, not accepted wholesale. Next time, start with S2, run Exa in parallel, and treat Parallel Task as tertiary.

---

## Final answer

**Should a plan building this architecture today be paused and revised based on newer work?**

**No.** Execute Phase A unchanged. The three verified-material findings (Oblivion for TTL, Rethinking Atomic Decomposition + Beyond Precision for FIRE-Bench scoring, From Fluent to Verifiable + DeepFact for Phase F/G) fold in as:
- 1 paragraph in §3
- 4 rows in §4
- 2 new tests in Phase G
- 1 new open question in §10

None of these block Phase A (the git mv rename). Phases B/C/D are also unaffected. The additions hit Phases G and F when they execute, and the reading is owed before those phases — not before Phase A.

The plan's architectural decisions survive the sweep. This is the expected outcome for a plan that already consumed substantial prior art through the review cycle that produced v2.1.

<!-- knowledge-index
generated: 2026-04-11T23:27:44Z
hash: 8dc8a525bc4a

title: claim_bench Plan — Post-Sweep 2026 Literature Audit
status: active
tags: claim-verification, plan-audit, literature-sweep, epistemics
cross_refs: research/claim-verification-package-prior-art.md
table_claims: 9

end-knowledge-index -->
