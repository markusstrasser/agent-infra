---
id: 2026-06-15-voi-sequenced-review
concept: review-dispatch
repo: agent-infra
decision_date: 2026-06-15
recorded_date: 2026-06-15
provenance: contemporaneous
status: accepted
initial_leaning: "Run cross-model critique immediately on every design packet"
relations:
  - type: branches_from
    target: 2026-06-14-review-dispatch-consolidation
  - type: depends_on
    target: 2026-06-07-verifier-conditional-autonomy
  - type: depends_on
    target: 2026-06-07-state-externalization-lens
---

# 2026-06-15: VOI-sequenced review — scout uncertainty before adjudication

## Context

Markus's **VOI directive** (Value of Information sequencing) was cited in practice
(`improvement-log.md` 2026-06-14 context-budget sweep) but never persisted as load-bearing
architecture — only a dangling `[[feedback-sequence-for-information-gain]]` wikilink.

Critique dispatch now has: deterministic `review_gate` → cross-model adjudication →
`orchestrator-top.json` → Opus. Cross-model review on **unresolved forks** wastes tokens
reviewing premises that a 30-second grep or a Composer scout could have settled.

**Principle:** sequence work by **expected information gain per dollar/second** — cheap
broad scout → targeted probe → expensive adjudication only on residuals.

## Alternatives considered

1. **Skip VOI layer; rely on cross-model + verify** — status quo. *Con:* K2-class misses
   (GPT med CLEAN on subtle spec defect) and invented findings on unsettled premises.
2. **VOI scout via Composer before adjudication** (chosen) — one fork/variant at a time;
   propose probe or run if `<1min` deterministic. *Pro:* raises conviction before
   orchestrator; Composer is subscription-metered and good at repo-grounded falsification.
3. **Always run full replay grid before any design review** — eval-correct but operator-tax;
   belongs on routing promotion, not every packet.
4. **Human-only VOI** — ask Markus at every fork. *Con:* violates declining supervision +
   supervision test case ("principle of VOI right? #f why ask").

## Counterevidence sought

- **Would Composer scout duplicate `/code-review`?** No — code-review owns **diff** mechanics;
  VOI scout owns **one design premise** on a plan packet (callers exist? join key on both sides?).
- **Would `<1min` probes become silent scope creep?** Mitigated: only **deterministic**
  checks (grep, `--help`, read one file, `git log -5 -- path`); no new architecture in scout.
- **Does this recreate a `/review` router?** No — it's a **phase** inside `/critique` partial
  regime, not a competing skill. Partition ADR preserved.

## Decision

Adopt **VOI-sequenced review** as a mandatory phase in the partial-verifier pipeline.

### Sequence (partial regime — plans/designs)

```
1. triage          review_gate.py → dispatch.json (preset, blockers)
2. voi_scout       Composer 2.5 (optional skip if packet has no open fork)
3. adjudicate      model-review cross2/cross4 + --verify
4. integrate       rank → orchestrator-top.json; Opus reads top-N only
```

### VOI scout contract (Composer 2.5)

**Input:** one subpart packet + **one named fork** (or the load-bearing uncertainty the
orchestrator would otherwise guess at).

**Output:** `.model-review/<run>/voi-scout.json`:

```json
{
  "fork": "cross2 default vs cross4 on closeout",
  "uncertainty": "whether governance paths touched",
  "voi_actions": [
    {"action": "grep governance markers in packet", "cost_sec": 5, "disposition": "executed", "result": "..."},
    {"action": "run critique_replay probe on K2 arm", "cost_sec": 600, "disposition": "proposed"}
  ],
  "conviction_after": "high|medium|low",
  "recommendation": "proceed cross2 | escalate cross4 | human checkpoint"
}
```

**Rules:**

| Rule | Detail |
|------|--------|
| **One fork** | Scout reduces uncertainty on **one** variant/fork per pass — not a survey |
| **<1min → do** | Deterministic probe (grep/read/git log/help) — execute, attach result to packet |
| **≥1min → propose** | Write to `voi-scout.json`; do **not** block adjudication unless `conviction_after: low` AND irreversible |
| **No disposition** | Scout does not merge into `findings.json` — amicus only until verify |
| **Composer profile** | `composer-2.5` (not `-fast`); read-only + narrow grep; subscription pool |
| **Skip when** | `review_gate` blockers present; clear-verifier path (diff-only → `/code-review` only) |

### Where this connects to existing architecture

| Layer | Role |
|-------|------|
| **Explore** (`/brainstorm`) | Generate forks — non-binding |
| **VOI scout** | Cheap conviction on **one** fork |
| **Adjudicate** (`/critique`) | Cross-model + verify |
| **Integrate** | Opus + `integration_audit` |

Relates to context-budget sweep pattern: scout all → audit → vet → **high-VOI cuts only** → canary.

## Evidence

- `improvement-log.md` 2026-06-14 — VOI-sequenced context-budget sweep (applied, shipped)
- `scripts/tests/test_supervision_taxonomy.py` — "principle of VOI right? #f why ask"
- `decisions/2026-06-07-guardian-angels-transfer.md` — information-gain question scoring
- `decisions/2026-06-07-state-externalization-lens.md` — externalize recoverable probes
- `evals/critique_replay` probe — adjudication quality varies; premises matter
- Phenome pattern (domain): `genome → highest VOI test → measure` (`wgs-guide-full.md`)

## Revisit if

- Composer scout invents premises at >1 per 10 scouts → quarantine or drop scout phase
- Median scout latency >3min → tighten fork scope or move to propose-only
- `critique_replay` shows scout does not improve anchor detection on defective packets

## Supersedes

Dangling memory link `[[feedback-sequence-for-information-gain]]` — superseded by this ADR
as the canonical source.
