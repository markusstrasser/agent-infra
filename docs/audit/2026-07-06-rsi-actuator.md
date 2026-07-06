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
- `scripts/steward_reconcile.py` + `scripts/tests/test_steward_reconcile.py` +
  `just steward-reconcile` — deterministic LOCATE of open steward proposals whose
  artifact already shipped. Signals: (0) proposal cites a hook/script sharing a slug
  token that exists on disk (userprompt-clock); (1) same-intent file in implemented/;
  (2) slug-token match to a shipped basename. Report-only — never moves/edits/closes;
  the human reads the cited source to DECIDE. Live: **22/70** flagged (triage found
  26/71 already-done+stale; the 4 delta are date-STALE, not artifact-exists).
- Wired `reconcile()` + DUE-predictions count into `pulse_tick._phase_drain` (tick
  STATE now carries `steward_reconcile_candidates` + `predictions_due_count`) and into
  `pulse.py gather_status`/`render_status`/`status_needs_attention` (control-plane inbox
  gets a "Steward reconcile" section; needs_attention trips on candidates).

## Not rebuilt (already existed)
- Prediction auto-resolve + DUE surfacing already run each tick (see above). The only
  prediction gap was the tick STATE not carrying the DUE count — now added.

## Precision note
Tightened from a naive "cites any existing file" (42/70, many false positives like a
proposal citing an unrelated hook it modifies) to "cites a file sharing a slug token"
(22/70). Test `test_cited_unrelated_file_is_not_flagged` guards the regression.
