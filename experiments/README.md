# Experiments

Small, bounded eval surfaces live here. These are not broad product areas; each
experiment should expose a mutable file, a deterministic evaluator, and a
holdout gate before it is handed to `scripts/autoresearch.py`.

## RSI-ready surfaces

| Experiment | Mutable surface | Eval | Current purpose |
|------------|-----------------|------|-----------------|
| `skill-routing/` | `scripts/skill-routing.py` | `python3 eval.py --locked` | Route prompts to the right skills/modules across canonical, stress, and holdout cases. |
| `claim-bench-rsi/` | `claim_bench/src/claim_bench/{scorer,process_metrics}.py` | `uv run python3 eval.py --locked` | Improve deterministic claim-verification parsing and source-extraction logic. |
| `hook-tuning/` | `policy.py` | `python3 eval.py --locked` | Seed gold set for hook policy decisions: keep, narrow, promote, demote. Needs more labels before serious optimization. |
| `context-packing/` | `packer.py` | `python3 eval.py --locked` | Seed context-selection policy under a small budget. Needs replay-derived labels before serious optimization. |
| `proposal-ranker/` | `ranker.py` | `python3 eval.py` | Pairwise ranking of proposed work items. |
| `toy-scorer/` | `scorer.py` | `python3 eval.py` | Minimal autoresearch smoke surface. |

## Operating rule

Do not treat telemetry as gold. If an eval is based on hook logs, session traces,
or context usage, label that split as seed/silver until a human-labeled holdout
exists. Autoresearch can aggressively mutate scorer/router code only when the
locked evaluator measures behavior we actually want.
