---
id: 2026-06-20-dynamics-decay-salience-no-build
date: 2026-06-20
status: decided
relates_to:
  - 2026-06-07-state-externalization-lens
tags: [rsi, salience, anti-over-build, mempalace]
---

# Decay-weighted salience for the RSI/decision graph — NO-BUILD

## Decision
Do **not** build a Hebbian-potentiation + Ebbinghaus-decay + Cepeda-spacing "salience" score
for ranking decisions/findings (the one transplantable idea from the MemPalace eval — its
`dynamics.py`). A read-only Pre-Build ablation killed it. If salience ranking is ever wanted,
the answer is a **one-line sort by `days_since_last_touch`**, not a decay engine.

## Why (the ablation, N=62 decisions/)
Touch stream = `git log --follow` commit timestamps per `decisions/*.md` (the only co-access
signal available). Three rankings compared: recency-only · recency+log(freq) · full-dynamics.

- **No data for the mechanism:** 29/62 decisions touched exactly once ever; only **17/62**
  touched on >1 distinct day. The repeated, spaced co-access that Hebbian/spacing models
  requires barely exists in this corpus.
- **Floor saturation:** with the MemPalace constants, `exp(-days/stability)` floors at 0.05 for
  anything older than ~4 days; decisions move weekly–monthly, so ~45/62 tie at the floor and
  their dynamics-rank is stable-sort tie-break noise. Even the genuine spacing candidates
  (`2026-03-17-shared-knowledge-substrate` 6 events, `2026-05-26-cross-attestation-v2` 3) floor.
- **Result:** Spearman(recency, dynamics) = 0.04 but **top-10 overlap = 10/10** — the head ranks
  identically to recency; only the floored tail "disagrees," and that's noise, not the spacing
  effect. recency+freq ≈ recency (Spearman 0.994).
- **The deeper kill (constant-independent):** git captures *edits*, not *reads*. The read-stream
  the full model wants does not exist in our data; retuning constants cannot model reinforcement
  that never happened.

## Consumer gap is real, fix is trivial
`top_priorities.py:144,167` does flat-rank pending-decisions (80) and findings (60) with no time
signal — a real gap. But the right fix is one sort key (`days_since_last_touch`), not a salience
engine. No new store, no decay state, nothing to maintain (state-externalization lens).

## Resurrection trigger
Only if decision/finding files start being **co-accessed across many distinct days** (ndd>1 for a
clear majority) — i.e. a real read/touch event stream comes to exist. Re-run the ablation
(`.claude/plans/dynamics-decay-P0-ablation.md`) to check. "Retune the constants" is NOT a valid
resurrection path — the kill is missing data, not parameter choice.

## Provenance
Idea source: MemPalace `dynamics.py` (see memory `mempalace-evaluated-emb-at-parity`). Scope:
`.claude/plans/2026-06-20-dynamics-decay-salience.md`. Ablation: `.claude/plans/dynamics-decay-P0-ablation.md`.
