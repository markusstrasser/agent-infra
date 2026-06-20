**Overall Verdict: NARROW**

F2 is directionally right: condensed MEMORY should not be trusted as free-floating prose, and raw provenance links are a good substrate. But the plan overclaims the paper support. The cited mechanisms mostly support **auditable, evaluated, retrievable raw-grounded memory**, not merely adding `source_session_id` / `trace_span_ids` fields plus a drift warning.

**2601.22436 — NARROW**

Strongest objection: The paper does show a raw-vs-condensed faithfulness asymmetry in many settings, but F2 overreads it into “raw links make condensed lessons a reliable improvement substrate.” In the paper, “raw experience” means concrete trajectories actually present to the agent at inference and causally perturbed; F2 proposes mostly provenance pointers, which are audit handles, not necessarily behaviorally used context. The paper also explicitly has task regimes where both raw and condensed experience have limited causal influence because pretrained priors dominate.

Correction: Reword the plan from “agents rely more faithfully on raw” as the reason to add links to: “condensed lessons require raw-link auditability and replay tests because condensed content is often not causally used.” Add an eval: condensed-only vs condensed+retrieved raw span vs corrupted/irrelevant raw span, measuring behavior change in local Claude/Codex/Cursor traces.

**2606.09900 — NARROW**

Strongest objection: Engram’s mechanism is not just provenance fields or bi-temporal frontmatter. The load-bearing system is lossless raw episodes, extracted atomic facts, non-destructive invalidation, hybrid retrieval with raw chunks, as-of filtering, abstention, and a same-answerer full-context baseline; F2 only captures the metadata shell. Also, Engram is strongest for factual/temporal recall, while many MEMORY lessons are normative governance rules or user-taste/process preferences where `valid_at/invalid_at` can be falsely precise.

Correction: Limit Engram-derived fields to factual/current-status/current-rule claims unless a rule-specific validity condition is explicit. Add a lean hybrid retrieval view over `agentlogs.db` that returns both structured memory facts and raw transcript spans, and require an internal full-history vs lean-retrieval eval before claiming Engram’s mechanism transferred.

**2606.13177 — NARROW**

Strongest objection: MEMREFINE supports pairwise compression of an already-built memory store toward a target budget using DELETE/MERGE/PRESERVE decisions, but the paper’s operations persistently edit the store; “never touching the append-only store, only retrieval view” is a safety adaptation, not the paper’s demonstrated mechanism. The evidence is also conversational-memory-heavy, not governance-rule or agent-harness memory, and it assumes real redundancy/budget pressure.

Correction: State this as “MEMREFINE-inspired active-view compression,” not as direct adoption. First measure duplicate/noisy MEMORY retrieval on historical correction queries; then use similarity to propose candidate pairs and an LLM judge to label `DROP_FROM_ACTIVE_VIEW`, `MERGE_IN_ACTIVE_VIEW`, or `PRESERVE`, with raw provenance retained and recall of high-value lessons tested.

**2606.14571 — NARROW**

Strongest objection: StreamMemBench is an evaluation lifecycle, not a schema recipe. It supports tracing an evidence anchor through storage, initial use, feedback incorporation, and follow-up reuse; F2’s “lifecycle status” metadata is only faithful if backed by those behavioral observations, not if filled in as a static memory field. It also requires paired future tasks, exposed memory deltas, and judge/simulator reliability, which a single-operator local harness does not get for free.

Correction: Move StreamMemBench support from “add lifecycle status to MEMORY” to “evaluate lifecycle status from traces.” For each important MEMORY lesson, record raw origin plus later reuse evidence: stored, initially applied, corrected if missed, and reused later. Treat unknown lifecycle status as unknown, not presumed active.

**Bottom Line**

F2 should survive, but only as: **condensed MEMORY entries become auditable pointers into raw traces plus evaluated active-view retrieval**, not as “raw links solve condensed-memory faithfulness.” The strongest correction is to make raw-link provenance necessary but insufficient: every promoted lesson needs either a raw replay/audit path or a lifecycle/eval record showing it was actually used.