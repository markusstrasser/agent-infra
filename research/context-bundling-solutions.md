# Context Bundling & Formatting Solutions: What Can We Learn?

**Date:** 2026-03-20
**Question:** What do repomix, aider repo-map, and other context packing tools know about formatting code for LLMs that we don't?
**Consult before:** repo_tools_mcp improvements, context engineering decisions, MCP tool surface area audits

## The Landscape (Four Tiers)

Ry Walker's March 2026 comparison identifies four tiers of code intelligence for agents:

| Tier | Examples | Approach | Our equivalent |
|------|----------|----------|----------------|
| Knowledge graph engines | GitNexus (14k stars), CodeGraphContext | Build queryable dependency/call graphs | `repo_callgraph` + `repo_imports` (partial) |
| MCP code search | Octocode, CodePathFinder | Search-focused tools | Grep/Glob + `repo_outline` |
| Context packing | Repomix (22k stars), code2prompt | Bundle entire repos into single files | `.claude/overviews/` (Gemini-generated) |
| Platform solutions | Sourcegraph Cody, DeepWiki, Greptile | Full-stack hosted | N/A (we use Claude Code directly) |

[SOURCE: rywalker.com/research/code-intelligence-tools, 2026-03-15]

## Tool-by-Tool Analysis

### Repomix (22k stars)

**What it does:** Packs a codebase into a single file for copy-pasting into chat UIs. Four output formats: XML (default), Markdown, Plain, JSON.

**Key formatting choices:**
- **XML as default** — justified by Anthropic/OpenAI/Google all recommending structured tags for complex prompts. Not benchmarked; based on vendor docs. [SOURCE: repomix.com/guide/output]
- **Section ordering:** `file_summary` (metadata + AI instructions) → `directory_structure` (tree) → `files` (content) → `git_logs` (recent commits)
- **Tree-sitter compression** (`--compress`): Extracts signatures, types, class structures; removes implementation bodies. Experimental. Preserves: class properties, interfaces, function signatures. Removes: loop/conditional logic, internal variables. [SOURCE: repomix.com/guide/code-compress]
- **Noise reduction options:** Remove comments, remove empty lines, security scanning (Secretlint)
- **Token counting** per file and total — awareness of budget

**What's novel vs our research:**
- The compression mode is conceptually identical to our `repo_outline` — both use tree-sitter to extract signatures. But repomix offers it as a *dial on the same content*, not a separate tool. The user sees the same repo at different compression levels.
- XML default is a community signal, not new evidence. Our `structured-vs-prose` memo already notes this is empirically open.
- **Git log inclusion** is interesting — recent commits provide change-velocity context. Our `repo_changes` tool does this separately.

**What doesn't transfer:** The whole-repo-in-one-file paradigm is for chat UIs without tool access. Claude Code can read files on demand — it doesn't need a monolith. Repomix's own MCP server acknowledges this by offering tools instead of a single file.

### Aider Repo-Map (PageRank on Symbols) — Most Novel

**What it does:** Before every LLM call, automatically computes which symbols/files are most relevant to the current conversation and includes a compact structural overview.

**Algorithm (6 phases):**
1. **Symbol extraction** — tree-sitter parses every file, extracts definitions (classes, functions, methods)
2. **Reference extraction** — tree-sitter `tags.scm` queries find all symbol references
3. **Graph construction** — directed edges from reference → definition across files
4. **Personalized PageRank** — biased toward files currently being edited. Files in the chat get extra weight.
5. **Token-budget rendering** — top-ranked symbols rendered as scope-aware elided views (`⋮...` between relevant chunks). Fits within a configurable token budget.
6. **Refresh on every turn** — the map adapts as the conversation evolves

[SOURCE: aider.chat/docs/repomap.html; github.com/NousResearch/hermes-agent/issues/535 for detailed analysis of `repomap.py`]

**What's genuinely novel:**
- **Conversation-aware ranking.** Our repo_tools are static — same output regardless of what the agent is working on. Aider's map changes based on what files are being edited. The context is *task-relevant*, not just structurally correct.
- **Token budget as first-class parameter.** Aider explicitly fits its map into a budget. Our tools don't know or care about remaining context — they dump everything at the requested tier.
- **Elided scope rendering** (`⋮...` between relevant parts of a file). Not "full file or outline" binary — a middle ground showing relevant definitions with surrounding context.

**Hermes-Agent adoption proposal (teknium1, 2026-03-06):** Explicitly calls this "Aider's most powerful system" and proposes porting it. Distinguishes it from regex search and embedding-based search as "automatic, graph-based, zero-effort context." [SOURCE: github.com/NousResearch/hermes-agent/issues/535]

### ContextPacker (No Embeddings, Hierarchical)

**What it does:** "Bootloader for agents" — gives an agent a mental map of an unfamiliar repo in seconds, no pre-indexing.

**Pipeline:**
1. **Semantic skeleton** — hierarchical tree with query-aware expansion. Low-signal folders compressed to `... +142 more files`; high-signal branches expanded. AST-based symbol extraction.
2. **LLM-assisted selection** — a fast reasoning model assigns priority tiers: Critical (55% budget), Important (30%), Supplementary (10%)
3. **Adaptive packing** — reads selected files, truncates gracefully to fit token budget. Imports and definitions always preserved even in truncated files.

[SOURCE: contextpacker.com/how-it-works.html]

**What's novel:**
- **Explicit budget allocation ratios.** 55/30/10 split for critical/important/supplementary. We have no equivalent — our approach is "load what seems relevant."
- **Hierarchical compression of the tree itself** — collapsing irrelevant subtrees instead of showing the full directory structure or nothing. This is a UI/compression technique we don't use.
- **LLM-in-the-loop for context selection** — using a fast model to decide what's relevant before sending to the main model. Our tiered loading is human/agent-decided, not pre-filtered.

**Benchmarks (self-reported):** 75% expert recall vs 60-70% for embeddings. ~1.5s latency warm. Zero setup time. [SOURCE: contextpacker.com/how-it-works.html]

### jCodeMunch MCP (1.2k stars)

**What it does:** Tree-sitter AST index of a codebase, exposed as MCP tools. Agents retrieve individual symbols (functions, classes, methods, constants) by name instead of reading whole files.

**Key claim:** 95%+ token reduction for code reading in retrieval-heavy workflows. [SOURCE: github.com/jgravelle/jcodemunch-mcp]

**Core framing:** "Agents should *navigate* code, not *read* it." Traditional: open file → scan → find relevant code. jCodeMunch: search symbol → fetch exact implementation with byte-level precision. [SOURCE: virtuslab.com/blog/ai/code-munch-mcp-your-agent-starts-navigating, 2026-03-11]

**What's novel:**
- **Symbol-level retrieval** — our `repo_outline` gives file-level structure (class/function signatures per file). jCodeMunch returns the *actual implementation* of a named symbol, nothing more. Fills the gap between "what exists" (outline) and "read the whole file" (Read tool).
- **Index once, query many** — indexes the codebase upfront, then serves queries from the index. Our repo_tools re-parse on every call (stateless).

**What doesn't transfer cleanly:** Requires maintaining an index. Our tools are stateless (re-parse live code) which means zero maintenance. The bitter lesson from `code-structure-for-agents.md` says stateless tools survive model improvements better. But the token savings are real for the current generation.

## Practitioner Confirmation: Context Budget Is Real

Reddit post (2026-03-13, r/ClaudeCode): User removed 63% of their Claude Code setup (15/20 MCP servers, ~50 skills, 52 commands, 12 agents) and reported dramatically better performance. "Night and day. Responses are noticeably faster, less token waste on startup, context window isn't getting polluted with tool definitions I never use." [SOURCE: reddit.com/r/ClaudeCode/comments/1rnxm5c]

This directly confirms our context-rot research: every tool definition is a token cost that degrades reasoning. The cost isn't just the tool description — it's the attention dilution across all other content.

## Synthesis: What's Transferable

### Already Known (no delta)
- XML tags improve LLM parsing of structured content (our structured-vs-prose memo)
- Tree-sitter for code signatures (our repo_outline already does this)
- File naming and architecture maps are highest ROI (our code-structure memo)
- Context rot is real and architectural (our context-rot-evidence memo)

### Novel Patterns Worth Considering

**1. Conversation-aware context ranking (Aider)**
- Our repo_tools are static queries. Aider's key insight: the *same codebase* should produce different context depending on what the agent is currently working on.
- Implementation path: personalized PageRank on symbol graph, biased toward files in current conversation.
- **Bitter-lesson risk:** Medium. Models are getting better at deciding what to read, but "what's structurally connected to what I'm editing" is genuinely un-derivable without the graph.
- **For us:** We already have the raw ingredients (`repo_callgraph`, `repo_outline`, `repo_imports`). A `repo_context(task="...", budget=N)` tool that combines them with relevance ranking would be the synthesis.

**2. Token budget as first-class parameter**
- None of our tools accept a token budget. They dump at the requested tier regardless of remaining context.
- Aider, ContextPacker, and jCodeMunch all treat token budget as a core parameter.
- **For us:** Adding an optional `max_tokens` param to repo_tools that truncates output to fit would be trivial and useful. The tool knows its output size; the agent doesn't until it receives it.

**3. Compression as a continuum, not discrete tiers**
- Repomix's `--compress` and Aider's elided views show a spectrum: full source → signatures + relevant bodies → signatures only → file names only.
- Our L0/L1/L2 tiering is conceptually similar but implemented as discrete tools. A single tool with a `detail` parameter (or auto-adjusted by token budget) would be smoother.
- **Bitter-lesson risk:** Low. This is a UX improvement, not a capability that models will replace.

**4. Hierarchical tree compression**
- ContextPacker collapses irrelevant subtrees to `... +N files`. This gives spatial orientation (you know the folders exist) without paying the full token cost.
- Our `repo_summary` shows every file. For large repos, a budget-aware version that collapses low-signal directories would be better.
- **For us:** Simple implementation — count tokens per directory, collapse directories below a relevance threshold.

**5. Symbol-level retrieval (the middle ground)**
- Current: `repo_outline` (signatures only) or `Read` (whole file). No way to get "just the implementation of function X."
- jCodeMunch fills this gap. Our `repo_outline` could add a `symbol` parameter that returns the full definition of a named symbol.
- **Bitter-lesson risk:** High. "One Tool Is Enough" paper shows RL-trained agents learn to search efficiently. But for current models, the token savings are substantial.

### Patterns to Explicitly Reject

**Whole-repo packing** — Designed for chat UIs without tool access. Claude Code agents have Read/Grep/Glob. A monolithic file is strictly worse than on-demand retrieval for tool-using agents.

**Embeddings/vector indexes** — Our `search-retrieval-architecture.md` already assessed this. CAG + native search tools beats RAG for codebases the agent works in repeatedly. ContextPacker's own benchmarks show marginal recall improvement (75% vs 60-70%) at the cost of infrastructure complexity.

**LLM-in-the-loop context selection** — ContextPacker uses a fast model to rank files. This adds latency, cost, and a failure mode. For repos the agent works in repeatedly, the agent learns what's relevant faster than a pre-filter can predict it.

## Actionable Items (If Pursued)

| Item | Mechanism | Effort | Bitter-lesson risk |
|------|-----------|--------|-------------------|
| `max_tokens` param on repo_tools | Truncate output to token budget | Low | None — UX improvement |
| Hierarchical tree compression in `repo_summary` | Collapse low-signal directories | Low | None — compression technique |
| Symbol-level retrieval in `repo_outline` | Return full definition of named symbol | Medium | High — models learn to search |
| Conversation-aware ranking | PageRank on symbol graph | High | Medium — requires graph maintenance |
| Continuous compression dial | Merge L0/L1/L2 into one tool with `detail` param | Medium | Low — UX improvement |

## Open Questions

- **Does adding `max_tokens` to repo_tools actually reduce downstream tool calls?** Measurable via session-analyst.
- **At what repo size does conversation-aware ranking pay off?** Aider's repos are often 50-500 files. Our repos are 20-50 files — may not be worth the graph overhead.
- **Is tree-sitter index maintenance worth it vs stateless re-parsing?** jCodeMunch claims 95% savings but requires index freshness. Our stateless approach has zero maintenance.

## Sources

- [SOURCE: rywalker.com/research/code-intelligence-tools] Four-tier code intelligence taxonomy (2026-03-15)
- [SOURCE: repomix.com/guide/output] Repomix output formats and XML rationale
- [SOURCE: repomix.com/guide/code-compress] Tree-sitter code compression
- [SOURCE: aider.chat/docs/repomap.html] Aider repo-map architecture
- [SOURCE: github.com/NousResearch/hermes-agent/issues/535] Detailed analysis of aider's PageRank repo-map (teknium1, 2026-03-06)
- [SOURCE: contextpacker.com/how-it-works.html] ContextPacker pipeline and benchmarks
- [SOURCE: github.com/jgravelle/jcodemunch-mcp] jCodeMunch MCP — symbol-level retrieval
- [SOURCE: virtuslab.com/blog/ai/code-munch-mcp-your-agent-starts-navigating] VirtusLab analysis of jCodeMunch (2026-03-11)
- [SOURCE: reddit.com/r/ClaudeCode/comments/1rnxm5c] 63% setup removal → dramatic improvement (2026-03-13)

<!-- knowledge-index
generated: 2026-03-21T23:52:35Z
hash: a14f0c22b568


end-knowledge-index -->
