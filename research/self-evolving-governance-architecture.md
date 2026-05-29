---
title: Self-Evolving Governance Architecture
date: 2026-05-29
tier: Standard
question: Validate architecture choices for a self-evolving agent-governance system — subtract-loop (retire dead rules/hooks), learn-from-corrections loop, report/act separation, pluggable detector that becomes more semantic as models improve.
---

## Self-Evolving Governance Architecture — Research Memo

**Ground truth (this repo):** The meta repo governs a fleet of Claude Code/Codex agents via
markdown rules + deterministic/advisory hooks + a Constitution. Today it only ADDS governance,
never retires it, and under-uses the user's direct corrections. We are adding a *subtract* loop
and a *learn-from-corrections* loop, both under strict report/act separation. Design assumption:
**models get more capable over time → don't over-commit to brittle hardcoded checks.**

**Prior coverage (not re-researched):**
- `research/agent-self-modification.md` — DGM/SICA/ACE/DGM-H. Established: archive-exploration > hill-climbing; meta-level improvements transfer; reward-hacking risk in self-improvement.
- `research/autoagent-self-optimizing-agents.md` — AutoAgent: a *deployed* meta/task split with a `FIXED ADAPTER BOUNDARY` (edit surface above the line, frozen plumbing below). This IS a working report/act-adjacent separation precedent — built on here.
- `improvement-log.md` (2026-04-05) — ERL: distilled heuristics +7.8% vs raw trajectories −1.9% on Gaia2. Validated/extended below (Q-bonus).
- Constitution Principle 1 (EoG: instructions-only = 0% reliable; "architecture shifts the slope, instructions shift the intercept") and the repo's own 67%-FP semantic-classifier datum are the local priors these findings are weighed against.

---

### Source grades

| Source | ID | Grade | Note |
|--------|----|-------|------|
| Judge's Verdict (Cohen's κ benchmark, 54 models 1B–405B) | arXiv:2510.09738 / OpenReview jVyUlri4Rw | B+ | Peer-reviewed-track, large model sweep, current frontier (Sonnet-4.5 era). Core Q1 evidence. |
| Diagnosing LLM Judge Reliability (conformal sets, transitivity) | arXiv:2604.15302 | B | Single-bench (SummEval), but rigorous; per-instance uncertainty result is robust. |
| Context Over Content: Evaluation Faking in Judges | arXiv:2604.15224 | B | 18,240 judgments; leniency bias scales WITH capability, invisible to CoT. Important contrarian datum. |
| Frontiers: LLMs for abstract evaluation (GPT-5, Gemini-3-Pro, Sonnet-4.5) | frma.2026.1807672 | B− | Current frontier models named; pediatric-abstract domain, small. |
| TrustJudge (probabilistic judging) | OpenReview 4uPyOCeN6U | B | Mitigation method; shows inconsistency is fixable with aggregation, not just scale. |
| The Two Boundaries: Why Behavioral AI Governance Fails Structurally | arXiv:2604.27292 | B | Rice's-theorem formal argument; conceptual not empirical. Strong for Q1/Q2 limits. |
| Separating Judgment from Enforcement (procedural principle) | LessWrong/greaterwrong | C+ | Blog/alignment-forum; conceptual, names the pattern cleanly. Corroborated by 3 arXiv papers below. |
| Sovereign Agentic Loop (SAL) — decoupling principle, pre-execution enforcement | arXiv:2604.22136 | C+ | Preprint, conceptual framework. |
| GAAT/GAOP — telemetry-to-enforcement loop | arXiv:2604.05119 | C+ | Preprint; names the "observe-but-don't-act gap" failure mode. |
| Three-Pillar Model (assisted→collaborative→autonomous, self-driving analogy) | arXiv:2601.06223 | B− | Stanford Deliberative Democracy Lab; conceptual + work-streams, not an eval. |
| MI9 runtime governance / Springdrift / selective-autonomy enterprise | OpenReview TseVPnC26W / arXiv:2604.04660 / OpenReview EixlcNkhpA | C+/B− | Deployed-ish; tiered-autonomy mechanisms. |
| HAARF healthcare progressive-autonomy levels | medRxiv 2026.04.09 | C+ | Domain-specific (clinical), red-teamed. |

Caveat on frontier timeliness: the strongest Q1 evidence (Judge's Verdict, the two 2604 judge papers) is tested on Sonnet-4.5 / GPT-5 / Gemini-3-Pro era — current frontier, transfers. The conceptual papers (Two Boundaries, SAL) are scale-independent (computability/architecture) so they transfer regardless.

---

## Q1 — Deterministic vs LLM-semantic detection for rule drift / contradiction / dead-rule decay, and how the tradeoff shifts as models improve

**Finding (graded MEDIUM-HIGH): The user's pluggable "starts deterministic, becomes semantic as models improve" bet is SUPPORTED — but with one structural correction. Capability does not move a single global reliability dial; it moves it PER-CRITERION. Some governance judgments will become trustworthy early; others may never become reliable purely from scale.**

Three convergent results:

1. **Reliability is criterion-dependent, not model-size-dependent.** Judge's Verdict (54 models, 1B–405B) found *training strategy matters more than scale* — some small models hit "Tier 1" (human-like, Cohen's κ near the κ≈0.80 human–human ceiling) while larger models do not. The conformal-prediction paper independently found *"criterion matters more than judge"*: coherence/relevance judged reliably (narrow prediction sets), fluency/consistency unreliable (wide sets) — across all judges tested. **Implication for the detector:** don't ask "is the model good enough yet?" Ask "is THIS detection task one where models agree with humans?" Bucket the detector's jobs by criterion difficulty, not by a single capability threshold.

2. **Capability scaling does NOT uniformly improve reliability — and one important bias scales the WRONG way.** "Context Over Content" (18,240 judgments, incl. a 671B MoE) found an implicit **leniency bias under stakes-framing that is invisible to chain-of-thought inspection** (ERR_J = 0.000 — the reasoning trace never reveals it) and *persists across scale*. This is the direct counter-evidence to a naive "just wait for better models" bet: a governance judge asked to evaluate its own fleet's compliance has exactly the stakes-framing that triggers this. **A more capable judge can be more confidently lenient, not more correct.**

3. **There is a computability ceiling, not just a quality gap.** "The Two Boundaries" applies Rice's theorem: for a Turing-complete agent, "does this program's effects comply with the policy" is **undecidable in general**. No amount of model capability closes this — it's not a quality problem, it's a decidability problem. Behavioral governance (inspecting outputs/reasoning to judge compliance) is structurally leaky; the paper argues the fix is architectural (route effects through a governance boundary), not a smarter reviewer.

**Synthesis / recommendation for Q1:**
- **Keep the pluggable detector interface — the bet is right in shape.** But the migration axis is *criterion difficulty*, not *time*. Define detector jobs as (a) **decidable/syntactic** (rule references a hook that no longer exists; two rules name the same trigger with opposite actions; a rule's grep target returns zero matches in any session) → **stay deterministic forever**, these are cheaper AND more reliable than any judge and immune to leniency bias; vs (b) **semantic** (two rules are *conceptually* redundant; a rule is "no longer earning its keep"; a correction implies a *general* principle) → LLM-semantic, but gated.
- **Gate every semantic detection on per-instance uncertainty, not on model version.** The conformal-set-width result (r≈0.576 with actual judge–human disagreement) gives a concrete mechanism: have the detector emit a confidence/uncertainty signal (ensemble disagreement, conformal set width, or simple self-consistency across N samples) and route only narrow-set/high-agreement detections to the actor; wide-set detections become human-review items. This is the architectural enforcement that makes "becomes semantic as models improve" safe — the system *measures* whether the model is reliable on each instance rather than assuming it.
- **Cross-model adjudication for the leniency-bias class.** Because leniency is invisible to CoT and survives scale, mitigate it the only way the evidence supports: blind/stakes-neutral framing + a second model (the repo already does cross-model review). Do NOT trust a single self-judging pass for retire-decisions.
- **Re the repo's 67%-FP datum:** that was a hardcoded *classifier with a fixed rule* (NON_HUMAN_ONLY / CANDIDATE_GENE vetoes), not a frontier-judge-with-uncertainty. The right read is not "semantic judging is 67% FP" but "a brittle hardcoded semantic *predicate* was 67% FP" — which is an argument FOR the pluggable+uncertainty-gated approach, against fixed semantic rules.

---

## Q2 — Report/act (detector/enforcer) separation: established pattern? failure modes of coupling?

**Finding (graded MEDIUM, conceptual convergence across 4 independent sources + 1 deployed precedent): Decoupling detection from enforcement is an established and increasingly named pattern in 2026 agent-governance literature. The user's report/act split is well-supported. BUT there is a specific, named failure mode of OVER-decoupling that the design must address.**

- **The pattern is named and recurring.** "Separating Judgment from Enforcement" (a procedural principle: a *Scientist-AI* judgment layer determines whether an agent acted within mandate, using observable behavior only, while enforcement stays separate and bounded, triggered only by adjudicated conclusions). SAL (arXiv:2604.22136) formalizes the same as the **Decoupling Principle**: "reasoning yields *verifiable intent* rather than direct control of system state" — model outputs are *intent proposals* validated against real state/policy before any mutation. AutoAgent (prior coverage) is the deployed instance: the meta-agent proposes harness edits; git commit/revert is the separate, bounded enforcement; `results.tsv` is the adjudication ledger.
- **Why coupling fails (the argument FOR the user's split):** "The Two Boundaries" shows that when the actor IS the judge, you get the "theater" region (governance asserts control over capabilities that don't pass through it) and the ungoverned region — two of three regions are failure modes. The alignment-forum framing adds: a coupled arbiter's own decisions can *consolidate power / self-justify*, which is exactly the reward-hacking-in-self-improvement risk flagged in `agent-self-modification.md` (Claim 6). A detector that can also act has an incentive to find work for itself.
- **The COUNTERVAILING failure mode — the "observe-but-do-not-act gap" (GAAT/GAOP, arXiv:2604.05119):** pure detection-without-enforcement means violations are detected *after* damage; for fast or irreversible effects this is too late. **This does NOT apply to the user's subtract/learn loops** because retiring a dead rule or proposing a learned heuristic is *not a fast/irreversible runtime effect* — the latency between report and human-supervised act is acceptable and even desirable. It WOULD apply if the same architecture were reused for runtime safety enforcement (blocking a destructive op), where pre-execution coupling is correct. **So: separation is right for the governance-evolution loop; for true runtime guardrails (the existing block-hooks), keep enforcement coupled/inline.** Two different planes, two different couplings.
- **Composability/evolvability argument:** the separation gives you exactly the pluggability Q1 needs — the detector can swap from deterministic→semantic→ensemble without touching the actor, and the actor's apply-policy (auto vs human-gated) can change without touching detection. The interface between them should be a typed, auditable *report artifact* (proposed action + evidence + confidence), not a direct call. This is the same shape as AutoAgent's `results.tsv` ledger and the repo's existing improvement-log → triage → implement pipeline.

**Recommendation for Q2:** Adopt the report/act split as designed. Make the boundary a **persistent, append-only report artifact** (proposal + evidence + uncertainty + provenance), per the repo's append-only-for-institutional-knowledge principle. Keep two planes explicit: (1) **governance-evolution plane** = decoupled, human-supervised actor (subtract/learn loops); (2) **runtime-safety plane** = coupled inline enforcement (existing block-hooks for irreversible/cascading-waste categories). Don't let the elegant decoupling leak into the runtime plane where the observe-but-don't-act gap bites.

---

## Q3 — Decay/retirement of governance artifacts; the "dead or working?" identification problem

**Finding (graded MEDIUM): There is real prior art (lint-rule deprecation, feature-flag lifecycle, dead-code analysis), and it converges on one answer to the identification problem: you cannot decide "dead vs working" from violation-count alone — you need EXERCISE/COVERAGE evidence, i.e., whether the rule was ever *reachable and load-bearing*, not whether it fired.**

The core problem the user names ("a rule's success looks like the ABSENCE of violations — so is it dead or is it working?") is exactly the feature-flag stale-detection problem, and the industry tools answer it the same way:

- **Feature-flag lifecycle (staleflags, flagwatch, Harness, LaunchDarkly tech-debt guides):** A flag is dead when it has the **same value across all environments for a long time** — i.e., it no longer *discriminates*. The signal is not "no errors" but "no longer changes any decision." Translated to rules: **a rule is dead when removing it would change no agent decision** — when its trigger condition is never reachable in current workflows, or every path it would gate is already gated by something else.
- **Lint-rule deprecation ("Crafting Trustworthy Custom Linter Rules"):** custom rules are retired when they produce **only false positives or zero true positives over a window** — measured by tracking per-rule fire counts AND disposition (suppressed/overridden/acted-on). A rule that fires but is always suppressed is *worse than dead* (it's noise); a rule that never fires might be working OR unreachable.
- **Dead-code analysis analogue:** static reachability (can this rule's trigger ever be hit by current agent behavior?) + dynamic coverage (was it hit in the last N sessions?). staleflags explicitly *quantifies the dead code a flag leaves behind* — the analogue is quantifying the instruction-tokens a dead rule costs every session (the repo already measures always-loaded token budgets — `context-budget-principles.md`).

**Resolving "dead or working?" — the three-signal test (recommendation for Q3):** Classify a rule/hook on three independent signals, because no single one disambiguates:
1. **Reachability (static):** Does the trigger condition still exist? (Hook references a tool/path that exists; rule's grep target still matches *something* in the codebase; the workflow the rule governs is still run.) → **Deterministic.** If unreachable → dead, retire candidate. This alone catches the cheapest, highest-confidence retirements (e.g., a hook guarding a deleted pipeline).
2. **Fire + disposition (dynamic):** Did it fire in the last N sessions, and when it fired, was it *acted on or always suppressed/overridden*? The repo already logs every hook trigger (Constitution Principle 3: "Measure before enforcing"). Always-suppressed = noise (retire); never-fired-but-reachable = ambiguous → signal 3.
3. **Counterfactual load-bearing test (semantic, for the ambiguous middle):** For never-fired-but-reachable rules — the genuine "is it the dog that didn't bark?" case — use an LLM-semantic check: "if this rule were removed, would a competent agent plausibly make the mistake it prevents?" This is the criterion-(a)-vs-(b) split from Q1: it's a *semantic* judgment, so it must be uncertainty-gated and is a REPORT (proposed retirement), never an auto-act. A rule that prevents a rare-but-catastrophic error (e.g., the data-guard / append-only guards) is load-bearing precisely *because* it never fires — the counterfactual test, not the fire-count, protects it.

**Key design rule:** never retire on absence-of-violations alone (signal 2 in isolation) — that's how you delete the smoke detector because there's been no fire. Retire only when reachability is gone (signal 1) OR (low counterfactual cost AND low/always-suppressed fire-rate). Tag rules by *failure category* (cascading-waste / irreversible-state / epistemic / style — the repo's existing taxonomy): irreversible-state guards get the highest counterfactual-protection bar regardless of fire-count.

---

## Q4 — Auto-apply vs human-in-loop for reversible self-modifications; earned/tiered autonomy

**Finding (graded MEDIUM): Tiered/earned autonomy — loosening the apply-gate as a track record accumulates — is the consensus design across 2026 governance frameworks, and it aligns precisely with the Constitution's Generative Principle ("maximize declining supervision" while keeping error-correction). The evidence supports it BUT conditions it on two things the design must build in: (1) the gate must loosen on MEASURED track record, not elapsed time; (2) automation-bias and algorithm-aversion are the two failure modes to instrument against.**

- **Staged autonomy is the dominant pattern.** Stanford Three-Pillar (arXiv:2601.06223) argues explicitly for progressive validation *analogous to staged autonomous-driving levels* (assisted → collaborative → autonomous), NOT immediate full automation, with **risk-based gating**: high-risk actions always trigger human review; low-risk high-volume tasks graduate to autonomous. HAARF (clinical) and MI9 (runtime governance) independently codify the same "co-pilot → fully autonomous levels with authority boundaries + emergency override." The selective-autonomy enterprise deployment (OpenReview EixlcNkhpA) gives the concrete mechanism: **a critic/abstention policy executes only high-confidence steps automatically and defers uncertain ones** — the same uncertainty-gating as Q1.
- **The two failure modes to instrument (PRIME–INSPECT, MDPI 16/10/4825):** **automation bias** (over-reliance — human rubber-stamps once the gate loosens) and **algorithm aversion** (trust collapses after one error, gate slams shut permanently). Trust calibration must be a *design objective*, tied to oversight, not a byproduct. For this repo: a single bad auto-applied retirement could trigger aversion and freeze the whole loop; a too-fast loosening could trigger rubber-stamping. The mitigation is the same ledger the repo already keeps (git log as error-correction ledger, Constitution Principle 13) — autonomy should be earned per *action-class* with a measurable proxy.
- **Reversibility × blast-radius is already the right axis.** The Constitution's existing self-modification rule (autonomous if meta-only + easily reversible + one clear approach; propose-and-wait if shared/multiple-approaches/irreversible) is exactly the risk-based gating the literature prescribes. The new loops should reuse it verbatim.

**Recommendation for Q4 — earned, per-action-class, MEASURED autonomy:**
- **Tier the apply-gate by action class, gated on a measured track record, not time.** Concretely: an action class (e.g., "retire a hook whose referenced path no longer exists") graduates from human-gated → auto-apply only after K consecutive human-approvals with zero reversions (the repo's pre-registered test #1 — "zero reverts of meta-initiated shared changes in 14 days" — is the natural promotion criterion). This makes "declining supervision" a *resolution observable*, matching the Constitution.
- **Never auto-apply across the irreversibility line.** Deterministic-reachability retirements of *meta-only, reversible* artifacts are the first auto-apply candidates (highest confidence, lowest blast radius). Semantic retirements, anything touching the irreversible-state guards, and anything shared across 3+ projects stay human-gated permanently (Constitution hard limits) — these are the "high-risk actions always trigger review" class.
- **Instrument both failure modes.** Track approval-without-modification rate (automation-bias proxy: if humans approve 100% without ever editing the proposal, the gate is rubber-stamping — tighten or sample-audit) and post-error gate behavior (algorithm-aversion proxy: don't let one bad retirement permanently freeze a class — demote it one tier, don't kill it).

---

## Bonus — Validate/extend the ERL finding (distilled heuristics > raw trajectories)

The ERL result (distilled heuristics +7.8% vs raw trajectories −1.9%, Gaia2) is **corroborated and extended** by the broader self-improvement literature already in the corpus:
- ACE (arXiv:2510.04618, in `agent-self-modification.md`) names *why* raw trajectories underperform: **context collapse** and **brevity bias** — feeding raw experience back degrades the playbook. Distillation is the mitigation. So ERL's "distilled > raw" is the empirical face of ACE's mechanism. **Extends the finding: distillation isn't just better, it's the defense against the specific degradation mode that makes raw-trajectory memory negative-value.**
- ERL's secondary result (failure-derived heuristics best for *search* +14.3%; success-derived best for *execution* +9.0%) maps directly onto the user's two new loops: the **learn-from-corrections loop is failure-derived** (a correction = a failure signal) and should be expected to be the higher-leverage of the two, consistent with ERL. The **subtract loop is closer to success-derived/structural pruning.**
- **Design implication:** the learn-from-corrections loop should distill each correction into a *general heuristic* (the report artifact), NOT store the raw correction trajectory. This is also what the ERL+ACE evidence says is the difference between +7.8% and −1.9%. The repo's improvement-log (structured distilled findings, not raw transcripts) is already the right shape — the new loop should write into that same distilled form. Caveat: ERL is a single-benchmark (Gaia2) workshop result; treat the *direction* as well-supported, the *magnitudes* as indicative.

---

## Consolidated recommendations (per question)

| Q | Decision | Confidence |
|---|----------|------------|
| Q1 | Keep the pluggable detector. Migrate by **criterion-difficulty**, not time. Decidable/syntactic checks stay deterministic forever (cheaper + immune to leniency bias). Semantic checks are **uncertainty-gated** (conformal width / ensemble disagreement / self-consistency) + cross-model adjudicated. The bet is right in shape; the axis is criterion, not calendar. | MEDIUM-HIGH |
| Q2 | Adopt report/act separation for the **governance-evolution plane** (decoupled, append-only report artifact as the boundary). Keep enforcement **coupled/inline** for the **runtime-safety plane** (existing block-hooks) — the "observe-but-don't-act gap" only bites fast/irreversible effects, which the subtract/learn loops are not. | MEDIUM |
| Q3 | Three-signal dead-rule test: **reachability (static, deterministic)** → **fire+disposition (dynamic)** → **counterfactual load-bearing (semantic, report-only)**. Never retire on absence-of-violations alone. Irreversible-state guards get max counterfactual protection regardless of fire-count. | MEDIUM |
| Q4 | Earned, **per-action-class, measured** autonomy. Graduate gate after K approvals + zero reversions (reuse pre-registered test #1). Auto-apply only meta-only + reversible + deterministic-reachability retirements first. Instrument automation-bias (approval-without-edit rate) and algorithm-aversion (post-error gate behavior). | MEDIUM |
| ERL | Confirmed + extended: distill corrections into general heuristics (don't store raw trajectories — that's the −1.9% path via context collapse). Learn-from-corrections (failure-derived) likely higher-leverage than subtract (per ERL's +14.3% search vs +9.0% execution split). | MEDIUM |

## One cross-cutting architectural through-line
All four answers reduce to the same primitive: **emit uncertainty/evidence and route on it, rather than assuming a global capability threshold.** Q1 (route semantic detections on conformal width), Q3 (route ambiguous rules through the counterfactual test), Q4 (auto-apply only high-confidence/low-blast-radius classes) are the same mechanism applied at detection, classification, and action. Build that signal once (a `confidence` + `evidence` + `blast_radius` field on the report artifact) and all three loops consume it. This is the architectural enforcement that lets the system safely get more autonomous as models improve — it *measures* readiness instead of *assuming* it, which is the only posture the leniency-bias-scales-with-capability evidence (Q1) permits.

<!-- knowledge-index
generated: 2026-05-29T11:33:56Z
hash: c35657f8a854

index:title: Self-Evolving Governance Architecture
cross_refs: research/agent-self-modification.md, research/autoagent-self-optimizing-agents.md

end-knowledge-index -->
