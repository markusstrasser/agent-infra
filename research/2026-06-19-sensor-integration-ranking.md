# Sensor integration ranking — 2026-06-19 (deterministic)

## Top 3
1. **humanmd-template-aware-grep** — HUMAN.md template-aware open-count grep (don't match the template example header) | autonomy: human-gate (shared) | gate: script
2. **prior-context v2 / existing_infra** — rediscovery=85 dominates blindspot | autonomy: tier-0 | gate: prior_context_triage ship slice

## Deferred
- Full RSI rebuild (field converged on our arch)
- integrate-rank LLM path (deterministic default; use `--synthesis` to opt in)

## Noise dropped
- Retired maintain candidates (`done: true`)

_Sensors excerpt:_
```
# Integration rank inputs — 2026-06-19
_window: blindspot 7d digest excerpt; funnel live_

## Blindspot digest
# Blindspot misses — 2026-06-19 13:30 (last 7d)

**164 corrections the human had to make** (of 2886 candidates), classified by the direction each implies:

- **GROW_COVERAGE (agent missed context → add detector)** — 85  (rediscovery=85)
- **RAISE_AUTONOMY (agent was timid → loosen/act more)** — 59  (over_caution=59)
- **REDUCE_ERROR (agent was wrong → correctness guardrail)** — 20  (error_correction=20)

By project: agent-infra=37, genomics=35, phenome=27, hutter=19, evals=11, substrate=11, anim-workbench=10, personal=3, research=3, -private-tmp=2, synthoria-bio=2, phenome--claude-worktrees-ancient-marinating-rain=2, arc-agi=1, intel=1

Top flags (sorted by confidence):

- `+1.00` [over_caution/regex] **evals/1c861d57** (2026-06-18): Alrigt did you fix the bugs? 1 ok do? if it's a real bug and you know it ... why not fix it?"? 2 run for what exactly? what task/e
- `+1.00` [over_caution/regex] **evals/ec7d18f6** (2026-06-15): Yeah obviously you want the semantic judge. You can not just do string matching; that's stupid. You can do the items; do whatever 
- `+1.00` [rediscovery/regex] **evals/ec7d18f6** (2026-06-15): A session-scoped Stop hook is now active with condition: "the abvoe ... until really you can't think of a domain that you didn't c
- `+1.00` [over_caution/regex] **evals/49301cbc** (2026-06-16): then /research a bunch ... and /decide on what you can do / integraet
- `+1.00` [over_caution/regex] **-private-tmp/9db71d76** (2026-06-13): You classify ONE message from a human operator (Markus) to his agent system (a Hutter-Prize compression RSI loop: observer/dreamer
- `+1.00` [over_caution/regex] **synthoria-bio/bbb56fe6** (2026-06-17): This intake form is for markus in genomics results I will give it to genomics agent's to QC and check the resulting artifacts ... 
- `+1.00` [rediscovery/regex] **synthoria-bio/bbb56fe6** (2026-06-17): So.... why don't you check the research inside Projects/genomics ... which you cearly DIDNOT do ... this is about validating what 
- `+1.00` [over_caution/regex] **phenome/adfa97e4** (2026-06-14): why not do slice 3 now? did things change?
- `+1.00` [over_caution/regex] **phenome/adfa97e4** (2026-06-15): Any questions for me ? or why waiting lazily?
- `+1.00` [rediscovery/regex] **phenome/adfa97e4** (2026-06-16): Yeah on Cloud agents in just egress pj, that's the user's decision if they want to trust Claude Code or they use a local agent so 
- `+1.00` [over_caution/regex] **phenome/adfa97e4** (2026-06-16): #f WHY are you asking for a probe? Probes are always yes ... VOI ... no harm ... etc
- `+1.00` [error_correction/regex] **phenome/adfa97e4** (2026-06-17): no stop ... never use opus or ggpt in cursor
- `+1.00` [error_correction/regex] **phenome/adfa97e4** (2026-06-17): no stop ... never use opus or ggpt in cura
- `+1.00` [error_correction/regex] **phenome/adfa97e4** (2026-06-17): no stop ... never use opus or ggpt in cursor .. .lways the native model composor 2.5 .... !!!!
- `+1.00` [rediscovery/regex] **phenome/a138bfef** (2026-06-14): Ok ... coool>> do all if strictt wins ... longterm. also /research .. did you read the full paper? ANd your conclusions /critiuqe?
- `+1.00` [error_correction/regex] **phenome/05335ab9** (2026-06-11): No it's not about shipping ... I just want it to be done and ready to actually have a research agent fill it up without later havi
- `+1.00` [over_caution/re…
```
