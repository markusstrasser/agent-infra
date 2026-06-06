# claim-bench

Claim-verification benchmark built on `inspect_ai` (UK AISI). Domain-neutral package; consumers (genomics, selve, research skill) plug in their own corpora and verdict-translation layers.

**Plan:** [PLAN.md](./PLAN.md) — phases, vetoed approaches, open gaps, package boundary
**Prior art:** `~/Projects/agent-infra/research/claim_verification_package_prior_art_2026-04-11.md` — consume inspect_ai + FIRE-Bench verdict
**Apr 10 paper scan:** `~/Projects/agent-infra/research/agent_harness_scientific_truth_review_2026-04-10.md` — VeRO/FIRE-Bench/AutoVerifier/Meta-Harness/SciNav

## What this answers

> Given a claim and an allowed tool surface, can the system find the right evidence, classify the claim correctly, surface contradictions, and abstain honestly when support is insufficient?

Five verdict classes:
- `supported` — evidence directly backs the claim
- `contradicted` — evidence directly refutes the claim
- `mixed` — both supporting and contradicting evidence exists
- `insufficient_evidence` — claim is verifiable in principle but no evidence found
- `not_verifiable` — claim is rhetorical, opinion, or underspecified

## Why inspect_ai

Per `research/claim_verification_package_prior_art_2026-04-11.md`: inspect_ai's `Task` / `Sample` / `Solver` / `Scorer` types ARE the benchmark contract. We don't rebuild it. We add custom scorers for the gaps inspect_ai doesn't ship (groundedness, calibration, trace faithfulness, atomic-claim P/R/F1).

## Layout

```
claim_bench/
├── README.md           # this file
├── src/claim_bench/
│   ├── task.py             # inspect_ai Task entrypoint
│   ├── scorer.py           # verdict-enum + groundedness scorers
│   ├── tools.py            # retrieval @tool wrappers
│   ├── process_metrics.py  # source/currency/calibration helpers
│   ├── atomic_claim.py     # atomic claim parsing and matching
│   └── cards.py            # independence + adequacy card derivation
├── cases/              # gold cases (cross-domain seed)
├── tests/              # deterministic unit/contract tests
├── logs/               # saved inspect eval logs
└── LEARNINGS.md        # what worked, what didn't, schema gaps
```

## Run it

```bash
cd ~/Projects/agent-infra
PYTHONPATH=claim_bench/src uv run python3 -m pytest claim_bench/tests
uv run inspect eval claim_bench/src/claim_bench/task.py
```

The pytest suite is the cheap deterministic contract. The `inspect eval` command is the live model/tool integration path.

## RSI eval

The recursive-improvement harness for deterministic claim-bench code lives in
`experiments/claim-bench-rsi/`. It is allowed to mutate only:

- `claim_bench/src/claim_bench/scorer.py`
- `claim_bench/src/claim_bench/process_metrics.py`

Run it with:

```bash
uv run python3 experiments/claim-bench-rsi/eval.py --locked
```

This eval uses the 30 authored/imported cases plus parser and source-extraction
probes. On 2026-06-06 it exposed a real parser failure: markdown output
`**not verifiable** ...` was parsed as `not`. Commit `d3110e0` fixed that in
`scorer.py`, moving the locked RSI score from `0.975000` to `1.000000`.

## Status

- **Gold cases:** 30 cross-domain cases in `claim_bench/cases/`
- **Verdict scorer:** implemented and covered by deterministic tests
- **Groundedness scorer:** implemented; live judge calls require API access
- **Process metrics:** implemented with deterministic unit tests
- **Atomic claim P/R/F1:** implemented with deterministic unit tests
- **Independence/adequacy cards:** implemented with deterministic unit tests
- **Phase 5 (genomics adapter):** not started
- **Phase 6 (extract package):** trigger = second consumer appears

## Conventions

- Cases are JSON, one per file, named `NNN_<verdict>_<slug>.json`
- Each case has: `task_id`, `claim_text`, `domain`, `claim_type`, `gold_verdict`, `gold_sources`, `notes`
- Cases live cross-domain initially (CRISPR / vitamin C / etc.) so the schema is stress-tested before genomics-specific corpora arrive in Phase 5
- No genomics imports anywhere in this directory — domain-specific code lives in domain adapters
