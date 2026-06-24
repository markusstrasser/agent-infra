---
id: 2026-06-24-risky-diff-review-shadow-retired
concept: verifier-conditioned-autonomy
repo: agent-infra
decision_date: 2026-06-24
recorded_date: 2026-06-24
provenance: contemporaneous
status: accepted
initial_leaning: keep the shadow accumulating until a clearer promote/cut signal emerged
relations:
  - type: retires
    target: 2026-06-07-guardian-angels-transfer
  - type: relates_to
    target: 2026-06-03-verifier-bound-autonomy
---

# 2026-06-24: Retire the risky-diff-review shadow — auto-review gate not justified

## Context

The `risky-diff-review` SHADOW (built 2026-06-07, `decisions/2026-06-07-guardian-angels-transfer.md`)
was a report-only detector counting high-blast-radius diffs (constitution/goals, behavioral-rule,
hook, schema, settings/mcp) that landed with **no test AND no review** in their session. Its sole
named consumer was one binary question: *build an auto-review gate for such diffs, y/n?* It carried
a self-imposed "promote/cut ~2026-06-21" date. That date is a reminder that fires only when an agent
acts; a maintain tick on 2026-06-24 acted on it.

## Alternatives considered

1. **Promote to an auto-review gate** — auto-dispatch `fresh-eyes-review` / `/critique` on flagged
   diffs. Rejected: the promote criterion was unmet (see Evidence).
2. **Keep accumulating (status quo)** — let the shadow run until a clearer signal. Rejected: its
   question is now answered with a controlled measurement; continuing is generation-without-consumption,
   and gov-id telos says a scaffold earns its place only while load-bearing.
3. **Retire the detector infra** (chosen) — the question is answered NO; remove the code, recipes,
   gov.py wiring, and one-shot plist. Evidence log archived (not destroyed).

## Decision

**Retire.** The auto-review gate is not built; the detector infra is eradicated.

## Evidence (the negative control is load-bearing)

Full 192-row shadow log, window 2026-05-08 → 2026-06-20 (6 weeks):

| Promote criterion | Result |
|---|---|
| (a) fires often | 19 review-worthy / 6wk ≈ 3/wk — modest, borderline |
| (b) unreviewed-risky correlates with later fixes | **FALSIFIED.** Flagged: 9/19 = **47%** had a later fix/revert touching their files. Control (30 NON-flagged commits to the same high-churn dirs — skills/hooks, scripts, .claude/rules): 14/30 = **47%**. Identical → the flag has **zero discriminative power**; 47% is file-churn baseline, not a risk signal. CONFOUNDED, not FIRED (`predict-then-falsify-gate.md`). |

Compounding: the original premise (self-review degeneracy) was already disconfirmed on Opus 4.8
(`decisions/2026-06-03-verifier-bound-autonomy.md`). The live hypothesis going in was CUT.

## What was removed

`scripts/risky_diff_review_shadow.py` · `scripts/risky-diff-review-oneshot.sh` ·
`scripts/tests/test_risky_diff_review_shadow.py` · `just risky-diff-shadow`/`risky-diff-report` ·
the `unreviewed_risky` block in `scripts/gov.py` · `com.agent-infra.risky-diff-review` plist.
Evidence log (`~/.claude/risky-diff-shadow.jsonl`, 53KB) archived to
`/Volumes/2TBPNY/claude-archive/shadow-logs/`. Fully git-reversible.

## Consequences

- One fewer report-only scaffold; `gov-report` loses its "Unreviewed risky diffs" section.
- The sibling `feature_loop_probe.py` (decompose-side shadow) is **kept** — its question (does CODE
  overlap correlate with rework?) is genuinely open and it reads live agentlogs views with no
  separate accumulation log. Not the same fate; its comments were de-referenced from the deleted sibling.
- **Methodological precedent:** run the negative control before promoting ANY shadow/detector. Two
  confounded-correlation findings surfaced the same session (this + over_caution efficacy) — both
  would have read as real wins (47%, −71%) on the target metric alone. The control is the cheapest
  falsifier the loop owns.
