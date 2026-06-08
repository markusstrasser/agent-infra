---
description: Gov-ID annotation schema + governance lifecycle verbs for the gov-shrink loop
paths:
  - ".claude/rules/**"
  - "scripts/*.py"
  - "improvement-log.md"
---
# Gov-ID — governance scaffold annotation

<!-- Gov-ID: rule:gov-id
goal: document the gov-shrink annotation contract and lifecycle verbs
verifier: null
blast_radius: local
-->

Every governance scaffold (rule, hook) is **temporary** — it earns its place only
while the model still fails its goal's verifier without it. As model capability
rises, `gov-shrink` re-runs the verifier with the scaffold removed; if the grader
still passes, the scaffold was training wheels and is proposed for retirement.
Goals + verifiers are durable; rules are not. Telos: the governance corpus
**shrinks** as IQ rises. Report: `just gov-report` (read-only; markdown/git is
authoritative — there is no governance DB).

## The Gov-ID block

Markdown rule files — HTML comment after the `# Title`:

```
<!-- Gov-ID: rule:<slug>
goal: <one line — the failure this prevents>
verifier: <evals/graders/governance/<name>.py | null>
blast_radius: <style|local|shared|constitution>
-->
```

Python hooks — comment lines after the module docstring:

```
# Gov-ID: hook:<slug>
# goal: ...
# verifier: ...
# blast_radius: ...
```

- **goal** — what it prevents, one line. If you can't state a goal, it may be theater.
- **verifier** — a ground-truth-bound grader in `evals/graders/governance/` (never an
  LLM-judge — leniency bias scales with capability). `null` = not yet capability-testable
  → it's on the generative backlog (write the verifier).
- **blast_radius** — sets the apply-gate tier:
  - `style` — format/naming; excluded from shrink, never auto-acts.
  - `local` — meta-only; eligible for earned-autonomy auto-retirement once a track record exists.
  - `shared` — affects 3+ projects; human-gated.
  - `constitution` — constitution/GOALS; human-gated, ≤1 proposal/week.

## Lifecycle verbs (improvement-log.md)

Append-only; mark state, never delete:

- `[ ]` proposed · `[x]` implemented (existing)
- **`[~]` retired** — scaffold removed because its verifier passes without it (or it
  decayed). Cite the verifier verdict or decay evidence.
- **`[>]` superseded-by `<id>`** — replaced by another artifact; link it.
- **`[obs]` behavioral observation** — an append-only calibration-ledger entry (TOKEN WASTE,
  SYCOPHANCY, MISSING PUSHBACK, REASONING-ACTION MISMATCH, OVER-ENGINEERING…). Consumer is
  recurrence→rule promotion, NOT per-item implementation — it can never be `[x]`. **Never tag a
  behavioral finding `[ ]`** (that inflates the actionable-open count into a panic number; F1
  2026-06-08). When a rule ships covering a class, bulk-mark its contributors `[>]` superseded-by.
- **`[-]` rejected** — decided not to do (one-off, low-severity, or out of scope).

**`[ ]` is reserved for genuinely-actionable, still-open infra/tooling/architecture work** —
the only stream "drain the backlog" applies to, and the only one `gov-report`/`doctor` should
count. Two streams, one file: the behavioral ledger (`[obs]`, mined for recurrence) and the
actionable queue (`[ ]`→`[x]`). Backfill tool: `scripts/reclassify_improvement_log.py`.

The subtract verb is the point: governance that only grows is a ratchet. `gov-report`
surfaces retirement candidates (decayed advisories, shrink-eligible scaffolds); a
human (or, for `local`+high-confidence+zero-reverts-14d, earned autonomy) applies the diff.
