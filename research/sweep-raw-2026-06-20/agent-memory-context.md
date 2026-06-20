# Agent Memory & Context Engineering Scout  
Date anchor: 2026-06-20. Search path: Exa MCP primary, official/GitHub/arXiv sources only.

## Ranked Findings

1. **PROJECTMEM**  
Primary: https://arxiv.org/abs/2606.12329v1 | 2026-06-10  
Claim: Local-first, event-sourced memory plus deterministic pre-action “judgment” gate for AI coding agents.  
Demonstrated vs asserted: Demonstrated lightly: paper reports implementation, 14 MCP tools, 19 CLI commands, 37 tests, 207 events across 10 projects; still self-study scale.  
Maturity: arXiv:2606.12329; repo https://github.com/riponcm/projectmem, 3 stars, last push 2026-05-20.  
Why it matters: Closest match to a single-operator local Claude-Code/Codex/Cursor harness: append-only typed events, MCP, local-only, and “warn before repeating failed fix.”

2. **Context Ledger**  
Primary: https://github.com/wiztek-llc/context-ledger | 2026-06-08  
Claim: Commit-boundary context compaction keeps compact ledger entries plus git SHA rehydration pointers, matching full-context retention at much lower context cost.  
Demonstrated vs asserted: Demonstrated on a bundled real 4-feature corpus with reproducible benchmark scripts; small corpus, but mechanism is concrete.  
Maturity: 10 stars; last push 2026-06-08.  
Why it matters: The steal is “git is the lossless store”; compact only decisions/interfaces/pointers, then rehydrate exact bytes with `git show`.

3. **@getnodus/context**  
Primary: https://github.com/getnodus/context | 2026-05-27; key PR 2026-06-03  
Claim: Portable MCP personal context layer shared across Claude, Cursor, Codex, etc., stored as local Markdown by default with verification/confidence metadata.  
Demonstrated vs asserted: Demonstrated as working repo/CLI/MCP package; maturity very early.  
Maturity: 1 star; last push 2026-06-18; latest release v0.1.1 on 2026-05-28.  
Why it matters: Useful pattern: memory entries have semantic types, author attribution, duplicate handling, and `verify` blocks instead of silent stale facts.

4. **Letta Code SDK: MemFS default for new agents**  
Primary: https://github.com/letta-ai/letta-code-sdk/commit/a6204fe59d7a56a4e720f25b0bc105103afd1411 | 2026-06-05  
Claim: SDK-created Letta Code agents now default to git-backed MemFS and get an `origin:letta-code` tag unless explicitly opted out.  
Demonstrated vs asserted: Demonstrated in code/tests; not a benchmark.  
Maturity: `letta-code-sdk` 74 stars; commit 2026-06-05. Parent Letta ecosystem is much larger, but this SDK is young.  
Why it matters: Confirms convergence on git-backed memory filesystem as the default state substrate for coding agents.

5. **MemRefine**  
Primary: https://arxiv.org/abs/2606.13177 | 2026-06-11  
Claim: LLM-guided delete/merge/preserve compression keeps long-term agent memory inside a fixed storage budget better than rule-based baselines.  
Demonstrated vs asserted: Demonstrated in paper experiments across memory frameworks and long-term conversation benchmarks; not yet a local coding-agent harness.  
Maturity: arXiv:2606.13177.  
Why it matters: Good design warning: memory growth needs compaction policy; similarity alone is not enough because factual value differs from surface similarity.

6. **StreamMemBench**  
Primary: https://arxiv.org/abs/2606.14571 | 2026-06-12  
Claim: Streaming benchmark tests whether agent memory turns observations and feedback into future-oriented assistance; current systems often fail that step.  
Demonstrated vs asserted: Demonstrated benchmark over eight memory systems and two backbones.  
Maturity: arXiv:2606.14571.  
Why it matters: Evaluates the real target for a local harness: not “can retrieve a note,” but “does the next session behave better because of it.”

7. **Mem0 current repo: MCP + agent skills + OpenCode plugin wave**  
Primary: https://github.com/mem0ai/mem0 | latest visible release activity 2026-06-12 to 2026-06-17  
Claim: Mature universal memory layer now exposes MCP docs/tools, agent skills, CLI, and plugin integrations around the April 2026 memory algorithm.  
Demonstrated vs asserted: Mixed: repo/tooling is demonstrated; benchmark claims are vendor-reported.  
Maturity: ~58-59K stars; last push 2026-06-12 in Exa repo metadata; latest release surfaced as Mem0 OpenCode Plugin v0.2.0 on 2026-06-17.  
Why it matters: Worth stealing integration ergonomics, not necessarily adopting hosted memory: MCP tools, skills, and agent-facing install paths reduce setup friction.

8. **Zep Graphiti MCP/Core Parity work**  
Primary: https://github.com/getzep/graphiti/pull/1565 | 2026-06-08  
Claim: Graphiti core/MCP recently added parity work around bi-temporal graph memory, communities, filters, triplets, custom types, and scalar `group_id` handling.  
Demonstrated vs asserted: Demonstrated in merged PR/release notes and tests; operational complexity remains high.  
Maturity: ~27K stars; relevant PR merged 2026-06-08.  
Why it matters: For a local single-operator harness, Graphiti is probably too heavy, but its typed temporal graph API is a useful reference for when Markdown/BM25 stops being enough.

9. **Training-Free Lexical-Dense Fusion for Conversational-Memory Retrieval / `opsem`**  
Primary: https://github.com/Chrislysen/opsem | 2026-06-02  
Claim: BM25 plus turn-level late-interaction dense retrieval beats either alone on LoCoMo; cross-encoder reranking hurts in their setup.  
Demonstrated vs asserted: Demonstrated with reproduction code and receipts; arXiv link pending.  
Maturity: 0 stars; last push 2026-06-02.  
Why it matters: Reinforces a local harness default: start with BM25/grep and only add dense retrieval where it wins by measured eval.

10. **Agentic Retrieval Matrix**  
Primary: https://github.com/cobusgreyling/agentic-retrieval-matrix | 2026-06-05  
Claim: Factorial benchmark isolates retriever × delivery × harness effects for agentic search/memory evaluation.  
Demonstrated vs asserted: Demonstrated as tiny offline benchmark scaffold; current fixture is only 3 questions.  
Maturity: 0 stars; last push 2026-06-06.  
Why it matters: The steal is the eval shape: compare inline vs file delivery and grep vs vector under the actual harness, not standalone retrieval scores.

## Skips / Low Transfer

- MemGPT/Letta original MemGPT paper: pre-2026 staple, low-transfer for current frontier behavior except as architecture lineage.
- Generic Mem0/Zep comparison blogs: vendor positioning, useful framing but not stronger than repo/arXiv primary sources.
- Hosted multi-agent memory services: deprioritized unless they ship local-first/MCP/git-compatible mechanics.

## TOP STEALS

1. **Memory-as-governance:** store failed attempts as typed events, then gate future actions before repeating them.  
2. **Restorable compression:** compact at semantic boundaries, keep exact rehydration handles to git/files/tool-output archives.  
3. **Verified local memory entries:** author attribution + `verify`/confidence state beats timeless prose summaries that quietly rot.