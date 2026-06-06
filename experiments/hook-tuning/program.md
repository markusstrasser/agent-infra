# Hook Tuning RSI Program

Optimize `policy.py`, a small hook-policy decision function. The labels in
`cases.json` are a seed gold set, not telemetry truth. They encode current
governance judgments:

- high-volume low-correction advisories should narrow
- block-heavy overridden hooks should demote
- high-correction PreToolUse advisories may promote
- useful low-noise blocks should stay

Do not edit `cases.json` or `eval.py`. Kept patches must pass the locked dev +
holdout suite and should make the policy simpler or more robust.
