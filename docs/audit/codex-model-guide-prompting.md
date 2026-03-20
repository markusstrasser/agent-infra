Report written to [model-guide/audit-prompting.md](/Users/alien/Projects/skills/model-guide/audit-prompting.md).

Highest-signal issues:
- `PROMPTING_GPT.md` still uses stale Responses-era guidance in a few places: `response_format` instead of `text.format`, manual `strict: true` as if Responses were not strict-by-default, unsupported 24h cache-retention claim for GPT-5.4, and missing `original` image detail.
- `PROMPTING_GEMINI.md` has the clearest factual errors: wrong llmx model name for Pro, wrong claim that Pro supports `thinkingLevel: medium`, stale `75%` cache discount, and no Flash-Lite coverage.
- `PROMPTING_KIMI.md` is the most drifted on model variants and stale GPT comparison numbers.
- `SKILL.md` inherits several stale/speculative tips and has no full-guide backing for GPT-5.3 Instant or Gemini 3.1 Flash-Lite.

The report includes per-file findings with categories, `file:line` citations, the SKILL cross-reference, and a markdown summary at the end.