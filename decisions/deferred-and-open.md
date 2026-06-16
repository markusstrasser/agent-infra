---
title: Deferred & Open — decision forks not yet closed
date: 2026-06-16
status: living
---

# Deferred & Open

Forks deferred or left open by a `/decide` arc, with the trigger that reopens each. So nothing is
lost and nothing is re-proposed from scratch. Append; mark closed with the resolving commit.

## RSI loop closure (ADR `2026-06-16-rsi-unified-control-surface.md`)

| Item | State | Reopen trigger |
|---|---|---|
| `rsi weights` — precision-weight detectors | **DEFERRED** | ≥2 detectors clear the PPV gate (`reflect.PPV_CLEARED` non-empty with ≥2 families). Until then it's a weighting brain for ~1 input. |
| `rsi gate` axis-granularity rollup | **OPEN** (shipped at FM-ID granularity) | A promotion flow exists AND axis-level (reach/knowledge/capability) freezing is wanted — needs an FM-ID→axis join `fm.py` does not emit today. Probe the writer before building. |
| Label the 22 reflect omission firings | **OPEN — human (amplify lane)** | Anytime. `new-script-without-test`×9, `entity-write-without-identity-read`×6 lead. Clearing PPV≥60% graduates a detector → then `weights` reopens. |
| `v_tool_friction` closure back-edge (Jun-8 plan Phase B) | **OPEN** (planned, never shipped) | If the supervision-side closure (AIR + canary) proves insufficient and tool-friction-by-project is still wanted. Was descoped to doctor.py; grep shows neither shipped. |
| MAST detectors: reasoning-action-mismatch, information-withholding | **OPEN** (logged improvement-log 2026-06-16) | A real instance shows in sessions (not yet recurrence-gated). |
| Auto-inject write-stub in `pretool-subagent-gate.sh` (vs block) | **OPEN** | Confirm PreToolUse can mutate `Agent` input on this CC version. Keeps the #47936 guard, kills the re-author friction. |

## Critique audit trail
- `.model-review/rsi-arch-opus.md` · `rsi-crosslab-gpt.md` · `rsi-factcheck-composer.md` (2026-06-16).
  Partial spine reversal: ship canary, defer the promotion brain. All load-bearing claims verified
  against code before folding.
