---
id: 2026-05-31-skillopt-not-institutionalized
concept: skill-optimization
repo: agent-infra
decision_date: 2026-05-31
recorded_date: 2026-05-31
provenance: contemporaneous
status: accepted
initial_leaning: "Prototype SkillOpt on a scored skill; if it lifts accuracy, consider adopting it to auto-optimize verifiable skills."
relations:
  - type: cross_repo_of
    target: evals/docs/findings/skillopt_claim_verification_probe_2026-05-31.md
---

# 2026-05-31: SkillOpt is an opportunistic tool, not standing infrastructure

## Context

SkillOpt (github.com/microsoft/SkillOpt) optimizes a skill markdown via bounded LLM-proposed edits,
accepting one only if it strictly beats a held-out selection score (validation gate). Prior memory note
([[skillopt-vs-autobrowse-veto]]) flagged the open question: optimize our *existing* scored skills with
this loop? Gating fact = it needs an automatic verifier. We probed it on claim verification (the one task
with a deterministic oracle, using the `evals` benchmark), opus-4-8 as optimizer+target.

## Alternatives considered

1. **Institutionalize** — standing eval + optimization loop maintained across verifiable skills. Pro:
   automates prompt iteration. Con: benchmark drift, re-validation per model upgrade, loop infra — the
   exact ongoing maintenance the constitution's "filter by maintenance, not effort" gate guards against.
2. **Opportunistic one-off (chosen)** — keep a frozen builder + harness; run only when a skill has a
   deterministic oracle, ≥100 clean cases, the prompt underperforms, AND a model upgrade forces revalidation.
3. **Abandon** — declare it not worth it at all. Rejected: the probe showed a real, evidence-grounded lift.

## Counterevidence sought

To reverse the "opportunistic, not infra" leaning we deliberately tested whether the win was *real and
general* enough to justify infrastructure: (a) a contamination probe (claim-only, no evidence) to rule out
that opus was recalling the public AVeriTeC labels — it collapsed to chance (0.231), so the +23pt is
evidence-driven, real; (b) a cross-model design review (GPT-5.5, free via codex sub) explicitly asked
"is this worth institutionalizing?" — it independently said NO and set a high flip bar (≥3 skills, ≥500
held-out cases, repeated ≥5-8pp over naive, no per-dataset regressions, survives a model swap). We did NOT
find evidence meeting that bar: N=26, single run, AVeriTeC-specialized, packets fact-checker-derived
(leakage axis per evals `contamination_audit_2026-05-12.md`), transfer untested. So the leaning held.

## Decision

**Do not build standing infrastructure around SkillOpt.** Treat it as a validated opportunistic
prompt-search trick for skills that have a deterministic, contamination-controlled oracle. The probe
result (seed 0.615 → learned 0.846 held-out, contamination-clean; hand-tuned judge_v1 = 0.769) is
recorded but is directional only at N=26. Reusable assets (dataset builder, evaluator, contamination
probe, learned-skill artifact) promoted to `evals/scripts/skillopt/`; full result in the cross-referenced
finding. This confirms, not reopens, the related point that open-ended skills (brainstorm) stay
instruction-driven — they lack the safe oracle that made this probe legitimate.

The `claude_chat` backend in SkillOpt needed 3 fixes for current Claude CLI (stdin redirect; an
`--output-format json` array-parsing bug that silently produced empty responses / a fake 0-score; and
dropping the credit-exhausted `ANTHROPIC_API_KEY` to use the OAuth sub) — documented in the evals README
so a future run doesn't rediscover them.
