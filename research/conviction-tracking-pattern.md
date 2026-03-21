# Conviction Tracking Pattern

Research memo documenting the cross-project pattern for structured belief tracking.

## Source

Intel's `conviction-schema.md` — the most mature implementation. YAML entries in entity
frontmatter track prior/posterior states, triggers, evidence, KL divergence, resolution observables.

## Universal Structure (domain-agnostic)

The pattern has six components that work in any domain:

1. **Immutable append-only entries** — once committed, never edited. Corrections get new entries.
2. **Prior/posterior explicit** — state what you believed before AND after the update.
3. **Trigger documented** — what evidence or event prompted the update.
4. **Evidence with source grade** — every claim linked to a verifiable source.
5. **Resolution observable** — specific, falsifiable: "Revenue >= $2.7B" or "ClinVar reclassifies to pathogenic."
6. **Horizon** — when the prediction resolves. Without this, you cannot score calibration.

## Domain-Specific Vocabulary

The power is in domain-specific terms. Do NOT try to unify these.

| Component | intel | genomics | meta |
|-----------|-------|----------|------|
| States | BUY/HOLD/AVOID/RESEARCH/WATCHLIST | PATHOGENIC/VUS/BENIGN/LIKELY_P/LIKELY_B | ADOPT/DEFER/REJECT/EXPERIMENTAL |
| Actions | initiate/add/hold/trim/exit/watch | classify/reclassify/defer/flag | implement/propose/revert/measure |
| Resolution | Market price, earnings, events | ClinVar reclassification, functional study | Session-analyst detection rate, hook ROI |

## Blind First-Pass Protocol (from intel)

When updating existing analysis with new evidence:
1. Read new evidence WITHOUT reading prior analysis.
2. Form independent assessment.
3. Then compare to prior. Document divergence explicitly.

## Calibration Connection

Intel's conviction entries include `resolution:` and `horizon:` — this makes the journal
a calibration data source. Meta's `calibration-canary.py` could accept conviction_journal
as a signal source (higher cadence than spot-check predictions).

## KL Divergence

Intel computes `KL(posterior || prior)` on scenario distributions to quantify update magnitude.
Formula: `sum(p_i * ln(p_i / q_i))` with 0.001 floor. Useful for detecting anchoring bias
(KL near zero despite material evidence) or overreaction (KL disproportionate to evidence strength).
