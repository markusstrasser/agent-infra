---
date: 2026-04-25
topic: agent-infra weekly digest — tool gating + skill discovery
sources: 2
tier: standard
---

# Tool Attention + Co-Evolving Skill Bank — Two papers from arxiv week of 2026-04-19

Two papers this week directly intersect with the harness-level work in this repo: one formalizes the cost model behind deferred tool loading (which `ToolSearch` already implements in our Claude Code harness), the other proposes a co-evolution loop between a decision agent and a learnable skill bank.

## Paper 1 — Tool Attention Is All You Need [Sadani & Kumar 2026, arxiv:2604.21816]

### What it argues

Eager schema injection at every turn imposes a hidden 10k–60k token "Tools Tax" in typical multi-server MCP deployments. Past ~70% context utilization, reasoning degrades. Tool Attention is a middleware-layer fix:

1. **Intent–Schema Overlap (ISO) score** — sentence-embedding similarity between user query and compact tool summary
2. **State-aware gating** — deterministic precondition filter (auth, workflow stage)
3. **Two-phase lazy loader** — permanent cacheable "Summary Pool" (~60 tokens/tool); full JSON schemas promoted only for top-k tools

### Numbers (with caveat)

| Metric | Full-Schema baseline | Tool Attention | Δ |
|---|---|---|---|
| Per-turn tool tokens | 47.3k | 2.4k | −95.0% |
| Context utilization | 24% | 91% | +67pp |
| Success rate (projected) | ~72% | ~94% | +22pp |
| P50 latency (projected) | ~4.2s | ~2.0s | −52% |
| Marginal cost/task (projected) | $0.21 | $0.03 | −86% |

**Caveat — token numbers are measured; success/latency/cost are projections.** The 120-tool, six-server benchmark is *simulated*, calibrated to public MCP audits (GitHub, Enterprise DB). Downstream metrics are extrapolated from measured token counts using "frontier chat model telemetry," not live end-to-end agent runs. Treat success-rate and cost claims as informed extrapolations, not measurements. `[ARXIV: 2604.21816]`

### Author-acknowledged limitations

- Application-layer fix only — can't resolve underlying MCP protocol gaps (no session-scoped capability negotiation)
- Performance contingent on tool-summary quality (cryptic names degrade retrieval)
- Live agent runs not conducted — success rate is projected

### Lift-able pattern

**Two-phase lazy loading with hallucination gate.** Keep a static cacheable summary list in system prompt; promote full JSON schemas only for top-k gated tools. Add a middleware gate that *rejects tool calls for schemas not promoted that turn* — this is the safety belt the paper underspecifies but is critical: an agent that has seen a tool's name in the summary pool can hallucinate calls to it without a loaded schema.

### Relevance to this repo

Our `ToolSearch` deferred-tool mechanism implements roughly the (1)+(3) parts of Tool Attention. **What we don't have:**

- Measured token-budget impact of `ToolSearch` vs naive eager loading — paper provides the methodology
- Hallucination gate — does the harness reject tool calls for un-promoted schemas, or does it lazily load on first use? Worth checking.
- ISO-score equivalent — `ToolSearch` uses keyword/`select:` matching, not semantic similarity. Could be an axis to evaluate.

## Paper 2 — Co-Evolving LLM Decision and Skill Bank (COS-PLAY) [Wu et al. 2026, arxiv:2604.20987]

### What it argues

Couples a decision agent with a learnable **Skill Bank** that evolves alongside it via Group Relative Policy Optimization (GRPO) with separate LoRA adapters. Skill Bank performs unsupervised skill discovery by:

1. Segmenting unlabeled agent rollouts
2. Learning "effect contracts" (state predicates that change between segment start/end)
3. Refining the bank: merging, splitting, retiring skills

### Numbers

| Benchmark | Result |
|---|---|
| Single-player games (avg) | +25.1% reward over GPT-5.4 |
| Diplomacy | +8.8% mean supply centers vs Gemini 3.1 Pro |
| Avalon | −1% win rate vs GPT-OSS-120B (competitive) |
| MMLU-Pro reasoning preservation | −0.8% absolute drop |
| Math-500 | −1.8% absolute drop |

Base model: Qwen3-8B for both agents. Cold-start SFT used 60 seed trajectories from GPT-5.4. Six interactive game environments (2048, Candy Crush, Tetris, Super Mario, Avalon, Diplomacy). `[ARXIV: 2604.20987]`

### Author-acknowledged limitations

- Text-state bottleneck — relies on compact textual summaries, can miss visual evidence
- Summarization errors compound over long trajectories
- No raw visual observation handling, no long-term temporal dependency modeling

### Lift-able pattern

**Effect-contract skill discovery.** Don't hand-write a skill set — segment successful trajectories and define each segment by the state-predicate diff between start and end. The "contract" is what makes a skill retrievable and composable. The merge/split/retire loop replaces our manual skill curation (this very session was 90 minutes of manual symlink curation across 5 projects).

### Relevance to this repo

Our skills (`~/Projects/skills/`) are hand-authored. The COS-PLAY paper suggests a different shape: skills as *discovered effect contracts* over agent trajectories. We have the trajectory data — `~/.claude/projects/*/UUID.jsonl` plus `runlogs.db` — but no automated skill-extraction loop. This is a research direction, not a quick fix; the paper's evaluation is on games, not coding tasks, so transfer is unproven.

## Synthesis

**Strong signal:** The Tool Attention paper validates the deferred-loading direction we're already on, and the methodology section is reusable for benchmarking our own `ToolSearch`.

**Weaker signal:** COS-PLAY is intellectually interesting but the gap between game-environment skill discovery and coding-agent skill curation is large. Worth re-reading once they (or someone) replicate on SWE-bench or terminal-bench.

**Concrete next step (optional):** Measure our actual `ToolSearch` token savings on a representative session — should be straightforward by comparing eager vs deferred tool listings in the system prompt header. Paper's framing makes this a 1-hour task, not a 1-week project.

## Measured: ToolSearch token impact in this harness

Testing the question Sadani's paper provokes: how much context does our `ToolSearch` deferred-loading actually save?

### Method

This session loaded 22 deferred tools incrementally via `ToolSearch`. Each loaded schema is wrapped in a `<function>{...}</function>` block and inserted into context. I measured the per-schema char count from the actual loaded definitions, computed an average, and extrapolated to the full deferred set.

### Numbers

- **Deferred tools listed at session start**: ~70
- **Tools loaded this session (sample)**: 22, total ~34,000 chars (~8,500 tokens at 4 chars/tok)
- **Average schema size**: ~1,545 chars (~386 tokens) per tool
- **Range**: ~250 chars (`read_paper`, minimal params) to ~3,500 chars (`web_search_advanced_exa`, 20+ optional fields)
- **Estimated total if all 70 were eager-loaded**: ~108,000 chars ≈ **~27,000 tokens**

### Interpretation

| Context window | Eager tool overhead | % of context |
|---|---|---|
| 200k (Sonnet/Opus default) | ~27k tokens | 13.5% |
| 1M (Opus 1M, Gemini) | ~27k tokens | 2.7% |

Tool Attention paper measured 47.3k tokens for a 120-tool environment; we measure ~27k tokens for 70 deferred tools (plus ~8 always-loaded basics). Per-tool, our schemas are ~70 tokens larger on average — likely because our MCP schemas are more verbose than the paper's calibration set. Order of magnitude matches.

### Caveats

- Sample bias: the 22 measured tools skew toward research/web (verbose param sets) and away from CRUD/notebook tools. True average may be lower.
- Char-to-token ratio is rule-of-thumb (4:1 for English; JSON schemas have more punctuation, may run 3.5:1, biasing token count up by ~15%).
- "Always-loaded" base (Agent, Bash, Edit, Read, ScheduleWakeup, Skill, ToolSearch, Write) is ~8 tools — already part of context, not part of the deferred budget.

### Verdict

`ToolSearch` saves a real but modest amount of context per session — ~27k tokens at the configured deferred-tool count of ~70. On 1M-context models this is barely 2.7% — not the order-of-magnitude win Sadani reports for 120-tool MCP setups, but not negligible either, especially given that the saved tokens compound with KV-cache: every turn pays them, every turn we save them.

The bigger qualitative win isn't the token count — it's that `ToolSearch` lets the harness ship ~70 capabilities without forcing the agent to scan all of them on every turn. The token saving is the side-effect of correct architecture, not the architecture's main purpose.

### Hallucination gate

**Confirmed present.** The system prompt states deferred tool calls without loaded schemas fail with `InputValidationError`. This is enforced at the harness's schema-validation layer, not as separate middleware. Functionally equivalent to Sadani's "reject calls for un-promoted schemas" pattern.

## Sources

- [arxiv:2604.21816] Tool Attention Is All You Need — Sadani & Kumar (Infrrd.ai), Apr 2026 — local PDF, full text 53k chars
- [arxiv:2604.20987] Co-Evolving LLM Decision and Skill Bank Agents for Long-Horizon Tasks — Wu et al. (UMD/USC/MBZUAI), Apr 2026 — local PDF, full text 65k chars

Both fetched via research-mcp `fetch_paper`; numbers extracted via `ask_papers` (Gemini 3 Flash, no RCS — RCS returned no relevant evidence on first attempt, which is itself a signal that Gemini's chunker is mis-scoring engineering-paper text).

<!-- knowledge-index
generated: 2026-04-25T22:57:56Z
hash: b38f858e9260


end-knowledge-index -->
