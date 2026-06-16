---
id: 2026-06-14-review-dispatch-consolidation
concept: review-dispatch
repo: agent-infra
decision_date: 2026-06-14
recorded_date: 2026-06-14
provenance: contemporaneous
status: accepted
initial_leaning: "Build a unified /review router skill that classifies artifacts and dispatches one pipeline"
relations:
  - type: branches_from
    target: 2026-06-12-vendor-binary-skill-archaeology
  - type: depends_on
    target: 2026-06-07-verifier-conditional-autonomy
  - type: depends_on
    target: 2026-06-04-consumption-over-autonomy
---

# 2026-06-14: Review dispatch — enforce partition + eval-gate, no new router skill

## Context

Session-end audit (2026-06-14) identified **review stack duplication** as the primary
waste vector: `/critique close` runs diff review (code-review) AND cross-model design
review on the same closeout; a proposed `composer-diff-review` launchd would add a seventh
parallel surface atop six existing review mechanisms.

Prior art already decided the spine:
- **Partition, don't compete** (`research/2026-06-12-vendor-binary-skill-archaeology.md`):
  diffs → code-review mechanics; plans/designs/findings → cross-model critique.
- **Verifier-conditioned routing** (`decisions/2026-06-07-verifier-conditional-autonomy.md`):
  clear verifier (bugs) vs partial verifier (design proxies) are different instruments.
- **`critique_replay` probe passed** (2026-06-13): cases discriminate; flash35 disqualified
  at probe (>1 invention on clean K2); full grid not yet run.

## Alternatives considered

1. **New `/review` router skill** — single entrypoint, artifact classifier, dispatch table.
   *Pro:* one mental model for agents. *Con:* SkillRouter overlap degrades routing
   (arXiv:2603.22455); adds a third skill beside `/critique` and `/code-review` without
   removing them; highest iatrogenic risk.

2. **Enforce existing partition + dedupe stacking** (chosen) — keep `/code-review` and
   `/critique`; fix closeout to review each layer once; merge nightly diff into
   `code-review-scout` schedule; eval-gate cosigner defaults via `critique_replay`
   verdict file; kill half-loops and superseded eval folders.

3. **Eval-first freeze only** — no skill changes until `critique_replay` full grid completes.
   *Pro:* zero routing risk. *Con:* leaves active closeout triple-review harm in production
   for weeks.

4. **Merge code-review into critique** — one mega-skill.
   *Con:* loses partition benefits; mixes diff finder/verifier mechanics with cross-model
   premise falsification; contradicts 2026-06-12 archaeology verdict.

5. **Vendor Claude Code plugin as canonical diff reviewer** — revert to embedded pipeline.
   *Con:* same-model martingale (9 Claude finders); we already un-archived local
   code-review with Composer default for cross-lineage diff review.

## Counterevidence sought

- **Would a router reduce confusion?** Searched skill descriptions: `/critique` already
  says "for code DIFF, use /code-review" (`skills/critique/SKILL.md:3`). Routing guidance
  exists; failure mode is **closeout workflow stacking**, not missing router.
- **Are the six surfaces redundant?** `posttool-review-check.sh` is an llmx failure circuit
  breaker, not a review pipeline. `fresh-eyes-review` is a blind-author subagent pattern
  (hutter/outer-loop), not duplicate diff review. Vendor `Workflow`/`code-reviewer` are
  opt-in orchestration — document "don't stack on closeout," don't delete.
- **Is flash35 safe as Gemini cosigner?** `critique_replay` probe: 2 inventions on K2 →
  disqualified per prereg. Conflicts with `model-guide` default — freeze until full grid.
- **Is skill-usage-watch worth keeping?** Collector has `pending: 23`, `audited: []` — half-loop
  is iatrogenic unless consumer ships.

## Decision

**Enforce partition architecturally. Do NOT add `/review`.**

### Governing principle

> **One artifact layer → one review pass → eval-gated defaults.**
> Partition (diff vs design) is settled; the bug is *stacking*, not *missing router*.

### Invariants (must preserve)

1. `/code-review` owns **diff** review (Composer default, local scouts).
2. `/critique` owns **plan/design/finding** cross-model review (`standard` = 2G+2GPT overlapping).
3. No change to default cosigner/model routing without `evals/critique_replay/ROUTING_VERDICT.md`
   (written post full grid) + `doctor.py` sync check.
4. Hooks that detect review *failures* (`posttool-review-check`) stay; they are not review stacks.
5. No new launchd job for diff review — extend `code-review-scout` / schedule instead.
6. Critique dispatch health: `model-review.py --preflight` before axis fan-out (P0 llmx refactor).

### Ship list (ordered)

| # | Change | Rationale |
|---|--------|-----------|
| 1 | **Fix `/critique close` Phase 2** — diff **only** via `/code-review` (Composer is its default provider, not a separate closeout path); design layer gets `standard` only on plan-close packet — **drop `standard,composer` on closeout design** | Removes triple-tap; Composer stays inside code-review for diffs |
| 2 | **Emergency negative gate:** demote `flash35` from default Gemini cosigner now (probe disqualified); positive promotion waits on full grid | Probe harm is live; promotion is gated |
| 3 | **`critique_replay` full grid** → `ROUTING_VERDICT.md` with **machine-readable JSON block** (doctor parses JSON only) | Evidence before positive promotion |
| 4 | **`doctor.py`:** if verdict missing/malformed → freeze defaults, exit nonzero | Fail-closed eval gate |
| 5 | **Closeout packet schema** in `build_plan_close_context.py`: `diff_target` + `design_target` fields | Machine-checkable partition |
| 6 | **Merge nightly diff into scout** — `code-review-schedule.py` `--since-last-green` with explicit fallback (`merge-base` with default branch if marker broken) | Replace, don't add launchd |
| 7 | **Kill `skill-usage-watch` launchd** — uninstall `com.agent-infra.skill-usage-watch`; audit pending queue once manually or drop; **do not** wire into `/improve maintain` | Half-loop + operator tax (critique round 1 consensus) |
| 8 | **Tombstone `evals/critique_efficiency/`** (README redirect) then delete | Broken-ref guard |
| 9 | **Scaffold `evals/critique_outcome_link/`** | Partial-verifier for design quality |

### Explicit rejections

- New `/review` skill
- `composer-diff-review` as separate launchd (`com.agent-infra.composer-diff-review`)
- Design-elegance LLM judge leaderboard
- Auto-stub prediction registration on governance commits
- Routing **promotions** before `ROUTING_VERDICT.md` JSON block (negative demotions allowed per item 2)
- **`skill-usage-watch` launchd** — kill, don't extend

## Evidence

- `research/2026-06-12-vendor-binary-skill-archaeology.md` (partition verdict)
- `research/2026-06-14-critique-decide-eval-strategy.md` (eval substrate)
- `evals/critique_replay/outputs/probe/PROBE-RESULTS.md` (flash35 disqualified)
- `improvement-log.md` 2026-06-07 risky-diff-review shadow (6 review surfaces already integrated)
- `decisions/2026-06-04-consumption-over-autonomy.md` (no verifier/consumer = no value)
- Cross-model critique round 1: `.model-review/2026-06-14-review-dispatch-consolidation-70ac34/` — spine held; folded closeout contract, kill skill-usage-watch, JSON verdict schema, emergency flash demotion

## Revisions
- **2026-06-14 post-critique:** Clarified Composer is inside `/code-review`, not a parallel closeout path; dropped `standard,composer` on closeout design; killed skill-usage-watch (was: wire consumer); added emergency negative gate + JSON verdict schema + closeout packet fields.

## Revisit if

- `critique_replay` full grid fails to discriminate (cases don't separate arms) → routing
  becomes operator-judgment-only; do not add router as workaround.
- Composer nightly diff review shows >2× recall vs scout at same cost → reconsider scout merge.
- Skill count drops such that `/review` router has zero overlap penalty (unlikely).

## Supersedes

Nothing. Narrows improvement-log `[ ]` nightly `composer-diff-review` launchd → scout extension.
