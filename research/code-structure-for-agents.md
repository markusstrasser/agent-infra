# Code Repository Structure for AI Agent Navigation

**Date:** 2026-03-06
**Question:** How should code files and repositories be structured/formatted for optimal AI agent navigation? Comments? Call graphs? Progressive summarization? Or does the bitter lesson make all of this moot?

## Selection rule

The null process here is building elaborate code-navigation infrastructure that becomes unnecessary when the next model ships. The residual signal comes from interventions that are:
- Information the model genuinely can't derive from source (intent, architecture, "why")
- Cheap enough to maintain that abandoning them costs nothing
- Validated by at least one empirical result, not just plausibility

## The Bitter Lesson Applies — Partially

Browser Use's experience is the cleanest practitioner articulation: thousands of lines of agent abstractions, every experiment fought the framework. The RL'd model was the value, not the scaffolding. Hex's product team confirms: "Are we building something that can take advantage of better models, or building around existing model deficiencies?" [SOURCE: browser-use.com/posts/bitter-lesson-agent-frameworks, hex.tech/blog/bitter-lessons]

**Counterpoint:** AutoHarness (arXiv:2603.03329) shows weaker model + better harness beats stronger naked model. Lance Martin (LangChain/Latent Space): "AI tool differentiation now lies in the harness, not just the underlying LLM."

**Resolution:** The bitter lesson kills abstraction layers that duplicate what the model already does (planning frameworks, routing logic, multi-agent decomposition). It does NOT kill information the model can't derive from first principles — repo architecture, build graphs, intent metadata. The model can learn to grep better; it can't learn your repo's architecture without seeing it.

## Graph-Based Code Navigation: Mixed Evidence

Three systems try to give agents structural code knowledge:

1. **CodexGraph** (arXiv:2408.03910, 61 citations, 2024): Code knowledge graph (classes, functions, imports, call chains) queryable by LLM. Works on benchmarks. But requires building and maintaining the graph index.

2. **Repository Intelligence Graph (RIG)** (arXiv:2601.10112, 2026): Deterministic, evidence-backed architectural map for multilingual projects. More practical than CodexGraph — deterministic, not learned. Targets build/test structure that's hard to infer from source alone.

3. **GraphCodeAgent** (arXiv:2504.10046, 2025): Dual graph (dependency + call) for retrieval-guided repo-level code generation. Shows improvement on benchmarks.

**The counterweight — "One Tool Is Enough"** (arXiv:2512.20957, 2025): RL-trained agent localizes files/functions with JUST a code search tool. No graph databases, no multi-tool scaffolding. Finding: existing methods "rely on multiple auxiliary tools, which often overlook code execution semantics." Single well-trained tool user matches or beats multi-tool setups.

**Takeaway:** Graph tools help for novel repos (no prior exposure). For repos where the agent works repeatedly, the model learns structure through experience faster than you can maintain a graph index. RIG is the most practical of the three — deterministic, build-system-aware, no learned components.

## Comments and Inline Documentation: Low Value for Agents

**"Do Not Treat Code as Natural Language"** (arXiv:2602.11671, 2026): Code has structural properties (AST, type systems, scope rules) that NLP techniques miss when treating it as flat tokens. Implication: structural information (imports, call chains, types) is more useful than prose comments for agent navigation.

**AGENTIF** (arXiv:2505.16944, 2025): Long system prompts and tool constraints are followed poorly. Tool and condition constraints especially weak. More instructions != better performance. This applies to inline comments too — they're instructions embedded in context.

**Practitioner consensus:** Nobody in the Claude Code ecosystem recommends adding comments for agents. The dominant pattern is an external architecture map (CLAUDE.md), not inline annotations.

## Progressive Summarization (RAPTOR for Code): Not Needed

Nobody has published a RAPTOR implementation for codebases. The closest:

- **RepoScope** (arXiv:2507.14791, 2025): Call-chain-aware multi-view context. Builds hierarchy from call graphs, not text summarization. More structural than RAPTOR.
- **Context Inlining** (arXiv:2601.00376, 2026): Inline the context directly instead of retrieving it. Simpler, works better for current context windows.

**Why RAPTOR hasn't taken off for code:** Code has a native hierarchical structure (modules -> files -> classes -> methods -> lines) that prose doesn't. You don't need learned summarization when the AST gives you a lossless hierarchy for free. The question is how to expose that hierarchy cheaply.

The existing **Plan & Clear** pattern and `.claude/overviews/` (Gemini-generated repo summaries) are effectively manual RAPTOR — pre-digested context at the repo level. Already deployed.

## What Actually Works (Evidence-Ranked)

| Technique | Evidence | ROI | Bitter-lesson-proof? |
|-----------|----------|-----|---------------------|
| Descriptive file names | Agent-pliability skill (validated), "One Tool" paper | High | Yes — names are the cheapest index |
| Architecture map (CLAUDE.md) | Universal in Claude Code ecosystem | High | Yes — intent/architecture can't be derived |
| Native grep/glob tools | "One Tool Is Enough", Claude Code architecture | High | Yes — model improves at using them |
| Semantic folder structure | All practitioner guides | Medium | Yes — helps humans too |
| `.claude/overviews/` summaries | Deployed, manual RAPTOR equivalent | Medium | Partial — context windows may obviate |
| Call graph / dependency tools | CodexGraph, RIG show benchmark gains | Medium | No — models will learn to derive this |
| AST/tree-sitter as agent tool | No published evidence | Unknown | Maybe — plausible but unvalidated |
| Inline code comments for agents | No evidence; AGENTIF shows instruction overload hurts | Low | No — may actively hurt |
| Progressive summarization | No code implementation exists | Low | No — native code hierarchy is better |
| Custom retrieval pipelines | "One Tool" paper shows RL beats them | Low | No — models learn to search |

## The Cheap Tool That Might Be Worth Building

A `repo-outline` CLI (tree-sitter or AST-based) that dumps class/function signatures per file without reading full source. This would let agents sample structure at ~1/10th the token cost of reading files. No published evidence it helps, but:
- Zero maintenance (reads live code, no index to update)
- Trivially abandonable if models make it unnecessary
- Fills the gap between "ls" (file names only) and "read file" (full source)

Already exists in some form: `ctags`, `tree-sitter` CLI, `pyright --outputjson`. Not packaged as an agent tool. Low cost to wire up, easy to kill.

## Implications for Our Repos

1. **Keep investing in file naming and folder semantics.** Agent-pliability skill is the right tool. Run it on code repos, not just docs.
2. **CLAUDE.md architecture maps are the highest-value artifact.** They encode intent and "which files for which tasks" — genuinely un-derivable from source alone.
3. **Don't add comments for agents.** If code needs comments for humans, fine. But agent-specific annotations are noise that won't survive the next model.
4. **Don't build a graph database or custom retrieval pipeline.** The bitter lesson will eat these within 1-2 model generations.
5. **Consider a lightweight `repo-outline` tool.** AST-based, zero-maintenance, easy to abandon. Package as MCP or CLI.
6. **Keep `.claude/overviews/` current.** They're the cheapest form of hierarchical summarization and already deployed.

## Open Questions

- **Does tree-sitter outline actually reduce agent tool calls?** Measurable with session-analyst: compare tool-call count on repos with/without outline tool.
- **At what repo size do architecture maps become necessary?** Small repos (<50 files) may not benefit. Threshold unknown.
- **Will Claude Code ship native code structure tools?** Anthropic is aware of this gap. If they ship it, all custom work is wasted.

## Sources

- [SOURCE: arXiv:2512.20957] "One Tool Is Enough" — RL agent beats multi-tool setups
- [SOURCE: arXiv:2602.11671] "Do Not Treat Code as Natural Language"
- [SOURCE: arXiv:2601.10112] Repository Intelligence Graph (RIG)
- [SOURCE: arXiv:2408.03910] CodexGraph — graph databases for repo navigation
- [SOURCE: arXiv:2504.10046] GraphCodeAgent — dual graph-guided agent
- [SOURCE: arXiv:2505.16944] AGENTIF — instruction overload for agents
- [SOURCE: arXiv:2603.03329] AutoHarness — weaker model + better harness
- [SOURCE: arXiv:2601.00376] Context Inlining — inline vs retrieve
- [SOURCE: arXiv:2507.14791] RepoScope — call-chain-aware multi-view
- [SOURCE: browser-use.com/posts/bitter-lesson-agent-frameworks] Browser Use bitter lesson
- [SOURCE: hex.tech/blog/bitter-lessons] Hex AI product lessons
- [SOURCE: arXiv:2602.00933] MCP-Atlas — tool discovery failures
- [SOURCE: arXiv:2602.14878] MCP tool descriptions study

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: 891bf72cd596


end-knowledge-index -->
