---
title: Plan-contract front-end — research synthesis (elicitation × spec-format × versioning)
date: 2026-06-18
status: active
---

# Plan-contract front-end — research synthesis

Synthesizes 3 parallel research axes (operator-directed, #f) into the grounded design for the
planning-lifecycle contract's **human-input front-end + versioning**. The format is the cheap part;
the leverage is eliciting the few underivable inputs and keeping the spec honest over time.

**Inputs** (all 2026-06-18):
- `research/2026-06-18-elicitation-best-practices.md`
- `research/2026-06-18-spec-formats-best-practices.md`
- `research/2026-06-18-spec-versioning-best-practices.md`

**Decision:** `decisions/2026-06-18-planning-lifecycle-contract.md` (Phase-2 front-end).

## The 3-way convergence (independent axes, same conclusion)

1. **Format = cheap 20%; eliciting the few underivable inputs + a staleness story = the leverage.**
   All three memos reached this independently.
2. **The 2025-26 spec-driven-dev frontier is a CAUTIONARY TALE, not a model.** Fowler/Böckeler's
   hands-on comparison: *more spec → less adherence* — spec-kit regenerated existing classes as
   duplicates; Kiro turned a bug fix into 4 stories / 16 acceptance criteria; "amplifies review
   overload + hallucinations." No winner. → validates our minimal-contract spine. The one thing
   **all of them lack is an executable parity oracle** — which is exactly our `verifier_commands`.
3. **The verifiability ladder maps 1:1 onto our regimes** (confirmed from the formats AND the
   versioning angle): clean → executable command (required); partial → command where one exists,
   else an EARS-observable line; principal → success_metric + checklist DoD (don't fake a command
   when the human is the verifier).
4. **Regime lives at the repo / constitution layer**, not per-plan — confirmed (matches the panel fold).

## Grounded contract schema (final, regime-gated, single ≤~15-line block)

| Field | Regime(s) | Guards / consumer | Grammar |
|---|---|---|---|
| `regime` | all | selects required set | clean\|partial\|principal (repo default) |
| `telos` | all (1-line; principal: fuller) | **intent-drift** — the ONE convergent gap across all PRD formats | "why / for-whom" |
| `exit_signal` | all | D4 (no measurable stop) | **EARS** observable |
| `scope_out` | partial, principal | D3/D2 (creep) | negative-space ("what would make this wrong") |
| `verifier_commands` | clean (req), partial | D2 closure + **the parity oracle SDD tools lack** | executable command |
| `success_metric` | principal | DoD when the human is the verifier | checklist (no fake command) |
| `hypothesis`, `operator_decision` | clean | hutter-style | — |
| `user_story`, `authority_split` | principal | product/taste register | — |

**STEAL: EARS** (`WHEN <trigger> THE SYSTEM SHALL <observable behavior>`, 5 patterns from
safety-critical RE). Its value: it makes a non-observable acceptance criterion *ungrammatical* — you
cannot write "handles edge cases gracefully" in EARS. Turns `exit_signal`/`verifier_commands` from
aspiration into a checkable predicate. The `--contract-check` adds an advisory warn on a
non-observable `exit_signal`. `telos` is the only NEW field vs the shipped slice.

## Versioning scheme (operator: "version it") — Git IS the substrate, no DB

- `spec_version` (SemVer; **MAJOR = "invalidates work agents already did"** — the plan-specific bump rule)
- `status` (draft → accepted → superseded)
- `governs_commit` (artifact SHA last reconciled — the drift anchor)
- append-only `## Changelog` in-file by default; `supersedes:` → a new file ONLY for wholesale replacement
- ~15-line staleness check: `git rev-list --count <governs_commit>..HEAD` on the governed path (spec
  untouched while its target churns ⇒ stale) — the parity gate the SDD tools conventionally promise
  but **none enforce**; ours is real because `verifier_commands` is executable
- `Spec-Version:` commit trailer → queryable provenance via `git log` (native-first; no DB)
- **REJECT:** a bitemporal DB for a single doc (over-build — Git is already bitemporal for files);
  SDD IDE/platforms; monotonic-int-only versioning; supersede-every-edit; version-without-a-diff-gate.

## Elicitation design — 3 edits to `interview-prompt` (the front-end the operator asked for)

interview-prompt already nails *which* question (info-gain). It lacks *what a kickoff must cover* and
*when not to ask*. Three edits:

1. **Step-0 six-cell coverage gate.** A kickoff must cover: **outcomes · scope-OUT · constraints ·
   prior-decisions · acceptance/exit · authority-split** (mostly the tacit, agent-underivable cells).
   Questions may only target cells still `unknown`.
2. **Score by SOLUTION-space split, not answer-variance** (Active Task Disambiguation, Kobalczyk,
   ICLR 2025, arXiv:2502.04485). A high-answer-variance question whose answers yield the *same plan*
   is worthless; reason in the space of viable solutions.
3. **Add the assume-and-mark branch** (Spec-Kit's real `[NEEDS CLARIFICATION]` template). Default to
   a calibrated guess and *record* it; ask only when the unknown is underivable AND high-impact. Maps
   1:1 onto `feedback_question_scope` + `feedback-see-it-through-when-confident`. interview-prompt has
   ask/drop today — add the third branch (assume + record).

**Straw-man-first** (Wiegers, the RE-canon parent of GA's predict step): the agent drafts the plan;
the cells it can't confidently fill *are* the question set. Pair each ask with a scenario ("the one
run that must succeed" → acceptance) and a negative ("what would make this wrong" → scope-OUT, the
single most-missed category).

## STEAL / AVOID (from the formats memo)

- **STEAL:** EARS for exit/acceptance; the constitution-layer regime (repo-level, not per-plan); an
  explicit clarify/elicit step.
- **AVOID:** multi-file artifact trees (`.specify/`); auto-generated or mandatory-expanded acceptance
  criteria; "spec as living source of truth" (Tessl MDD-inheritance risk); user stories outside the
  principal regime; free-text acceptance fields.

## Post-synthesis completeness check (every input landed)

- **elicitation memo** → six-cell gate (1) + solution-space scoring (2) + assume-and-mark (3) +
  straw-man-first ✓
- **spec-formats memo** → EARS + `telos` + verifiability-ladder=regimes + single-block + STEAL/AVOID ✓
- **versioning memo** → `spec_version`/`status`/`governs_commit` + changelog/supersedes + staleness
  hook + `Spec-Version:` trailer + reject-DB ✓

## Provenance caveats (AI-output, graded)

- elicitation: `fetch_paper` failed on the arXiv targets (used /abs); load-bearing Wiegers claims came
  via search snippet → graded down. Kobalczyk arXiv:2502.04485 verified at /abs.
- All SDD claims (spec-kit / Kiro / Tessl / Fowler-Böckeler) are 2025-26 → search-grounded, not recall.
- Cross-check before building on a single-source claim; the EARS grammar + the SemVer MAJOR-rule +
  the six-cell set are multiply-sourced and safe to build on.

## Sources

The 3 sibling memos; Kobalczyk et al., *Active Task Disambiguation* (ICLR 2025, arXiv:2502.04485);
Fowler/Böckeler SDD-tool comparison (martinfowler.com, 2025); EARS (Mavin et al.); GitHub Spec-Kit
repo; Wiegers, *Software Requirements*.
