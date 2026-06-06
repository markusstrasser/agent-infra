# Claim-Bench RSI Program

Optimize only deterministic claim-verification support code.

Editable files:
- `../../claim_bench/src/claim_bench/scorer.py`
- `../../claim_bench/src/claim_bench/process_metrics.py`

Do not edit cases, tests, or this evaluator. The primary metric is the locked
aggregate from `uv run python3 eval.py --locked`, which includes deterministic parser
contracts, DOI/source extraction probes, and the existing claim-bench gold-case
schema audit.

Kept patches must also pass `uv run python3 eval.py --holdout`. Prefer small changes
that improve robustness without widening parsers so far that malformed judge or
model output is treated as valid evidence.
