---
title: "Integration Plan — 38-paper deep-read → what to build, grounded in mechanism"
date: 2026-06-20
status: DRAFT (pre-adversarial-refute; extractions clobbered by peer git-clean, regenerable via committed pipeline)
method: 38 arxiv papers downloaded (0/38 hallucinated, verified), codex gpt-5.5 read each in FULL (read-only sandbox, $0), structured extraction (mechanism/why/preconditions/measured/limits/integration). This plan synthesizes the 38 `integration-into-our-system` verdicts.
extractions: research/papers-2026-06-20/extractions/*.md (regenerate via run_extractions.sh — see _status.tsv for the 38 verified IDs)
inputs: research/2026-06-20-agent-landscape-fresh-sweep.md (the sweep that surfaced the IDs)
---

# Integration Plan — grounded in 38 full-paper reads

## Meta-finding (the load-bearing result)

**38 papers from different angles converge on the SAME small set of bolt-ons to OUR exact
surfaces.** This is not 38 ideas; it is ~8 ideas independently re-derived 38 times. When that many
papers, asked to map onto our system cold, all point at "add a typed trace IR / link condensed
memory to raw / gate edits by predicted-mechanism-fired," the signal dominates any single paper's
asserted numbers. **Nothing here is a dependency to adopt** — every extraction independently
concluded "pattern-extract, our primer rejects hosted runtimes."

## Convergence count (how many of 38 independently named each target)

| Bolt-on | Papers backing it (independent) | Strength |
|---|---|---|
| **predict-then-falsify gate** (pre-register mechanism + trace signature; accept only if it fired) | ~30 | OVERWHELMING |
| **session-trace → typed IR** (normalize transcript into typed steps before diagnosis) | ~30 | OVERWHELMING |
| **MEMORY condensed→raw first-class provenance links** | ~32 | OVERWHELMING |
| **act-drain anti-accretion** (ADD/MODIFY/DELETE lifecycle, not monotonic append) | ~28 | VERY STRONG |
| **/eval local harness-eval lanes** (env-grounded verifier, held-out, token-cost first-class) | ~25 | VERY STRONG |
| **skills/rules/hooks → typed graph** (depends/conflicts/supersedes/duplicate edges) | ~18 | STRONG |
| **ToolSearch → capability-envelope + intention graph** | ~10 | MODERATE |
| **over-ask ask-gate** (uncertainty decomposition) + **Workflow** primitives (wait_for, plan-contract) | ~8 | MODERATE |

## The structure: 3 foundations everything else assumes, then 5 layers

The 30+-paper items aren't independent — **F1/F2/F3 are a substrate the rest require.** You can't run
anti-accretion credit-assignment, a harness-eval, or a faithfulness check without (a) a typed trace
to diagnose, (b) condensed→raw links to audit, and (c) a gate that accepts only mechanism-confirmed
edits. Build the foundation first; the layers become cheap.

---

### FOUNDATION

**F1 — session-trace typed IR** (the substrate)
- **Mechanism (HTIR, arXiv:2606.06324):** compile raw cross-vendor transcripts into a typed
  `TraceStep(id, vendor, role, request_ref, response_ref, status, effect_kind, resource_ref)` +
  provenance/control-flow link tables, then diagnose against the IR, not raw prose. Reinforced by
  ACDL (2605.01920, context-shape DSL), pi-cwl (2606.11213, typed expl/act episodes + dependency
  edges), PROJECTMEM (2606.12329, event types issue/attempt_failed/fix_worked), MiniMax
  (2605.26494, (state,action,observation,artifact,reward) episodes).
- **Why it works:** diagnosis on typed steps lets you group by *diagnosed flaw* instead of anecdote,
  and makes "did the intended mechanism fire?" a query, not a re-read.
- **Measured:** HTIR reports 15.2–50.0% held-out gains (paper, not reproduced — screen-only).
- **Our bolt-on:** a derived view over `agentlogs.db` (NOT a new DB) — `session-trace` emits typed
  steps + effect/provenance edges. Label inferred edges as inferred (pi-cwl caveat).
- **Confidence:** MED (single paper for the IR shape; the *pattern* is 5-way triangulated). **Autonomy: autonomous** (agent-infra-local).

**F2 — MEMORY/improvement-log condensed→raw provenance links** (the substrate)
- **Mechanism:** every condensed lesson carries `source_session_id` + `trace_span_ids` + lifecycle
  status. Engram (2606.09900) adds bi-temporal `valid_at/invalid_at/supersedes` (invalidate, never
  delete — matches our append-only rule). MemRefine (2606.13177): compaction proposes
  DELETE_FROM_VIEW/MERGE/PRESERVE over a *retrieval view*, never touching the append-only store.
- **Why it works (the theory — arXiv:2601.22436, "Not Always Faithful Self-Evolvers"):** controlled
  interventions show agents **misuse condensed experience and rely more faithfully on raw**. A
  condensed lesson without a raw link is a weak, possibly-ignored improvement substrate.
- **Measured:** Engram 83.6 vs 73.2 on LongMemEvalS, ~8× fewer tokens (paper — screen-only). 2601.22436
  is a demonstrated critique across frameworks (rates model-sensitive).
- **Our bolt-on:** add the provenance fields to MEMORY frontmatter + improvement-log entries; a drift
  hook warns when a lesson claiming a rule doesn't link the live rule path (Engram drift-check).
- **Confidence:** MED-HIGH (32-way convergence + a demonstrated theory paper). **Autonomy: autonomous.**

**F3 — predict-then-falsify gate** (the acceptance discipline; ALREADY PLANNED — papers validate building it FIRST)
- **Mechanism (EvoTrainer, arXiv:2606.03108, the sharpest):** an intervention counts only if
  diagnostics + backtests support the *mechanism*; before accepting a harness/rule/hook edit, record
  {predicted failure-class reduced, expected trace-observable, exact agentlogs query, negative
  control, rollback criterion}; accept only if the trace shows the mechanism fired — not if aggregate
  score merely improved. ~30 papers independently specify this exact gate.
- **Why it works:** directly attacks our measured #1 risk (accretion/"policy maze") — a rule that
  doesn't move its pre-registered trace signal never lands. Also the defense against reward-hacking /
  self-preference (RHO 2606.05922 from the sweep; NRT-Bench 2606.20408).
- **Our bolt-on:** a "mechanism record" required on every act-drain rule/hook proposal; gate checks
  the trace post-change. Composes with F1 (the trace to check) + F2 (the provenance to audit).
- **Confidence:** HIGH (30-way + it's our own pre-existing plan). **Autonomy: autonomous.**

---

### LAYER (cheap once the foundation exists)

**L1 — act-drain anti-accretion** — replace monotonic "count corrections → append rule" with:
ADD/MODIFY/**DELETE** lifecycle (ReSkill 2606.01619), a typed skill/rule graph with
`depends_on/conflicts_with/supersedes/duplicate_of` edges (SkillDAG 2606.03056), recurring-**flaw**
records grouping rules by diagnosed flaw not anecdote (HTIR), and lifecycle-failure labels — *where
did a rule FAIL* before adding another (StreamMemBench 2606.14571). Trace-derived skill candidates
with a verifier (Socratic-SWE 2606.07412). **Confidence: STRONG. Autonomy: autonomous** (this IS the gov-shrink telos).

**L2 — /eval local harness-eval lanes** — build LOCAL slices (not adopt benchmarks): env-grounded
final-state verifier, held-out chronological traces, **token cost first-class**, model×harness grid.
Templates from Terminal-Bench (2601.11868), WildClawBench (2605.10912, grades Claude Code/Codex/Hermes
harnesses — direct prior-art), WeaveBench (2606.09426, trajectory-aware per-clause-evidence judging +
9 cheating-pattern detectors), ComplexMCP (2605.10787, state-diff + injected-failure recovery),
SentinelBench (2606.05342, wait-vs-poll + no-op tasks), NRT-Bench (2606.20408, objective-sim >
LLM-judge), ALE (2606.05405, load/start/evaluate task-spec + failure taxonomy). **Confidence: VERY STRONG. Autonomy: bounded** (eval design is partial-verifier).

**L3 — over-ask ask-gate as a behavioral eval first** — uncertainty decomposition (2606.19559):
split action-confidence `c_t` from request-uncertainty `u_t`; route to clarify only when `u_t≥θ`.
Targets our measured `over_caution=63`. Build as a behavioral testground (replay reconstructed
underspecified scenarios, grade act-vs-ask by tool telemetry) BEFORE any live hook. Reinforced by
Beyond-Commitment-Boundary (2606.13603, epiphenomenal-tail = over-deliberation) + RePro (2606.14302,
retrospective progress). **Confidence: MED-HIGH. Autonomy: operator-go** (new harness, behavior-shaping).

**L4 — ToolSearch capability-envelope + intention graph** (optional/later) — return typed relations
+ required-params/side-effects/verifier envelope (SkillDAG, CAHL 2606.09371), intention-node rerank
over BM25 (SING 2606.16591), regime-aware loading (A2H 2606.01770), composite read-only tool batch
for deterministic chains (HyperTool 2606.13663, write/mutate blocked). **Confidence: MODERATE. Autonomy: autonomous (small).**

**L5 — Workflow primitives** (optional/later) — `wait_for(condition, timeout)` deterministic-first
(SentinelBench), plan-contract artifact for fan-out (CAHL, OrchRM 2606.13598), portfolio/router over
EXISTING recipes — no per-query generation (FlowBank 2606.11290). **Confidence: MODERATE. Autonomy: autonomous (small).**

## Recommended sequence
1. **F1 + F2 + F3** (the substrate; F3 is already planned, F1/F2 are derived views + frontmatter — all autonomous).
2. **L1** anti-accretion on act-drain (the telos; highest-convergence actionable layer).
3. **L2** one eval lane (start with the over-ask behavioral lane so it feeds L3) + **L3** ask-gate.
4. L4/L5 only if a measured need appears (don't pre-build — primer rule).

## NOT building (explicit)
- Any framework/runtime/DB as a dependency (all 38 extractions agree; primer rule).
- Reward-model / learned scorer in front of ToolSearch (OrchRM caveat: null-baseline SQL/rubric likely captures most benefit).
- Self-preference / self-judge fitness (RHO/Exploration-Hacking; collides with standing DGM caution).
- Importing any paper's numbers as expected effect — all harness-confounded, screen-only.

## Refutation status
⏳ PENDING — adversarial codex pass (refute.sh) re-reads each foundation/layer claim against its
cited paper to refute "this integration faithfully uses the mechanism." Only refutation-survivors
stay. Blocked by the peer git-clean incident (see Provenance note); rerun after isolation.

## Honest caveats
- Plan rests on gpt-5.5-low scout + gpt-5.5-medium full-read extractions — I did NOT independently
  re-read all 38 PDFs. The convergence is robust to any single extraction error; specific NUMBERS are not.
- All measured % are paper/vendor-reported and harness-confounded → **screen-only**, never cite as expected lift.
- F1's IR shape is single-sourced (HTIR); the *need* is 30-way. Build the minimal IR, not HTIR's full schema.

## Provenance note (2026-06-20 peer-collision incident)
The 38 extraction files + this plan were initially left UNTRACKED and a concurrent peer session ran
`git clean -fdx`, deleting all untracked + gitignored work (extractions, PDFs, txt) and committing a
tree (a4d38fa) without the papers dir. This plan was reconstructed from context and committed
immediately. The extractions are regenerable: `research/papers-2026-06-20/run_extractions.sh` over the
38 IDs in `_status.tsv`. **Lesson: commit generated provenance immediately in a shared checkout, or
worktree-isolate — gitignore does NOT protect against `git clean -fdx`.**
