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

## Probed — NOT RSI-ready (verifier gap, do not re-derive)

Candidates probed and rejected because the **verifier**, not the mutable surface,
is missing. Both have a deterministic editable surface; neither has an
optimization-grade verifier (closed-loop + numeric metric + holdout big enough to
hold out). The mutator is never the bottleneck — the gold-backed verifier is
(`decisions/2026-06-03-verifier-bound-autonomy.md`).

| Candidate | Editable surface | Why blocked (probed 2026-06-07) |
|-----------|------------------|-------------------------------|
| intel entity-resolution | `intel/tools/build_entity_resolution_map.py:merge_record` | **Open-loop + tiny gold.** `intel/tools/evals/er_eval.py` reads a *static* `xwalk` table — editing the resolver doesn't move the metric. Closing the loop means rebuilding 1.3M xwalk rows / 739K entities over a 2.2 GB DuckDB (Splink) per mutation — infeasible at 45 s/eval. And the gold is 47 hand-labeled pairs (a regression canary, not an optimization set; no real holdout). |
| corpus reference-resolution | `corpus_core/resolve_references.py` | **Closed-loop but no metric dataset.** `test_resolve_references.py` runs the real functions (closed-loop ✓) but is **9 hand-written contract assertions**, not a labeled P/R dataset over many papers with a holdout. No optimization gradient (all 9 already pass), nothing to hold out. |

To promote either: build the labeled, holdout-able metric dataset first (human
labeling is the gate), then a *scoped* closed-loop eval (run only the editable fn
over the labeled subset — never rebuild the full pipeline).

## Operating rule

Do not treat telemetry as gold. If an eval is based on hook logs, session traces,
or context usage, label that split as seed/silver until a human-labeled holdout
exists. Autoresearch can aggressively mutate scorer/router code only when the
locked evaluator measures behavior we actually want.
