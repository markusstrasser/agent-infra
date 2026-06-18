---
title: Spec/PRD Formats + Spec-Driven-Development-for-AI-Agents — Best Practices for the agent-infra Plan Contract
date: 2026-06-18
status: complete
tags: [planning-contract, spec-driven-development, spec-kit, kiro, EARS, acceptance-criteria]
---

# Spec Formats Best Practices — agent-infra Plan Contract

Axis (one only): specification/PRD formats + the 2025-26 spec-driven-development (SDD) frontier for AI coding agents.
Goal: recommend the field set + format for our agent-consumed "plan contract" (current slice: `exit_signal`, `scope_out`, `verifier_commands`, `regime`).

Anchor decision this feeds: `decisions/2026-06-18-planning-lifecycle-contract.md` — chosen mechanism is a
**typed plan contract elicited at kickoff, regime-gated, consumed by gates that already exist**, where
**every field must change a gate outcome / closeout claim / human decision** (else it's a tracker field → cut).
Sibling research (do not duplicate): `…-elicitation-best-practices.md` (HOW to elicit), `…-spec-versioning-best-practices.md` (keeping specs in sync).

---

## TL;DR — the verdict for our contract

The 2025-26 SDD frontier (spec-kit, Kiro, Tessl) **validates the ADR's anti-bloat thesis with hard failure data**,
not refutes it. The headline finding from every critical source: the spec formats these tools ship are **too
verbose for the work**, agents **don't reliably parse long specs**, and stale specs **actively mislead**. The
parts worth stealing are small and specific:

1. **EARS notation** (Easy Approach to Requirements Syntax) for the *one* place we need testable behavior:
   the verifier/acceptance line. `WHEN <trigger> THE SYSTEM SHALL <observable behavior>` is a 5-pattern
   grammar that forces every acceptance criterion to name a trigger + an *observable* outcome → directly
   maps to "is there a command that checks this." Steal the grammar, not the tooling.
2. **The constitution layer** (spec-kit's `constitution.md`, Kiro's "steering" files) = durable project
   principles the agent references on every task. **We already have this** (repo `CLAUDE.md` + Constitution).
   Confirms: regime + durable rules belong at repo level, NOT re-stated per plan (matches ADR §3).
3. **Requirement→task back-references** (Kiro/spec-kit link tasks to the requirement ID they satisfy) =
   the traceability that makes closeout checkable. Our analog: `verifier_commands` *are* the back-reference
   (a task is done when its verifier passes), so we don't need a separate ID graph.

What to **avoid**: the multi-file artifact set (spec.md + plan.md + tasks.md + research.md + data-model.md +
contracts/ + quickstart.md), auto-generated user stories, mandatory acceptance-criteria expansion, and
specs-as-living-source-of-truth (Tessl's bidirectional sync) — all measured to produce review overload,
duplication, and drift at our scale.

**One-line recommendation:** our contract should be a **single ≤~15-line typed block at the top of the plan
file**, regime-gated, with the *verifier/exit* fields written in EARS-style observable form. Not a folder.
Not a document set. The contract is the minimal-yet-sufficient executable core that spec-kit/Kiro bury
inside a verbose artifact tree.

---

## 1. Classic spec/PRD formats — what FIELDS make a spec executable + verifiable

Surveyed: Amazon PR-FAQ, lean one-pager PRD, RFC/design-doc, user-story + acceptance-criteria, BDD/Gherkin,
spec-by-example, and EARS. The executable/verifiable core that survives across all of them is small.

| Format | Core fields | What makes it verifiable | Fit for an *agent-consumed kickoff contract* |
|---|---|---|---|
| **Amazon PR-FAQ** | press-release (the win, customer-facing) + FAQ (objections) | working-backwards forces a *telos* statement; FAQ surfaces scope edges | Telos only. Too narrative for kickoff; the "why/for-whom" is the salvageable bit. |
| **Lean one-pager PRD** | problem, goal/success-metric, scope-in, scope-out, non-goals | success-metric + explicit non-goals = the two checkable fields | **High** — this is essentially our contract minus the verifier. `scope_out`/non-goals confirmed load-bearing. |
| **RFC / design-doc** | context, proposal, alternatives, tradeoffs, rollout | alternatives-considered = audit trail; not itself a pass/fail | Low for kickoff (it's a *decision* artifact). We have `decisions/` for this. |
| **User-story + acceptance-criteria** | "As a \<role\> I want \<X\> so that \<Y\>" + AC list | AC list is the verifiable part — IF the AC are observable | Story = principal-regime only; AC pattern = universal (see EARS). |
| **BDD / Gherkin** | Given / When / Then scenarios | Then-clause is directly executable (test maps 1:1) | The *shape* transfers (trigger→observable), but Gherkin's full scenario syntax is heavier than we need. |
| **Spec-by-example** | concrete input→output examples as the spec | examples ARE the test fixtures | Excellent where a clean verifier exists; = our `verifier_commands` with fixtures. |
| **EARS** | 5 patterns, all ending `… THE SYSTEM SHALL \<behavior\>` | every requirement names trigger + *observable* behavior → testable by construction | **Highest** — smallest grammar that guarantees a checkable acceptance line. |

**The convergent executable core** (the intersection across formats): a verifiable spec needs exactly
(a) a **goal/telos** (why, for whom — one line), (b) **scope-out / non-goals** (the boundary), (c) a
**success criterion stated as an observable outcome** (not an intention), and (d) a **done condition**
(exit). Everything else in these formats is narrative context that an agent either ignores or drowns in.
Our current slice (`exit_signal`, `scope_out`, `verifier_commands`, `regime`) already covers (b), (c+d).
The gap is (a) **telos**, and only for the regimes where the agent can't derive the "right thing" from the
repo alone (principal/taste, cross-repo).

### EARS in detail (the one grammar to steal)

EARS (Mavin et al., originally Rolls-Royce; widely used in aerospace/automotive/medical — i.e. safety-critical,
where "is this requirement testable" is non-negotiable). Five patterns, each forcing trigger + observable
behavior ([alistairmavin.com/ears](https://alistairmavin.com/ears/), [Terzakis tutorial PDF](https://www.iaria.org/conferences2013/filesICCGI13/ICCGI_2013_Tutorial_Terzakis.pdf)):

```
Ubiquitous:        THE SYSTEM SHALL <behavior>.                         (always true)
Event-driven:      WHEN <trigger> THE SYSTEM SHALL <behavior>.          (on an event)
State-driven:      WHILE <state> THE SYSTEM SHALL <behavior>.           (during a state)
Optional feature:  WHERE <feature included> THE SYSTEM SHALL <behavior>.(conditional on config)
Unwanted behavior: IF <unwanted trigger> THEN THE SYSTEM SHALL <behavior>. (error/edge handling)
```

Why it matters for *us*: the value isn't the prose template — it's that **the grammar makes a non-observable
acceptance criterion ungrammatical.** You cannot write "the function handles edge cases gracefully" in EARS
without naming the trigger and the observable response. That is exactly the discipline that turns
`exit_signal` / `verifier_commands` from aspiration into a checkable predicate. Note: spec-kit itself does
NOT use EARS by default and there's an open feature request to add it ([spec-kit#1356](https://github.com/github/spec-kit/issues/1356)) — Kiro *does* (below). We take the grammar directly, skipping both tools.

---

## 2. The 2025-26 SDD frontier — how the tools structure the agent-consumed spec, and what they got right/wrong

By 2026 every major coding tool shipped an SDD flavor: GitHub Spec Kit, AWS Kiro, Claude Code, Cursor,
OpenSpec, BMAD, Tessl, Google Antigravity ([Augment Code guide](https://www.augmentcode.com/guides/what-is-spec-driven-development)).
The three that define the design space — and the one independent comparison that critiques all three —
are Kiro, spec-kit, and Tessl ([Martin Fowler / Birgitta Böckeler, "Understanding SDD: Kiro, spec-kit, and Tessl"](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)).

### GitHub spec-kit

Artifacts ([github/spec-kit](https://github.com/github/spec-kit)):
- `.specify/memory/constitution.md` — project governing principles (durable).
- `specs/<feature-id>/spec.md` — functional requirements + user stories.
- `specs/<feature-id>/plan.md` — technical implementation strategy.
- `specs/<feature-id>/tasks.md` — actionable task breakdown.
- Supporting: `research.md`, `data-model.md`, `api-spec.json`, `contracts/`, `quickstart.md`.

Commands: `/speckit.constitution`, `/speckit.specify`, `/speckit.clarify` (resolve underspecified areas),
`/speckit.plan`, `/speckit.analyze` (cross-artifact consistency), `/speckit.tasks`, `/speckit.implement`,
`/speckit.checklist` (validate requirements), `/speckit.converge` (assess codebase vs artifacts).

**Right:** the `constitution` layer (durable principles referenced on every phase); an explicit `clarify`
step (elicit before building — same instinct as our kickoff interview); `analyze` for cross-artifact
consistency; a `checklist` validation pass.
**Wrong (measured):** "very verbose," one spec → many files across `.specify`; reviewer fatigue ("I'd rather
review code than all these markdown files"); and the killer — **the agent ignored research notes describing
existing classes and regenerated them, creating duplicates**, despite the elaborate spec. I.e. *more spec did
not produce more adherence.* Treats a spec as a per-change-request artifact (branch per spec), not a living
feature doc.

### AWS Kiro

Artifacts ([kiro.dev/docs/specs](https://kiro.dev/docs/specs/)): a **3-file linear flow** —
- `requirements.md` — user stories ("As a…") + acceptance criteria in **EARS** notation
  (`WHEN <condition> THE SYSTEM SHALL <behavior>`; full keyword set WHEN/IF/WHILE/WHERE). Sections:
  user stories, system behaviors (EARS), functional requirements, edge cases & error handling.
- `design.md` — technical architecture, sequence diagrams, implementation approach.
- `tasks.md` — discrete, trackable tasks with clear descriptions, expected outcomes, and dependencies.

Two workflow variants: Requirements-First and Design-First. Memory via optional "steering" files (= constitution).

**Right:** the **simplest, most intuitive model** of the three (Req→Design→Tasks); **EARS acceptance criteria**
(the one genuinely verifiable field pattern in the whole SDD space); tasks carry expected-outcome +
dependencies; steering files = durable principles.
**Wrong (measured):** **massive over-specification for small work** — "a small bug fix generated 4 user stories
with 16 acceptance criteria" (Fowler/Böckeler). Auto-generated criteria degrade into "requirements dressed as
user stories" ("As a developer, I want the transformation function to handle edge cases gracefully…" — a
non-observable AC, exactly what EARS is supposed to prevent, defeated by auto-generation). Specs are temporary
planning artifacts, not kept in sync with code.

### Tessl (the spec-as-source extreme)

One spec file → one generated code file; tags `@generate` / `@test` control output; generated files marked
"DO NOT EDIT"; **bidirectional spec↔code sync**.
**Right:** most concise *at the file level*; lowest abstraction gap (fewest LLM interpretation hops);
only tool seriously pursuing specs-as-source.
**Wrong (measured):** non-determinism persisted even with detailed specs — author "had to iterate on the spec
and make it more and more specific to increase repeatability." Fowler/Böckeler draws the **Model-Driven
Development parallel**: spec-as-source risks inheriting MDD's inflexibility *and* LLM non-determinism
simultaneously. (This is the cautionary tale for anyone tempted to make our plan contract the source of truth.)

### The cross-tool verdict (independent, the most valuable single source)

Böckeler declares **no winner** and questions the premise: *"I wonder if some of them are trying to feed AI
agents with our existing workflows too literally, ultimately amplifying existing challenges like review
overload and hallucinations."* Her one constructive design requirement: **"An effective SDD tool would at the
very least have to provide flexibility for a few different core workflows, for different sizes and types of
changes."** → directly validates our **regime-gating** (different required fields by clean/partial/principal)
and **scale-sensitivity** (don't force 16 AC onto a bug fix).

### Why SDD exists at all (the three failure modes it targets)

From [BCMS SDD 2026 guide](https://thebcms.com/blog/spec-driven-development) and corroborating sources, SDD is
a response to three LLM-coding failure modes: **intent drift** ("add login" is underspecified; the model picks
defaults that don't match intent), **context decay** (agent forgets older decisions past its context window and
silently contradicts them), and **unverifiable output** (no acceptance criteria → no way to know the code is
right). Our contract targets the same three: telos+scope fight intent drift, repo-level regime/constitution
fights context decay, `verifier_commands`/EARS exit fights unverifiability. Same disease, lighter dose.

### The dissenting frame worth holding

[Scala Teams, "SDD Doesn't Fix the Requirements Problem"](https://www.scalateams.com/blog/spec-driven-development-requirements-problem)
and [Augment Code, "What SDD gets wrong"](https://www.augmentcode.com/blog/what-spec-driven-development-gets-wrong):
the hard part was never the *format* of the spec — it's knowing what to build (requirements elicitation) and
keeping the spec true as reality changes (staleness). A prettier template doesn't fix an under-elicited
requirement. **This is exactly the ADR's thesis** ("planning failures are under-elicited inputs, not
under-instructed execution") arrived at independently by the SDD critics. Implication for us: the *format* work
(this memo) is necessary but not sufficient — it must sit on top of the elicitation work (sibling memo) and a
staleness story (sibling memo). The contract format alone is the cheapest 20%.

---

## 3. Acceptance-criteria / definition-of-done patterns that make work verifiable by an executor

The patterns that actually make a deliverable checkable, ranked by fit to an *agent* executor:

1. **Executable verifier command (highest).** A literal command + expected exit/result. This is our
   `verifier_commands` and it dominates every prose pattern: it's the only AC an agent can run *itself*
   before claiming done. Spec-by-example and BDD's Then-clause both reduce to this when there's a clean
   verifier. Maps to the Constitution's "clear verifier" regime.
2. **EARS observable-outcome line (when no command exists yet).** `WHEN <trigger> THE SYSTEM SHALL <observable>`
   — forces the AC to be about something *witnessable*, even if the witness is a human read, not a script.
   This is the bridge for the *partial* regime where the verifier is noisy/delayed.
3. **Scenario / Given-When-Then (BDD).** Heavier; good when behavior has meaningful state preconditions.
   Use only when the trigger isn't enough and the precondition matters.
4. **Checklist DoD (lowest, but non-zero).** A flat "definition of done" list. Gameable and prose-y (BetterBench
   showed checklists are a FLOOR, not a validity cert — see `research/2026-06-14-eval-methodology-canon.md`),
   but fine for the *principal* regime where the real verifier is human taste.

**The verifiability ladder maps 1:1 onto our regimes** — this is the unlock:
- **clean** regime → AC = executable verifier command (#1). Required.
- **partial** regime → AC = verifier command where one exists, else EARS observable line (#2) naming what a
  human checks. The `exit_signal` should be written EARS-style.
- **principal** regime → AC = success_metric + a checklist DoD (#4); the human is the verifier, so don't fake
  a command.

**The anti-pattern to encode against** (from the Kiro data): an acceptance criterion that states an *intention*
("handles edge cases gracefully," "works correctly," "is robust") rather than an *observable*. EARS grammar
makes this ungrammatical; a free-text AC field invites it. So if we add an acceptance/exit field, **constrain
its form** (EARS or a command), don't leave it free-text.

---

## Recommended field set + format for OUR plan contract

### Format

A **single typed block at the top of the plan file** (`.claude/plans/*.md`), YAML or a fenced `contract`
block — NOT a multi-file artifact tree. Rationale: plans today carry no such block (1/32 per the ADR probe),
so this is a convention addition either way; a single block is parseable by the existing plan-status hooks and
costs ~15 lines, vs spec-kit's measured review-overload from a `.specify/` folder. **One block, one parser**
(the ADR's canonical shared parser), regime-gated.

### Fields, by regime (every field maps to a consumer — no display-only fields)

```yaml
# --- always (any regime) ---
regime:        clean | partial | principal   # repo-level default (CLAUDE.md); per-plan override only on divergence
telos:         <one line: the win + for whom>  # NEW — closes the convergent-core gap (a); fights intent-drift
scope_out:     [<explicit non-goals / boundaries>]   # consumed by orchestrator scope-guard (D3)
exit_signal:   <EARS-style observable: "WHEN <X> the work is DONE">  # consumed by close check (D4); the #1 missing input

# --- clean regime adds ---
hypothesis:           <the claim the run tests>
verifier_commands:    [<cmd → expected exit/result>]   # AC pattern #1; consumed at closeout (verifier_ran)

# --- partial regime adds ---
scope_in:             [<in-bounds>]
verifier_commands:    [<cmd>]            # where one exists
acceptance:           [<EARS line per criterion where no command exists>]   # AC pattern #2, constrained form
execution_surface:    <where it runs>    # local | modal | hetzner | …
operator_decision:    <any human-owned call already made>   # prevents the D1 re-freeze of a settled decision

# --- principal / taste regime adds ---
user_story:           "As a <role> I want <X> so that <Y>"
success_metric:       <observable proxy for the taste call>
divergent_options_ref: <link to options explored>   # Constitution P6
authority_split:      <what the human owns vs the agent owns>
```

**Field-justification table** (the anti-tracker gate — each field changes a gate outcome, a closeout claim,
or a human decision; drop any that doesn't):

| Field | Regime(s) | Consumer / what it changes | Source pattern |
|---|---|---|---|
| `regime` | all | selects required-field set; routes autonomy | Böckeler "flexibility for different change types" |
| `telos` | all | human decision: is this the right thing? fights intent-drift | PR-FAQ working-backwards; lean PRD goal |
| `scope_out` | all | orchestrator scope-guard (D3); gate outcome | lean PRD non-goals |
| `exit_signal` | all | close check (D4); closeout claim | EARS event/unwanted pattern |
| `hypothesis` | clean | closeout: was it confirmed? | spec-by-example |
| `verifier_commands` | clean/partial | closeout `verifier_ran`; gate outcome | AC pattern #1; Kiro tasks→outcome |
| `acceptance` (EARS) | partial | human-checkable closeout where no cmd | Kiro EARS; AC pattern #2 |
| `execution_surface` | partial | routing; probe-primitive-first | (ours) |
| `operator_decision` | partial | prevents re-litigating a settled call (D1) | (ours; ADR panel finding) |
| `user_story` | principal | frames the taste target | Kiro/agile user story |
| `success_metric` | principal | the proxy the human grades against | lean PRD success-metric |
| `divergent_options_ref` | principal | Constitution P6 artifact gate | RFC alternatives |
| `authority_split` | principal | human decision boundary | (ours) |

### Steal vs avoid (the deliverable's punchline)

**STEAL from spec-kit / Kiro / Tessl:**
- **EARS grammar** for `exit_signal` and the partial-regime `acceptance` field — the one mechanism that makes
  acceptance criteria observable-by-construction. (Take the grammar; skip both tools' generators, which
  defeat it via auto-expansion.)
- **The constitution/steering layer = repo-level durable principles** — confirms regime + rules live in
  `CLAUDE.md`, not the per-plan contract (we already do this; SDD independently arrived here).
- **An explicit `clarify`/elicit step before building** (spec-kit `/clarify`, Kiro's interactive req gathering)
  — validates the ADR's kickoff interview. (Detail in the elicitation sibling memo.)
- **Task→requirement traceability** as a *concept* — but realized as `verifier_commands` (a task is done when
  its verifier passes), not a separate requirement-ID graph.

**AVOID (measured failure at our scale):**
- **Multi-file artifact trees** (`spec.md` + `plan.md` + `tasks.md` + `research.md` + `data-model.md` +
  `contracts/` + `quickstart.md`). Review overload; agents ignore the bulk. One block.
- **Auto-generated / mandatory-expanded acceptance criteria** (Kiro's 16-AC bug fix; "requirements dressed as
  user stories"). Make AC required-but-constrained-in-form, never auto-bloated. Scale AC count to change size.
- **Specs as the living source of truth / bidirectional sync** (Tessl). MDD-inheritance risk + non-determinism;
  our plan contract is a *kickoff* artifact, not a source-of-truth doc. (Staleness handled in the versioning
  sibling memo, lightly.)
- **User stories outside the principal regime.** For clean/partial work a user story is theater
  ("As a developer I want the function to…") — use `hypothesis` / `exit_signal` instead.
- **Free-text acceptance fields.** They invite intention-statements ("handles edge cases gracefully"). Constrain
  to EARS or a command.

### The single most important design principle (cross-source convergence)

Both the independent SDD critic (Böckeler: tools "feed AI agents our existing workflows too literally,
amplifying review overload and hallucinations") and the requirements critics (Scala Teams / Augment: "SDD
doesn't fix the requirements problem") land on the same place the ADR did: **the leverage is eliciting the few
underivable inputs in a constrained form, not producing a verbose document.** More spec measurably did not
produce more adherence (spec-kit's duplicate-generation; Kiro's 16-AC bug fix). So our contract should be the
**smallest block that makes the work verifiable** — telos + scope + an observable exit, with regime selecting
the 2-4 extra fields that actually gate something. That is precisely the current 4-field slice plus `telos`
(and the regime-conditional extras), with the exit/acceptance fields written in EARS form.

---

## Sources

- [github/spec-kit](https://github.com/github/spec-kit) — artifacts, commands, constitution.
- [Kiro docs — Specs](https://kiro.dev/docs/specs/) and [Requirements-First Workflow](https://kiro.dev/docs/specs/feature-specs/requirements-first/) — 3-file flow, EARS acceptance criteria.
- [Martin Fowler / Birgitta Böckeler — "Understanding SDD: Kiro, spec-kit, and Tessl"](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) — the independent cross-tool critique (most valuable single source: 16-AC bug fix, spec-kit verbosity/duplication, Tessl MDD parallel, "no winner," flexibility-by-change-size).
- [Alistair Mavin — EARS official guide](https://alistairmavin.com/ears/) and [Terzakis EARS v1.0 tutorial (PDF)](https://www.iaria.org/conferences2013/filesICCGI13/ICCGI_2013_Tutorial_Terzakis.pdf) — the 5 EARS patterns.
- [spec-kit#1356 — EARS integration feature request](https://github.com/github/spec-kit/issues/1356) — spec-kit does not use EARS by default.
- [BCMS — Spec-Driven Development: The Definitive 2026 Guide](https://thebcms.com/blog/spec-driven-development) — the three failure modes (intent drift, context decay, unverifiable output).
- [Scala Teams — "SDD Doesn't Fix the Requirements Problem"](https://www.scalateams.com/blog/spec-driven-development-requirements-problem) and [Augment Code — "What SDD gets wrong"](https://www.augmentcode.com/blog/what-spec-driven-development-gets-wrong) — format ≠ requirements; staleness.
- [Augment Code — What Is Spec-Driven Development](https://www.augmentcode.com/guides/what-is-spec-driven-development) — 2026 tool landscape.

## Provenance note

All claims above are web-sourced (June 2026 search), tagged inline. SDD tooling is a fast-moving 2025-26 space —
spec-kit/Kiro field structures and commands verified against vendor docs/GitHub this session; the verbosity/
failure observations are from one careful independent practitioner (Böckeler) plus corroborating critic posts,
not a controlled study — treat the *failure-mode direction* as well-supported and the *magnitudes* (e.g. "16
acceptance criteria") as single-source anecdote. EARS is a stable, decade-old standard (low staleness risk).
