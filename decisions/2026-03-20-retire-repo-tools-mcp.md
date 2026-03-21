---
id: 2026-03-20-retire-repo-tools-mcp
concept: repo-navigation
repo: meta
decision_date: 2026-03-20
recorded_date: 2026-03-20
provenance: contemporaneous
status: accepted
initial_leaning: keep MCP, improve tool descriptions
relations: []
---

# 2026-03-20: Retire repo-tools MCP — CLI/Bash beats MCP for generic scripts at this repo scale

## Context

repo-tools MCP (7 tools, 1,442 LOC in `scripts/repo_tools_mcp.py`) was configured in 8 projects. Zero recorded usage across 4,287 runs. Meanwhile agents use Read (24.5k), Grep (5.6k), Glob (2.6k), and Bash (50.3k) directly.

Research on context bundling tools (repomix, aider repo-map, ContextPacker, jCodeMunch) identified patterns worth selective adoption but confirmed that MCP wrapper overhead is not justified at current repo sizes (17-339 files).

## Alternatives considered

1. **Improve MCP tool descriptions** — better names, shorter descriptions, usage examples. Rejected: the tools solve a problem agents don't have at this scale. Read+Grep is faster and more flexible.
2. **Remove MCP, delete scripts** — rejected: scripts have value as CLI tools via Bash. `repo-outline.py` already referenced in codebase-map.md.
3. **Remove MCP, keep scripts as CLI, add `symbol` subcommand** — chosen. Eliminates 7 MCP tool definitions consuming context tokens per session while preserving useful functionality.
4. **Replace with PageRank symbol graph (aider pattern)** — not yet justified at 17-339 files. Re-evaluate at 500+.
5. **Canary/staged deprecation** — MCP re-addition is a one-line JSON edit. Low blast radius doesn't warrant staged rollout.

## Decision

- Removed `"repo-tools"` from `.mcp.json` in all 8 projects
- Kept `scripts/repo_tools_mcp.py` on disk (trivial to re-activate)
- Added `symbol` subcommand to `repo-outline.py` (AST-based, with grep fallback)
- Added `--compact` flag to `repo-summary.py` (collapse dirs >20 files, max 3 depth)
- Added lightweight telemetry (`~/.cache/repo-tools-usage.jsonl`) to track CLI usage
- Wired `--compact` into `repo-index-refresh.json` pipeline for genomics and intel

## Evidence

- Runlog query: 0 `mcp__repo-tools__*` tool uses across 4,287 runs
- 7 MCP tool definitions × 8 projects = 56 tool descriptions loaded into context per session, never used
- Research memo: `research/context-bundling-solutions.md`
- Cross-model review: `.model-review/2026-03-20-repo-tools-overhaul-1c073c/`

Key learning: **CLI/Bash > MCP for generic scripts on repos this size.** MCP adds value when tools need structured input/output or discovery. For "run this script on this path," agents already have Bash.

## Revisit if

- Repo sizes exceed 500 files (PageRank symbol graph becomes worthwhile)
- MCP protocol adds discovery features that reduce context cost of tool definitions
- A new MCP pattern emerges that agents prefer over Bash for repo navigation

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: 134b2304ffe7

status: accepted
cross_refs: research/context-bundling-solutions.md

end-knowledge-index -->
