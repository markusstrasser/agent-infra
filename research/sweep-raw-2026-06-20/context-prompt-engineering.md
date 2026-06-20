# Recent Context-Engineering / Prompt-Engineering Developments for Agents

Date anchor: 2026-06-20. Source path: Exa MCP primary search; primary URLs only in findings.

## Ranked Findings

1. **Claude Code Dynamic Workflows** — https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code — **2026-06-02**  
   Claim: Claude Code can now generate task-specific workflow harnesses with subagents, model choice, worktree isolation, barriers, and synthesis steps.  
   Demonstrated vs asserted: **Demonstrated product capability + official examples**, not benchmarked in the post.  
   Maturity: Official Anthropic blog; described as released/available in Claude Code.  
   Why it matters locally: This is the closest upstream validation of your file-bus/orchestrator model: dynamic harnesses should be reusable skills/templates, with worktree isolation and explicit barriers.

2. **Less Context, Better Agents** — https://arxiv.org/abs/2606.10209 — **2026-06-10 arXiv window**  
   Claim: Last-5 tool-call retention plus summarization beat full history on a 50-task D365/MCP workflow: 91.6% complete itemization vs 71.0% full-context, with much lower token use.  
   Demonstrated vs asserted: **Demonstrated**, but narrow enterprise expense benchmark; not universal.  
   Maturity: arXiv:2606.10209.  
   Why it matters locally: Supports replacing “keep more transcript” with task-aware pruning plus compact summaries for long Claude/Codex sessions.

3. **Engram: Bi-Temporal Memory Engine** — https://github.com/ly-wang19/engram — **repo created 2026-06-04; arXiv:2606.09900**  
   Claim: Lean hybrid retrieval from bi-temporal facts + raw chunks beats full-history replay on LongMemEvalS: 83.6% vs 73.2%, about 8x fewer tokens.  
   Demonstrated vs asserted: **Demonstrated by paper/repo benchmark logs claim**, needs local reproduction before adoption.  
   Maturity: GitHub 2 stars; created 2026-06-04; arXiv:2606.09900.  
   Why it matters locally: The steal is not the repo; it is the invariant: append lossless episodes, invalidate never delete, retrieve provenance-tagged slices instead of replaying chat history.

4. **Context Window Lifecycle / pi-cwl** — https://github.com/Kiz8-Team/pi-cwl — **repo last push 2026-05-18; arXiv:2606.11213**  
   Claim: Agents annotate trajectory into typed dependency-linked episodes; deterministic eviction drops recoverable action history while preserving active/user context.  
   Demonstrated vs asserted: **Partly demonstrated** via reference implementation and paper claim of 89 sequential tasks / 80M tokens; very immature.  
   Maturity: GitHub 0 stars; last push 2026-05-18; arXiv:2606.11213.  
   Why it matters locally: Strong design pattern for your compaction hooks: evict by recoverability/dependency, not age alone.

5. **CodeGraph local MCP code knowledge graph** — https://github.com/colbymchenry/codegraph — **latest release 2026-06-13; last push 2026-06-19**  
   Claim: Local SQLite/tree-sitter code graph for Claude Code, Codex, Cursor, etc.; claims fewer tool calls and cheaper agent exploration.  
   Demonstrated vs asserted: **Tool exists; performance claims asserted by repo README**, should be locally benchmarked against `rg`/Zoekt before trust.  
   Maturity: GitHub 52,139 stars; last push 2026-06-19; MIT.  
   Why it matters locally: Relevant only if it beats existing Zoekt + `rg` on agent-navigation tasks; the useful pattern is “agent-readable graph query before file fanout.”

6. **HarnessBridge** — https://github.com/mandyyyyii/HarnessBridge — **repo created 2026-06-10; arXiv:2606.12882**  
   Claim: Learnable harness controller projects observations into compact states and rejects/executes actions through trajectory-grounded action projection; reports Terminal-Bench/SWE-bench token and trajectory reductions.  
   Demonstrated vs asserted: **Paper-demonstrated**, but early repo and likely research-grade.  
   Maturity: GitHub 6 stars; created 2026-06-10; arXiv:2606.12882.  
   Why it matters locally: Near-term steal is not training a controller; it is treating observation projection and action validation as first-class harness interfaces.

7. **Agentic Context Description Language (ACDL)** — https://arxiv.org/abs/2605.01920 — **2026-05-03**  
   Claim: A formal DSL for specifying exactly what messages/context appear at each agent step and how context evolves over time.  
   Demonstrated vs asserted: **Specification/tooling exists**, adoption unproven.  
   Maturity: arXiv:2605.01920; official site: http://www.acdlang.org/.  
   Why it matters locally: Useful as an audit notation for context pipelines, especially when comparing Claude/Codex/Cursor instruction loading or compaction behavior.

8. **Anthropic Claude Plugins official marketplace** — https://github.com/anthropics/claude-plugins-official — **major vendor plugin PRs 2026-05-19; last push 2026-06-19**  
   Claim: First-party plugin distribution standardizes skills, hooks, MCP servers, agents, LSPs, and binaries as installable Claude Code packages.  
   Demonstrated vs asserted: **Demonstrated repo/ecosystem artifact**.  
   Maturity: GitHub 30,396 stars; last push 2026-06-19; Apache-2.0.  
   Why it matters locally: Packaging is now part of context engineering: repeatable harness capabilities should ship as versioned plugins/skills, not copied markdown.

9. **Google Agentic Resource Discovery (ARD)** — https://developers.googleblog.com/announcing-the-agentic-resource-discovery-specification/ — **2026-06-17**  
   Claim: Open spec for publishing, discovering, and verifying agents, skills, MCP servers, and tools via web-hosted catalogs and trust metadata.  
   Demonstrated vs asserted: **Spec/product preview**, hosted-enterprise bias.  
   Maturity: Official Google Developers announcement; GitHub/spec referenced by Google.  
   Why it matters locally: Mostly a trust/discovery pattern: local harnesses need pinned, inspectable capability catalogs, not ad hoc tool sprawl.

10. **Google Agentic RAG sufficient-context loop** — https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/ — **2026-06-05**  
   Claim: Multi-agent RAG loop uses query planning/routing plus a “Sufficient Context Agent” that checks whether retrieved evidence is enough before final answer; reports up to 34% factuality improvement.  
   Demonstrated vs asserted: **Official product/research claim**, hosted stack; not directly local.  
   Maturity: Google Research / Google Cloud public preview.  
   Why it matters locally: The steal is a deterministic-ish “sufficient context” gate before synthesis, especially for research scouts and code reviews.

## Notes on Exclusions

Skipped pre-2026 staples unless refreshed by a 2026 release/result. I also skipped non-primary listicles/Medium-style roundups as findings, using them only as discovery hints when Exa surfaced them.

## TOP STEALS

1. **Typed context lifecycle:** store episodes with recoverability/dependencies, then evict deterministically before summarizing.  
2. **Lean retrieved memory beats replay:** append raw episodes, consolidate asynchronously, retrieve provenance-tagged slices.  
3. **Harness capabilities as packages:** skills/hooks/MCP/workflows should be versioned and pinned, with local trust metadata and explicit verification gates.