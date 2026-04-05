---
title: "CORAL: Autonomous Multi-Agent Evolution via Shared Persistent Memory"
date: 2026-04-05
tags: [multi-agent, memory, coordination, autoresearch]
status: complete
---

# CORAL: Autonomous Multi-Agent Evolution (arXiv:2604.01658)

**Authors:** Ao Qu + 16 co-authors
**Source:** [arxiv.org/abs/2604.01658](https://arxiv.org/abs/2604.01658) (135 views on alphaXiv)

## What CORAL Does

First framework for autonomous multi-agent evolution on open-ended optimization problems. Long-running agents explore, reflect, and collaborate through shared persistent memory, asynchronous execution, and heartbeat-based interventions. SOTA on 10/11 diverse tasks (math, algorithmic, systems optimization), 3-10x higher improvement rates with fewer evaluations than fixed evolutionary baselines.

## Memory Architecture

Filesystem-based, structured as `.coral/public/` with three directories:

| Directory | Content | Format |
|-----------|---------|--------|
| `attempts/` | Historical evaluations + solutions | JSON, keyed by commit hash |
| `notes/` | Observations, learnings, reflections | Markdown |
| `skills/` | Reusable procedures, tools, patterns | Executable artifacts + descriptions |

**Access:** Symlinks from each agent's isolated worktree → centralized `.coral/public/`. Agents read/write via native tools (Bash, file I/O) — no special API.

**Conflict avoidance by design:** Unique filenames per attempt (commit hash key), unique filenames for notes/skills. No explicit locking needed. Authors report zero file-level conflicts across agents.

## Coordination Protocol

**No direct agent communication.** Coordination is entirely through shared memory — agents write attempts/notes/skills, other agents later retrieve them as context. This indirect coordination increases exploration diversity while enabling knowledge accumulation.

**Heartbeat interventions** (periodic prompts injected into agent context):
1. **Per-iteration reflection** — record observations during work
2. **Periodic consolidation** (every 10 evals) — review progress, organize notes, distill procedures into skills
3. **Stagnation-triggered redirection** (after 5 non-improving evals) — prompt strategy reassessment

## Isolated Workspaces

Each agent operates in a separate **git worktree** with its own branch. Symlinks provide shared memory visibility while preventing code interference.

## Results

- SOTA on 10 diverse tasks
- 3-10x higher improvement rates vs fixed evolutionary baselines
- Anthropic kernel benchmark: 4 co-evolving agents improved best score from 1363 → 1103 cycles
- Gains attributed to knowledge reuse and multi-agent exploration diversity

## Comparison to Our Architecture

| Aspect | CORAL | Our infrastructure |
|--------|-------|--------------------|
| **Shared memory format** | `.coral/public/` (attempts/notes/skills dirs) | `MEMORY.md` + `improvement-log.md` + `research/` |
| **Memory structure** | Three directories, flat files | Index file + individual memory files |
| **Access mechanism** | Symlinks + native tools | Direct file read/write |
| **Conflict avoidance** | Unique filenames (commit hash keys) | Append-only for improvement-log; git for others |
| **Agent isolation** | Git worktrees per agent | `isolation: "worktree"` for subagents |
| **Coordination** | Indirect via shared files | Indirect via shared files + orchestrator queue |
| **Heartbeats** | Periodic consolidation + stagnation detection | Session-analyst (post-hoc, not injected) |
| **Stagnation handling** | After 5 non-improving evals → redirect prompt | Manual (human notices + steers) |

**Key architectural parallels:**
- Both use filesystem-as-memory with native tool access (not a special API)
- Both use git worktrees for agent isolation
- Both avoid locks via unique naming conventions
- Both coordinate indirectly through shared state, not direct messaging

**What CORAL has that we don't:**
1. **Heartbeat-based stagnation detection** — automatic redirect after N non-improving attempts. Our autoresearch has stall detection but it's per-run, not cross-agent.
2. **Skills directory as shared memory** — agents distill procedures into reusable skills that other agents consume. Our skills are author-curated, not agent-generated from experience.
3. **Periodic consolidation prompts** — forced synthesis every N evaluations. Our session-analyst runs post-hoc, not mid-session.

**What we have that CORAL doesn't:**
1. **Typed memory with semantic indexing** — MEMORY.md with frontmatter vs flat directories
2. **Human curation layer** — improvement-log requires 2+ session recurrence before becoming rules
3. **Cross-session provenance** — git trailers, Session-ID, Evidence headers

## Verdict: **Extract pattern — heartbeat consolidation**

The stagnation detection + periodic consolidation pattern is the main takeaway. Implementation path: a hook or injected prompt that fires every N tool calls during long sessions, prompting the agent to review progress and adjust strategy. This is architecturally similar to our autocompact thrash detection but for cognitive stagnation rather than context limits.

The skills-from-experience pattern (agents writing skills during work) is interesting but premature for us — our curation layer exists for quality reasons (Constitution principle: findings require 2+ session recurrence).

<!-- knowledge-index
generated: 2026-04-05T23:39:54Z
hash: 63f5fe84f027

title: CORAL: Autonomous Multi-Agent Evolution via Shared Persistent Memory
status: complete
tags: multi-agent, memory, coordination, autoresearch

end-knowledge-index -->
