# Proposal: retire the risky-diff-review shadow detector (gov-shrink)

**Date:** 2026-06-24 · **Class:** governance deletion (agent-infra-local) → human sign-off · **Risk:** low (report-only detector; fully reversible via git revert)
**Source:** maintain tick — disposing the `[2026-06-07] SHADOW: risky-diff-review` finding past its promote/cut date

## Decision already made (autonomous, in improvement-log)

The shadow's binary question — *"build an auto-review gate for unreviewed-risky diffs, y/n?"* — is answered **NO**, on a controlled measurement (this is the resolved part; it needs no sign-off):

- **Correlation half FALSIFIED by negative control.** Over the full 192-row log (2026-05-08→06-20): 9/19 (47%) review-worthy commits had a later fix touching their files — but 14/30 (47%) NON-flagged commits to the same high-churn dirs did too. **Identical.** The flag has zero discriminative power; 47% is file-churn baseline, not a risk signal.
- **Premise already disconfirmed:** self-review degeneracy did not reproduce on Opus 4.8 (`decisions/2026-06-03-verifier-bound-autonomy.md`).

## What needs YOUR sign-off (the deletion)

The detector's named consumer (the promote decision) is now resolved, so it is generation-without-consumption going forward. Per gov-id telos (a scaffold earns its place only while it's load-bearing), retire the infra:

| Delete | Why |
|---|---|
| `scripts/risky_diff_review_shadow.py` | the detector; question answered |
| `scripts/risky-diff-review-oneshot.sh` | its runner |
| `scripts/tests/test_risky_diff_review_shadow.py` | tests for deleted code |
| `just risky-diff-shadow` / `risky-diff-report` recipes | no consumer |
| the `risky_diff` block in `gov.py` report | no consumer |
| `~/.claude/risky-diff-shadow.jsonl` + `risky-diff-review-done` | 53KB of answered-question data (archive or drop) |

**Reversible:** git revert restores all of it; the 53KB log can be archived to `2TBPNY` first if you want the raw data kept.

## The one reason to KEEP it instead (defensible)

It's cheap (one gov.py function + report-only). If the operating regime changes — a weaker model takes over more autonomous work, or self-review degeneracy starts reproducing — the data is already flowing and the promote decision could be revisited with fresh evidence. If you value that standing option over the complexity-surface saving, **keep-as-canary** and just mark the finding decided (already done). My lean is **retire** (the telos: don't carry scaffolds whose question is answered), but the keep case is real, so it's your call.

## Dedup

- Not on vetoed-decisions; not previously proposed.
- This is the symmetric partner to the over_caution ablation candidate logged the same session — both are gov-shrink dispositions of confounded-benefit detectors, surfaced by running the negative control the loop should run before promoting any shadow.
