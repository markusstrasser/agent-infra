# Arena.ai Agent Arena — What Transfers to a Single-Operator Setup — Research Memo

**Question:** Arena.ai launched "Agent Arena" (live agentic evals, 5-signal leaderboard via causal inference). Can we learn from it? Specifically: is a per-vendor tool-hallucination incidence metric worth building, and does any other Arena signal transfer?
**Tier:** Standard→Deep | **Date:** 2026-06-04
**Ground truth:** We already extract raw behavioral session features (`session-features.py`), report-only build-then-undo detection (`buildthenundo.py` + `v_build_then_retire`), and run a real eval harness (`~/Projects/evals/`: judge_v1, calibration, cross_lab_review). A composite session quality_score is **vetoed twice** (`vetoed-decisions.md`; `session_quality` table confirmed 0 rows today).

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Arena's "causal inference" = treating each agent **subcomponent** (orchestrator/harness/LLM/tool/framework) as a *treatment* and estimating its effect across millions of sessions; rankings via Bradley-Terry on pairwise votes | Arena-Rank methodology blog | HIGH | [arena.ai/blog/arena-rank](https://arena.ai/blog/arena-rank/) | VERIFIED |
| 2 | Tool-hallucination has a settled 3-class taxonomy: (a) incorrect tool selection, (b) malformed parameters, (c) "tool bypass" (model simulates output instead of invoking) | Amazon, "Internal Representations as Indicators of Hallucinations in Agent Tool Selection" | HIGH | [arXiv:2601.05214](https://arxiv.org/pdf/2601.05214) | VERIFIED |
| 3 | Classes (a-nonexistent-tool) and (b-malformed-args) are **deterministically detectable** from our logs; class (c-bypass) is NOT (no call = no error event) | `agentlogs.db` probe + taxonomy | HIGH | [DATA] | VERIFIED |
| 4 | Genuine tool-hallucination incidence in our corpus is low: claude ~202 (131 malformed-arg + 71 invented-tool), codex ~186, gemini 0, kimi 1, over 507K tool calls (~0.13–0.17%) | `agentlogs.db` tight-signature query | HIGH | [DATA] | VERIFIED |
| 5 | A naive FTS/LIKE probe over-counts ~3× (claude 606 → 202 genuine) because research-memo text contains phrases like "tool not found" | `agentlogs.db` cross-check | HIGH | [DATA] | VERIFIED |
| 6 | Cross-vendor *rate comparison* is confounded: Claude's harness **rejects** malformed calls (surfacing `InputValidationError`), other harnesses may coerce/silently accept — so a raw per-vendor rate is apples-to-oranges | tool_result sampling + harness design | MED | [INFERENCE] | INFERENCE |
| 7 | Literature on tool-call quality is benchmark-based (BFCL, ToolBeHonest, AgentHallu, CRITICTOOL), not production-log-derived — Arena is the novel "live log" instance | Exa research-paper sweep | MED | [arXiv:2406.20015](https://arxiv.org/abs/2406.20015), [AgentHallu](https://openreview.net/forum?id=lQ1kt3nkD2) | VERIFIED |

---

## Key Findings

### Arena's headline method structurally does not transfer
Arena ranks **models/components** by routing comparable tasks across a population and estimating per-component treatment effects (Bradley-Terry + reweighting). This needs *component variation across many independent sessions/voters* — a marketplace property. We are a single operator with ~4,586 single-stream sessions and no counterfactual same-task assignment. There is **no single-stream analog** of the causal leaderboard, and model *selection* is already owned by `model-guide` + `evals/cross_lab_review`. [INFERENCE from claim 1]

### The composite leaderboard output is already vetoed
Arena's deliverable is a composite score per model. We built that twice (`compute_quality_score`/`enrich_sessions_db`, @ce4f331); it never ran (0/3850 scored); migration 003 dropped the table. `session-features.py` enforces the veto in a code comment: *"RAW advisory features only — never reduced to a composite quality_score."* Porting Arena's leaderboard = re-deriving a vetoed decision. (`vetoed-decisions.md`, scored-regression-gate entry.)

### Three of the five signals are already covered; two are not
| Arena signal | Our status |
|---|---|
| Steerability | Covered — `backtrack_count`, `query_reformulation_count`, session-analyst corrections |
| Error recovery | Partial — we have `tool_failure_rate` but not "recovered after failure" |
| Task success | Covered (eval-harness, not session-derived) — `evals/` judge_v1 |
| Praise/complaint | Not extracted — `#f` marker exists but unscored |
| Tool hallucination | **Not measured** — the one genuinely new, cheap, deterministic, cross-vendor, non-composite signal |

### The actionable reframe: fix tools, don't rank models
The Arena framing is "rank models by tool hallucination." For a single operator the **actionable** consumer is different: the invented tools (`mcp__phenome__grep`, `mcp__genomics__modal_volume_inspect`) and the malformed-arg patterns (`head_limit` on Glob, `-o` on Grep, `offset` as string) are a **TODO list for tool-affordance fixes** — add the missing alias, fix the misleading tool description, add the param. That consumer has teeth; a per-vendor rate does not (gemini 0, kimi 1, claude/codex ~0.15% — too low and too confounded to drive model routing).

### Deterministic scope is honest and sufficient
Our deterministic signal catches taxonomy classes (a-invented-tool) and (b-malformed-args) — the "harness-rejected" subset. It **misses** (c-tool-bypass, model fabricates a result) and "wrong-but-valid tool," which need LLM-judgment or transcript heuristics. For a cheap characterization that's the right scope; the memo must state what it misses rather than imply full coverage.

---

## What's Uncertain
- Arena's *exact* tool-hallucination operationalization (deterministic vs LLM-judged) isn't in their public blog — claim 2's taxonomy is the literature standard, not necessarily Arena's internal definition.
- Whether (c-tool-bypass) occurs for us at all — untested; would need a transcript-level heuristic (assistant claims a tool result with no preceding tool_call). Possibly a follow-up probe.

## Disconfirmation
- Searched for the signal being a problem: incidence is **low** (~0.15%), which is itself the disconfirming evidence against a *standing per-vendor metric*. Pre-build check #1 ("has this problem actually occurred?") → yes but rare → favors one-time characterization over standing infrastructure.
- No evidence found that single-operator log-derived component ranking is methodologically valid; Arena's own method depends on population-scale component variation.

## Recommendation (→ plan)
Do **not** port the leaderboard or build a per-vendor composite. **Do** run a one-time characterization (1/10 complexity): bucket the ~400 genuine tool-hallucination events by `(tool_name, error_class)` to surface the top hallucinated-against tools/args, then fix those affordances. Graduate to a standing report-only view (`v_tool_hallucinations`, mirroring `v_build_then_retire`) **only if** recurrence justifies it. Plan: `.claude/plans/` (next).

## Sources & Search Log
- [arena.ai/blog/arena-rank](https://arena.ai/blog/arena-rank/) — Bradley-Terry + component-treatment causal method
- [arXiv:2601.05214](https://arxiv.org/pdf/2601.05214) — Amazon, tool-hallucination 3-class taxonomy + real-time detection (86.4%)
- [arXiv:2406.20015](https://arxiv.org/abs/2406.20015) — ToolBeHonest diagnostic benchmark
- [AgentHallu](https://openreview.net/forum?id=lQ1kt3nkD2), [Faults in Agentic AI taxonomy](https://arxiv.org/html/2603.06847v1), [CRITICTOOL](https://arxiv.org/abs/2506.13977v1) — corroborating fault taxonomies
- [DATA] `~/.claude/agentlogs.db` — 507,210 tool_calls; tight-signature incidence probe (claude 202 / codex 186 / gemini 0 / kimi 1)
- Queries: 1 WebSearch (Arena method), 1 Exa research-paper sweep (8 hits), 6 local SQL/grep probes. Perplexity unavailable (quota 401).
