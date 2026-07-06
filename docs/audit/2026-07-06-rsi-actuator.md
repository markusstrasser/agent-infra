# RSI Resolution Actuator — 2026-07-06

STUB — see final return. The RSI loop over-produces ledger rows (predictions,
steward proposals, rsi-close) and under-consumes them; this adds the missing
DRAIN/SURFACE step to the existing pulse tick.

## Inventoried as ALREADY-EXISTING (do not rebuild)
- Predictions auto-resolve: `predictions.py cmd_auto_resolve` (proxy-free refute of
  reverted commits) IS wired — `register_implementations.py:121`, called by pulse
  tick `_phase_sense`. DUE predictions surface in the control-plane inbox via
  `pulse.py status` ("Predictions due" section) + `questions_view._collect_predictions`.
- So prediction surfacing + deterministic drain already run each tick. Gap: the tick
  STATE (last-tick.json) didn't carry a DUE count, so a tick reader didn't see it.

## Added
(filled in final return)
