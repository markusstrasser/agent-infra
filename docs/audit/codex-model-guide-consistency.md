The audit is written to [audit-consistency.md](/Users/alien/Projects/skills/model-guide/audit-consistency.md).

Summary:
- `1` MISMATCH: `Claude Sonnet 4.6` is labeled `1/5 cost`, but the benchmark pricing table shows `$3/$15` vs Opus `$5/$25`, so it is 60% of Opus pricing, not 20%.
- `4` DRIFT items: `Professional analysis` picks Opus even though `GDPval` favors Sonnet; `Hard math` picks GPT-5.4 alone even though BENCHMARKS marks a GPT/Kimi tie; `Computer use / browsing` collapses two tasks even though browsing favors Gemini and computer use favors Opus; `SKILL.md` says last updated `2026-03-07` but `CHANGELOG.md` stops at `2026-03-06`.
- `8` INCOMPLETE items: `ARC-AGI-2 TBD` remains in `SKILL.md` despite a `52.9%` benchmark entry; `GPT-5.4` max output is still `TBD`; `DocVQA 95%+` for GPT-5.4 is not represented in `BENCHMARKS.md`; `GPT-5.3 Instant`, `Gemini 3 Flash`, and `Gemini 3.1 Flash-Lite` are in the skill but missing from BENCHMARKS; `GPT-5.4 + web search ~95%+` has no benchmark entry; the changelog never records when those extra models were added.
- `0` STALE items: nothing crossed the `>14 days` threshold as of `2026-03-20`.

No tests were run; this was a document consistency audit only.