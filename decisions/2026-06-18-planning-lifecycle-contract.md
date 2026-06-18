---
id: 2026-06-18-planning-lifecycle-contract
concept: planning-lifecycle-contract
repo: agent-infra
decision_date: 2026-06-18
recorded_date: 2026-06-18
provenance: contemporaneous
status: proposed
initial_leaning: "Adopt the alignment report's ~12 planning contracts + new requirements/interview skills. REVERSED by audit: ~7/10 diagnosed classes already have rules (instruction-following failures) or are already shipped (D3 orchestrator scope-guard, D10 isolation); adding prose contracts re-instructs already-instructed classes (Constitution P1, ~0% reliable). Converged to: one typed plan contract elicited at kickoff, consumed by gates that already exist."
relations:
  - type: branches_from
    target: 2026-06-07-verifier-conditional-autonomy
  - type: relates_to
    target: 2026-06-18-unified-loop-infra-scaffold-cookbook
  - type: relates_to
    target: 2026-06-16-rsi-unified-control-surface
  - type: relates_to
    target: 2026-06-16-feature-work-loop-binding-measurement-first
  - type: relates_to
    target: 2026-06-16-shared-checkout-isolation-by-default
---

# 2026-06-18: Planning failures are under-elicited inputs, not under-instructed execution — fix at the kickoff front-end with a typed plan contract, reuse existing gates

## Context

Two companion research docs (`research/2026-06-18-planning-process-deep-diagnosis.md`,
`…-alignment-report.md`) traced 10 cross-repo planning failure classes (D1–D10) across hutter,
genomics, phenome. The alignment report recommended ~12 new planning contracts + new skills
(closure-packet, scope-triple, requirements-slice, interview-kickoff, telos_check, handoff
template, …). Operator steer (2026-06-18): "think the full loops" and "it's ok to demand more
from me — improve the interview/requirements skill, the long-term vision, user stories."

This ADR is the `/decide` arc over that solution space. The arc began with an **audit** of the
diagnosis, because building 12 contracts on an un-audited diagnosis would be building on sand.

## The real axis (Phase 0)

First framing (alignment report's): "what planning contracts/sections to add." The audit
**reverses it**. The real axis is:

> **For each diagnosed failure, is the gap a MISSING rule (→ build architecture) or an
> UNFOLLOWED rule (→ another rule is theater; the only levers are a force-function or
> accept-as-semantic)? And where does the failure ROOT in the planning loop?**

Audited answer: ~7/10 classes already have a rule or are already fixed in code. The
**genuinely-missing-input** failures — D4 proliferation (no exit defined), D3 budget (scope
unstated), D2-scope (closure inputs) — **root at the under-built human-input front-end** (the
agent acting on inputs it was never given). So the leverage there is *eliciting the few
underivable inputs up front* — exactly the operator's steer.

**Narrowed by the cross-model panel (see Panel outcome below):** D1 freeze is NOT a missing-input
failure — the hutter retro shows the agent *knew* Markus's decision was real and still froze the
independent measurement (a self-Q branching error under pressure, DESPITE the `see-it-through`
rule). A kickoff `authority_split` field would not have prevented it. D1/D5/D6/D7 are in-the-moment
judgment / already-instructed → **accept + detect** (they already surface: `over_caution=56`), NOT
front-end. The front-end claim is scoped to the missing-input classes only.

### Hidden assumptions made explicit
1. "The diagnosis is ground truth." **Partly false** — G1 ("100 not run yet?!", the D2 headline
   exemplar) is **unverified** (absent from genomics improvement-log AND agentlogs FTS); genomics
   plan count is 73 not the report's 79; exit-signal absence is ~65% not universal; X2
   (supervision-KPI blindness) is **already fixed** (`supervision_taxonomy.py` rewrite). The
   classes are real; the novelty and magnitude are overstated.
2. "More planning contracts → fewer planning failures." **False for already-instructed classes**
   (Constitution P1: instructions ~0% reliable on what matters; SlopCodeBench: instructions shift
   the intercept, not the slope).
3. "There is no existing loop infra to build into." **False** — `loop.yaml` manifest + 4 autonomy
   regimes (`unified-loop-infra-scaffold-cookbook`), the `pulse` closure loop reusing
   reflect/fm/supervision-kpi sensors (`rsi-unified-control-surface`), `plan-review-gate`, and the
   measure-first `feature-work-loop-binding` ADR all already exist.

## Audit verdict (governance gate applied per class)

Gate = recurs 2+ ∧ not-covered-by-existing-rule ∧ (checkable predicate OR architectural change).

| D | Verified? | Covered/fixed? | Verdict |
|---|---|---|---|
| D1 freeze | yes (retro+META-AUDIT row 60) | `see-it-through` + detected (`blindspot over_caution=56`) | accept + detect |
| D2 closure | G1 **unverified**; G4 documented | partial (`/critique close`,`/rsi`) | 1 checkable slice (`verifier_ran`) |
| D3 unscoped | yes | **fixed in code** (`pipeline_orchestrator.py:163`) | done |
| D4 exit | yes (~65%) | counter-pattern exists, unenforced | 1 checkable slice (`exit_signal`) |
| D5 phase-artifacts | yes | Constitution P6 + `/decide` | accept |
| D6 inventory-filename | yes | hook exists (`pretool-inventory-dispatch.py`) | accept residual |
| D7 assert-no-probe | yes | `probe-primitive-first`,`checkable-claims-carry-probes` | accept |
| D8 plan↔critique | 1 instance | partial (`plan-review-gate` post-step) | accept/fold |
| D9 MCP bypass | yes (260×) | **no enforcement** | 1 checkable slice (routing-warn) |
| D10 clobber | yes | **decided+shipped** (`shared-checkout-isolation`) | done |

## Alternatives considered

1. **Alignment-report kit — ~12 contracts + `requirements-slice` skill + interview-kickoff.**
   Rejected: re-instructs already-instructed classes (D1/D5/D6/D7); this repo "is NOT a place to
   write more rules about rules"; maintenance surface with no slope change.
2. **Detection-loop only — add no gates; wire each D-class into `pulse`/`blindspot`/observe and
   let the RSI loop promote.** Partly adopted (the Correct stage), but insufficient alone: it
   leaves the *root* (missing up-front inputs) unaddressed; prevention at the front-end is cheaper
   than detecting the same freeze post-hoc every time.
3. **Force-functions only — hooks for the 3 checkable slices, nothing on the front-end.** Rejected
   as the whole answer: ignores the operator steer and the audit's root-cause finding (front-end
   is where the expensive ones start).
4. **New planning platform / loop-core for planning.** Rejected: build-then-undo graveyard
   (outer-loop killed zero-caller; scored-gate built twice never ran; orchestrator eradicated).
5. **State-externalization: typed plan contract elicited at kickoff, consumed by existing gates
   (CHOSEN).** Externalizes the recoverable bookkeeping (the underivable inputs) into a queryable
   contract block; the policy keeps only the semantic decision. Reuses `loop.yaml` (manifest-as-
   interface), `pulse` (sensor reuse), `feature-work-loop-binding` (measure-first, harness-state).
6. **Regime-routed contract** is a property OF #5, not a rival: required fields differ by
   clean/partial/principal verifier regime (Constitution's 3; the cookbook's `coverage-poor` is a
   discovery-loop subtype, kept out of the planning vocabulary to avoid drift).

## Counterevidence sought

What would falsify the chosen mechanism (#5)? The strongest kill: **the contract becomes
checkpoint-bloat 2.0 / "another tracker"** — phenome's own foundation-exit plan warns "must not
become another tracker," and this repo has a tracker graveyard (finding-triage DB, scored-gate).
Searched for it: the distinguishing test is *consumption*. A tracker with no consumer rots; this
contract is consumed at THREE existing gates (plan-review-gate, close check, pulse) — it is born
with consumers. Also searched: does demand exist (measure-before-enforce)? Yes — the diagnosis IS
the demand measurement (7h freeze, 96 plans, blindspot over_caution=56). Also searched whether
the front-end is already built: `interview-prompt` exists but is taste/writing-scoped and
unwired to plan kickoff; `/decide` Phase 0 frames but doesn't externalize the inputs into a
consumed contract. So the front-end is genuinely under-built (architectural gap), not merely
under-instructed. Decision survives consider-the-opposite — CONTINGENT on the advisory-shadow
gate measuring a low false-positive rate before any enforcement (without it, this becomes the
ratchet the feature-work ADR warns against).

## Decision

1. **One typed plan contract** — a canonical machine-parseable block in `.claude/plans/*`
   (form chosen in Phase 1; **probed**: plans carry neither frontmatter nor such a block today,
   1/32, so this is a convention addition either way — the existing plan-status hooks that already
   parse plans set the parse precedent), regime-aware. Fields, by verifier regime:
   - **clean** (hutter): `hypothesis`, `exit_signal`, `operator_decision_if_any`. No user-story.
   - **partial** (genomics, phenome): `scope_in`, `scope_out`, `exit_signal`, `verifier_commands`,
     `execution_surface`, `closure: {verifier_ran}`; `telos_check` if cross-repo.
   - **principal/taste**: `user_story`, `success_metric`, `divergent_options_ref`,
     `authority_split`.
   The contract is the SINGLE definition of these inputs (invariant-has-one-definition); skills
   READ it, nothing executes it (manifest-as-interface, per `loop.yaml`).
2. **Elicit at kickoff, once.** Extend `interview-prompt` with a `project-kickoff` route that asks
   only the 3–5 highest-information *underivable* inputs (variance × update-magnitude filter
   already in the skill), regime-gated, and writes them into the plan's contract block. `/decide` Phase 0
   produces the same contract for consequential arch work. "Demand more from Markus" = demand the
   RIGHT few up front, not a longer quiz.
3. **Consume at the gates that exist** — no new gate process:
   - `plan-review-gate` additionally checks contract-presence-by-regime — **advisory/shadow**,
     report-only, measure false-positive rate ≥2 weeks before any promotion to a soft block.
   - Close: a thin `verifier_ran:` check (command + exit code surfaced) — the *checkable* slice of
     D2; "surface known bad state" stays a semantic ask in `/critique close`/`/rsi`.
   - Correct: planning-failure classes are `pulse`/`blindspot` detectors (mostly already firing).
4. **Execution force-function — D9 only.** A per-repo routing-warn (genomics first) when a bash
   call has a purpose-built MCP replacement. D1/D5/D6/D7 are accepted as already-instructed +
   detected; no new prose.
5. **Propagate the working patterns** (docs, copy-stamp): `foundation-exit` exit-block,
   genomics `CERT-SPEC`/`OPERATOR-PREFLIGHT`, `docs/handoffs` convention, and a per-repo
   **operator-decision-set** table (what Markus owns vs the agent owns) into the repos lacking
   them. No new skill.
6. **No action on D3, D10** (shipped) and **no new platform**.

## Evidence

- Audit: 3 repo fact-checkers (PRESENT/ABSENT/MISMATCH) + agentlogs FTS + rule-coverage grep,
  this session. G1 unverified; D3/D10 shipped; D6 hook fired on this session's own dispatches.
- Existing infra read first (read-before-plan): `loop.yaml`/regimes, `pulse` (canary+gate thin,
  weights deferred), `plan-review-gate`, `feature-work-loop-binding` (measure-first invariants),
  `shared-checkout-isolation` (D10 resolved), `interview-prompt` SKILL.
- Constitution P1 (architecture>instructions), P3 (measure before enforcing), self-improvement
  governance gate; `state-externalization-lens`.

## Cross-model panel outcome & converged scope (2026-06-18)

Panel: 2 repo-grounded Opus agents (fact-checker; spine-critic+alt-explorer) + 1 cold cross-lab
(GPT-5.5, no repo access). **Verdict: SPINE SOUND — zero mechanism reversals.** GPT (cold,
unanchored) independently returned "SPINE SOUND / PLAN BLOATED." The kickoff-contract-consumed-by-
existing-gates mechanism survives; the panel resolved one level deeper into **scope**, not spine.

**Rejected from the panel (verify-before-fold):**
- Fact-checker ABSENT verdicts on `interview-prompt`/`pretool-inventory-dispatch.py`/plan-status
  hooks — **search errors** (it searched `agent-infra/.claude/`, the files live in
  `~/Projects/skills/`; re-verified present). The spine-critic's "REVERSE" verdict partly inherited
  this false premise (the /decide skill's documented wrong-directory-reverses-spine failure mode).
- "Detection-only" alternative — rejected: detection re-finds the 96-plan proliferation every time
  without *preventing* the genuinely-missing exit-input (D4); prevention at the cheap front-end wins
  for missing-input classes.

**Folded (converged scope — the plan is narrowed to a minimal CONSUMED slice):**
1. **Minimal vertical slice first.** Phase 1 only: define the contract block + a *canonical shared
   parser* (not a throwaway) → write ONE real phenome plan with it → extend `plan-review-gate` to
   report presence (advisory). STOP. Everything else is explicitly **post-validation, contingent on
   the slice proving a field changes an outcome** — not bundled.
2. **Every field must change a gate outcome, a closeout claim, or a human decision** (GPT #2). A
   field that is only displayed/archived is a tracker field → cut. Each field maps to a specific
   uncovered class (D4→`exit_signal`, D3/D2→`scope_out`+`verifier_commands`); fields with no mapped
   class are dropped. This is the real anti-tracker defense (stronger than "born with consumers,"
   which is aspirational until a consumer is wired).
3. **Regime is repo-level**, set once in each repo's CLAUDE.md (hutter=clean, genomics/phenome=
   partial, product-facing=principal), per-plan override only on divergence — NOT re-declared per
   plan. Single-sources the regime vocabulary with `verifier-conditional-autonomy` (its 3 regimes)
   and keeps the cookbook's `coverage-poor` discovery-only (no drift).
4. **D9 routing-warn is split out** (GPT #7) — it's an MCP-bypass fix orthogonal to kickoff
   contracts; its own small work item, gated independently.
5. **Phase 5 pattern-propagation is CUT from this plan** (GPT #8/#12) — prose-spread risk, and a
   `single-source governance index` substrate (commit `4bd3b6a`) may already cover the
   operator-decision-set table. Reintroduce only if the contract proves useful + check that commit.
6. **Promote criterion = low FP AND a usefulness signal** (GPT #3): the contract must be shown to
   have prevented a real scope/exit/authority failure, not merely a <15% false-positive rate.

## Revisit if

- The advisory contract-presence check shows a high false-positive rate (>~15%) over 2 weeks →
  the contract is misfit; demote to docs-only.
- The contract accrues fields nobody consumes → it is becoming a tracker; cut unconsumed fields.
- A second concrete need for cross-repo telos reconciliation appears → harden `telos_check`.
- The cross-model panel (Phase 4) produces an architecture-spine reversal → reopen here (this ADR
  is `proposed`; it becomes `accepted` only after the panel stops producing reversals, per the
  pulse/cookbook precedent).

## Supersedes

None. Branches from `2026-06-07-verifier-conditional-autonomy` (regime taxonomy); subsumes the
alignment report's §3–7 recommendations into the chosen mechanism (those become this ADR's
rejected/folded alternatives, not a parallel build).

## Revisions

### 2026-06-18 — Phase-1 slice shipped; operator overrode the panel's "defer front-end"
- **Phase-1 minimal slice SHIPPED** (commit `125c803`): extended `scripts/plan-status.py` with
  `--contract-check` (advisory, never blocks) + `--contract-init` (light elicitation: 3 answers →
  frontmatter block). Partial-regime, 3 fields, reuses the canonical `parse_frontmatter`. Measured
  shadow baseline: **0/169** partial-regime plans carry the contract (it's new — not 169 bad plans).
  Even phenome's `foundation-exit` exemplar reads as missing: it has a measurable exit in *prose*
  but not in a machine-checkable block — the externalization gap, confirmed.
- **Sequencing FLIPPED by operator (#f).** The panel deferred the interview / requirements / vision
  / user-story front-end to post-validation; the operator — the principal on his own planning
  process — directs it as **first-class now**, grounded in best-practice research and **versioned**.
  This is a principal-register telos call (amplify, not measure-first); logged per the
  autonomy-exception convention (clear/partial → principal-final is the operator's to make).
  Dispatched 3 research axes → `research/2026-06-18-{elicitation,spec-formats,spec-versioning}-
  best-practices.md`. The front-end design + a contract **versioning** scheme will be added here
  once that research lands. The Phase-1 slice stands as the consumption substrate it plugs into.
