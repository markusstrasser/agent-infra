# Cross-Model Review: Context Bundling Infrastructure
**Mode:** Review
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (CLAUDE.md Constitution, GOALS.md)
**Extraction:** 23 items extracted, 15 included, 4 deferred, 1 rejected, 3 merged

## Key Insight (Both Models Converge)

SessionEnd regeneration is self-defeating for caching. If you regenerate views after every session and do ~1 review per session, cache hit rate = 0%. Formalized: hit rate = (r-1)/r where r = reviews per unchanged prefix.

**Fix:** Anchor stable base to HEAD (last commit), not session-end. Only rebuild when HEAD changes. Send working-tree diffs as the variable suffix.

## Verified Findings (adopt)

| ID | Finding | Source | Verified How |
|----|---------|--------|-------------|
| G1+P1 | SessionEnd regen contradicts caching goal | Both | Formal: r=1 → 0% hits |
| G4+P6 | Cache keys are fragile — determinism is prerequisite | Both | Timestamps/ordering break byte-identity |
| G6 | JIT (Make/Justfile) > blind pre-computation | Gemini | Solves freshness without waste |
| G3+P5 | response_format differs per provider — need per-provider logic | Both | Gemini wants MIME/schema, OpenAI wants json_schema |
| G7 | stream() and batch() in api.py lack system message support | Gemini | Verified: api.py:168, api.py:239 |
| G9 | manifest.json over-engineered — filesystem mtime sufficient | Gemini | ls .context/ is enough |
| P7 | System/user split is hygiene, not caching | GPT | Both providers cache user message prefixes too |
| P8 | ROI: parallel > views > --json > caching > --system > -f | GPT | Quantified per-item |
| P9+P13 | Measurement ledger needed before enforcement | GPT | "Measure before enforcing" at ~45% coverage |
| P10 | HEAD-anchored base + working-tree delta for cache hits | GPT | r increases → hit rate approaches 100% |
| P12 | Two-tier output: JSON array + narrative per finding | GPT | Preserves nuance + enables automation |

## Deferred (with reason)

| ID | Finding | Why Deferred |
|----|---------|-------------|
| G2 | Upgrade --compare for parallel dispatch | Shell & works fine; demonstrated in this review |
| G5 | Repomix MCP server | Maturity uncertain; Gemini flags own uncertainty |
| G11 | Errors/CI-failures view | No CI pipeline currently |
| P11 | Atomic writes for .context/ | Over-engineering for single operator |

## Rejected (with reason)

| ID | Finding | Why Rejected |
|----|---------|-------------|
| G12 | Routing tool for view selection | Adds complexity; Claude choosing from filesystem is fine for single operator |

## Gemini Errors (distrust)

| Claim | Why Wrong |
|-------|----------|
| "Bash & + wait is the wrong tool" | Claude Code does run parallel Bash tool calls concurrently. Demonstrated in this very review. |
| "Temperature override ignored" warning | Expected behavior — Gemini 3.x locks temp at 1.0. The -t 0.3 was aspirational per SKILL.md, known not to work. |

## GPT Errors (distrust)

| Claim | Why Wrong |
|-------|----------|
| P4: "Many tool runtimes serialize tool invocations" | Claude Code parallelizes Bash tool calls when sent in same message. Just verified empirically. |
| Token estimate arithmetic correction | Valid catch but immaterial — these are rough ranges, not budgets |

## Revised Priority List

1. **Parallel dispatch** — fix SKILL.md instruction (already works)
2. **JIT context generation** — Makefile + repomix configs
3. **Determinism testing** — verify byte-identical repomix output
4. **--schema flag in llmx** — per-provider structured output
5. **HEAD-anchored base context** — stable prefix for cache hits
6. **Simple measurement logging** — JSONL per review
7. **--system + -f flags** — hygiene improvements
