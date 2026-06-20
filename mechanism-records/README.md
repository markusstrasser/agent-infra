# mechanism-records/

Git-tracked **predict-then-falsify** records (F3). One JSON per governance change
whose justification is a behavioral claim. The gate (`scripts/mechanism_record.py`)
accepts a change only if its pre-registered mechanism *fired* against agentlogs.db,
with a negative control that stayed flat.

Schema + verdicts + when-required: `.claude/rules/predict-then-falsify-gate.md`.

```bash
uv run python3 scripts/mechanism_record.py list           # records + last verdict
uv run python3 scripts/mechanism_record.py check <slug>   # re-run the gate
```

`example-*.json` records are schema illustrations / pipeline validations — they may
bind to a generic signal and do not assert a governance result. Real gates cite a
real `change_ref` and a metric scoped to the failure they claim to reduce.
