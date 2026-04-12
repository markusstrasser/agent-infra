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
experiments/claim-bench/
├── README.md           # this file
├── task.py             # inspect_ai Task entrypoint (Phase 0)
├── scorer.py           # verdict-enum + atomic-claim scorers
├── tools.py            # retrieval @tool wrappers (Phase 1+)
├── process_metrics.py  # groundedness / calibration / trace faithfulness (Phase 2)
├── cards.py            # independence + adequacy card derivation (Phase 4)
├── cases/              # gold cases (cross-domain seed)
│   ├── 001_supported_crispr_2015.json
│   └── 002_contradicted_vitamin_c_cold.json
├── runs/               # eval outputs (gitignored)
└── LEARNINGS.md        # what worked, what didn't, schema gaps
```

## Run it

```bash
cd ~/Projects/agent-infra
uv sync                                        # install inspect_ai if missing
uv run inspect eval experiments/claim-bench/task.py
```

(Phase 0 task runs against a placeholder solver — proves the harness shape, not the model.)

## Status

- **Phase 0 (probe):** in progress — task.py + 2 cases + verdict scorer
- **Phase 1 (real solver):** not started
- **Phase 2 (process metrics):** not started
- **Phase 3 (atomic claim P/R/F1):** not started
- **Phase 4 (cards):** not started
- **Phase 5 (genomics adapter):** not started
- **Phase 6 (extract package):** trigger = second consumer appears

## Conventions

- Cases are JSON, one per file, named `NNN_<verdict>_<slug>.json`
- Each case has: `task_id`, `claim_text`, `domain`, `claim_type`, `gold_verdict`, `gold_sources`, `notes`
- Cases live cross-domain initially (CRISPR / vitamin C / etc.) so the schema is stress-tested before genomics-specific corpora arrive in Phase 5
- No genomics imports anywhere in this directory — domain-specific code lives in domain adapters
