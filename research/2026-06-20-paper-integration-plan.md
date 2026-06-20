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
  provenance/control-flow link tables, then diagnose against the IR, not raw prose. Reinforced
  (NARROW, post-refute) by ACDL (2605.01920) — as a `context_shape` SUBVIEW only, not full IR; and
  pi-cwl (2606.11213) — dependency edges are INFERRED forensic hints, NOT causal ground truth.
  [PROJECTMEM 2606.12329 relocated to F2/F3; MiniMax 2605.26494 DROPPED — model paper, not trace-IR.]
- **Why it works:** diagnosis on typed steps lets you group by *diagnosed flaw* instead of anecdote,
  and makes "did the intended mechanism fire?" a query, not a re-read.
- **Measured:** HTIR's 15.2–50.0% is a FULL repair loop; the typed-IR ablation shows trace-grounded
  diagnosis contributes but does NOT isolate the IR alone (refute). Preconditions: rich tool/env logs,
  recurring failures, held-out tasks, recomputable target-flaw metrics. Screen-only.
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
- **Confidence:** MED post-refute (EvoTrainer downgraded HIGH→pattern-extraction: papers support the
  gate as analogy from versioned experiments / replayable objective evals, not as proof every local
  rule/hook edit needs it). **Build it, but it only bites once F1/L2 supply replayable artifacts +
  objective (or explicitly-labeled proxy) outcomes.** **Autonomy: autonomous.**

---

### LAYER (cheap once the foundation exists)

**L1 — act-drain anti-accretion** — replace monotonic "count corrections → append rule" with:
ADD/MODIFY/**DELETE** lifecycle, but (refute) each candidate needs **old-vs-new replay / trace-mechanism
evidence** before promotion, not lifecycle verbs alone (ReSkill 2606.01619). A typed skill/rule graph
(SkillDAG 2606.03056) — **for retrieval/interface structure ONLY; `supersedes`/`duplicate_of` and
"typed edges reduce accretion" are NOT demonstrated (REFUTED)** — source lifecycle semantics from the
replay metric, not the graph. StreamMemBench (2606.14571) → a *diagnostic taxonomy* (label where a
correction's fix belongs: retrieval / prompt-surfacing / hook / deletion), not auto-enforcement.
Trace-derived skill candidates (Socratic-SWE 2606.07412) must carry trace-IDs + a verifier + held-out
replay + a **retirement condition**, else "trace-derived" is just another accretive rule-gen path.
**Confidence: MED post-refute. Autonomy: autonomous** (this IS the gov-shrink telos — gated by F3).

**L2 — /eval local harness-eval lanes** — build LOCAL slices (not adopt benchmarks): env-grounded
final-state verifier, held-out chronological traces, **token cost first-class**, model×harness grid.
Templates from Terminal-Bench (2601.11868), WildClawBench (2605.10912, grades Claude Code/Codex/Hermes
harnesses — direct prior-art), WeaveBench (2606.09426, trajectory-aware per-clause-evidence judging +
9 cheating-pattern detectors), ComplexMCP (2605.10787, state-diff + injected-failure recovery),
SentinelBench (2606.05342, wait-vs-poll + no-op tasks), NRT-Bench (2606.20408, objective-sim >
LLM-judge), ALE (2606.05405, load/start/evaluate task-spec + failure taxonomy). **Confidence: VERY STRONG. Autonomy: bounded** (eval design is partial-verifier).

**L3 — over-ask ask-gate, eval-only first** — uncertainty decomposition (2606.19559): split
action-confidence `c_t` from request-uncertainty `u_t`. **Do NOT ship `u_t≥θ` threshold-routing as the
mechanism (refute): the paper itself finds no single threshold dominates, prompt-uncertainty competes
with task budget, and it causes capability dilution.** Use `u_t` as an **offline label/feature in an
eval lane**: replay reconstructed underspecified scenarios, grade act-vs-ask by tool telemetry,
**locally calibrate any threshold on agentlogs, and compare against a cheap-probe-first baseline.**
[2606.13603 DROPPED from L3 → separate "post-commitment over-deliberation tail" eval idea.]
**Confidence: MED post-refute. Autonomy: operator-go.**

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

## Refutation status — DONE (6 high-effort codex skeptics, refute/*.md)

**Result: nothing survived as clean HOLDS — all NARROW, with 3 citations REFUTED and dropped.**
The unifying finding: every mechanism is *directionally* faithful, but each paper's EVIDENCE is
narrower than this plan first implied — **none demonstrates its bolt-on reduces OUR specific failure
(accretion / over-ask).** This tightens rather than kills the plan: it makes **F3 (predict-then-falsify)
+ L2 (local eval) the mandatory gate** — every other bolt-on is a *design pattern that must be locally
validated on our own agentlogs before promotion*, not borrowed evidence.

| Claim | Verdict | Correction applied |
|---|---|---|
| **F1** typed trace-IR | NARROW (×4) + **REFUTED ×1** | HTIR's gains are a *full repair loop*, not IR-isolated; ACDL→`context_shape` subview only; pi-CWL edges = inferred hints, not ground truth; PROJECTMEM moved to F2/F3; **MiniMax 2605.26494 DROPPED** (model paper, not trace-IR). |
| **F2** memory raw-links | NARROW (×4) | Reword: not "agents rely more on raw" but "condensed needs raw-link **auditability + replay tests**, condensed is often not causally used"; Engram fields → factual/current-status only; MemRefine → active-**view** compression, measure duplicate retrieval first; StreamMemBench → *evaluate* lifecycle from traces, don't presume status. |
| **F3** predict-then-falsify | NARROW | **EvoTrainer downgraded HIGH→pattern-extraction.** Gate is a good local design but the papers support it only as analogy from versioned experiments / replayable objective evals — implement **only after F1/L2 provide replayable artifacts + objective (or explicitly-labeled proxy) outcomes.** |
| **L1** anti-accretion | NARROW (×3) + **REFUTED ×1** | **SkillDAG 2606.03056: `supersedes`/`duplicate_of` claim REMOVED** — typed edges are for retrieval/interface, NOT demonstrated to reduce accretion; ReSkill → tested candidate versions w/ reject/prune + old-vs-new replay required; StreamMemBench → diagnostic taxonomy only; Socratic-SWE → require trace-IDs+verifier+held-out+retirement-condition or it's just another accretive rule-gen path. |
| **L2** eval lanes | NARROW (×5) | WildClawBench's model×harness claim needs **equalized env** (perms/tools/secrets/versions/timeouts) for fair local rankings + doesn't cover Cursor; SentinelBench = narrow wait-vs-poll only, don't over-generalize. |
| **L3** ask-gate | NARROW + **REFUTED ×1** | **Threshold-routing `u_t≥θ` removed as the mechanism** — paper itself: no single threshold dominates, prompt-uncertainty competes with task budget, capability dilution. Use request-uncertainty as an **offline label/feature in an eval lane**, locally calibrate, compare vs **cheap-probe-first baseline**. **2606.13603 DROPPED** from L3 → separate "over-deliberation tail" eval idea. |

**Net:** structure (3 foundations + 5 layers) holds; 3 citations dropped; F3 demoted from HIGH to
the gate-that-must-be-built-first-but-proven-locally; the through-line is now explicit — **import
mechanisms as patterns, prove each on our traces via F3/L2, never cite paper numbers as expected lift.**

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
