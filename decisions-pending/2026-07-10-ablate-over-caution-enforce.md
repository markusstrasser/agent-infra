# Ablation: over_caution smart-judge enforce → shadow (2026-07-10)

**Status:** APPLIED (reversible) — user directed `/improve` DO ALL on observe dossier backlog.

## What changed
- `~/.claude/settings.json` `SMART_JUDGE_ENFORCE_VECTORS`: removed `over_caution`
- Left: `verify_before_claim` still enforce
- `SMART_JUDGE_MODE` remains `enforce` (other vectors)
- `over_caution` still **classified** in shadow (Stop smart-judge still scores it; just doesn't re-prompt)

## Why
- improvement-log `[obs] 2026-06-24`: enforce graduation CONFOUNDED — target metric fell with all controls
- Measured cost: 27–38s latency on flagged turns + metered haiku fast-path
- Blindspot still shows over_caution 14/7d under enforce — coverage ≠ efficacy
- Dossier wild-card: closure via ablate, not new detectors

## Pre-registered measure (14d)
| Metric | Source | Pass if |
|--------|--------|---------|
| typed over_caution/day | `supervision-kpi.py --days 14` | flat or ↓ vs pre-ablation baseline (~1.3/day from 9/7d) |
| control: rediscovery/day | same | does not spike >2× |
| Stop re-prompt latency | hook-trigger `smart-judge` | fewer enforce fires for over_caution |

**Baseline window:** 2026-07-03→10 (observe run 1514): over_caution=9, rediscovery=7.

**Control hygiene (Opus 2026-07-10):** prior-context REDISCOVERY keyword tune was drafted then **reverted** so it cannot confound this ablation's rediscovery control. Do not ship rediscovery-touching changes until this 14d window closes.

## Rollback
Restore `"SMART_JUDGE_ENFORCE_VECTORS": "verify_before_claim,over_caution"` in `~/.claude/settings.json`.

## Non-goals
- Do NOT delete the over_caution classifier vector
- Do NOT add a replacement timidity hook until this ablation reports
- Do NOT ship DEFAULT parallel-fan-out in the same window (Opus: ablation first, then loosen)