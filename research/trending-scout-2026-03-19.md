# Trending Scout — 2026-03-19

**Date:** 2026-03-19
**Categories scraped:** All languages (daily), Python (weekly), Rust (weekly), TypeScript (weekly)
**Total repos seen:** ~55
**Picks evaluated:** 10
**Prior art:** `cognee-technical-assessment.md` (reused), `anthropic-tooling-landscape.md` (referenced)

---

## Candidates (ranked by value - maintenance)

### 1. anthropics/claude-plugins-official

| Field | Content |
|-------|---------|
| Repo | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) (12,776 stars, Python, no license listed) |
| What it does | Official Anthropic-managed plugin directory for Claude Code. Plugins bundle MCP servers + slash commands + agents + skills into a single installable unit. 30 internal plugins (Anthropic), 13 external (3rd party). Install via `/plugin install {name}@claude-plugins-official`. |
| Why relevant | **We build Claude Code skills.** The plugin system is the canonical distribution mechanism. Plugin structure: `.claude-plugin/plugin.json`, `.mcp.json`, `commands/`, `agents/`, `skills/`. Several of our skills already exist as official plugins: `claude-md-management`, `code-review`, `frontend-design`, `playground`, `skill-creator` (our `skill-authoring`). |
| Integration path | **Direct adoption.** Compare our skill versions against official plugin versions. Adopt plugin format for new skills. Consider publishing our unique skills (researcher, epistemics, causal-dag, brainstorm, entity-management) as plugins. |
| Current overlap | `anthropic-tooling-landscape.md` already documented this (line 191). Our skills directory (`~/Projects/skills/`) uses symlinks, not the plugin system. Five of our skills have official Anthropic counterparts. |
| Maintenance cost | Near-zero — it's a format/distribution change, not new infrastructure. |
| Verdict | **Adopt.** Audit our 5 overlapping skills against official versions. Migrate to plugin format for new skills. Understand what the official versions do differently (they may be better). |

### 2. NousResearch/hermes-agent

| Field | Content |
|-------|---------|
| Repo | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (9,114 stars, MIT, Python) |
| What it does | Self-improving AI agent by Nous Research. Autonomous skill creation from experience. Skills self-improve during use. FTS5 session search with LLM summarization. Built-in cron scheduler. Multi-platform gateway (Telegram/Discord/Slack/WhatsApp). Honcho dialectic user modeling. Compatible with agentskills.io open standard. 6 terminal backends (local, Docker, SSH, Daytona, Singularity, Modal). Research-ready: batch trajectory generation, Atropos RL environments. |
| Why relevant | **Highest pattern overlap with our infrastructure.** They independently built: (1) skill creation from experience ≈ our session-analyst → implement loop, (2) FTS5 session search ≈ our sessions.py, (3) cron scheduling ≈ our orchestrator.py, (4) skill self-improvement ≈ our improvement-log pipeline, (5) subagent delegation ≈ our Agent tool patterns. This is convergent evolution — different codebase, same architecture. |
| Integration path | **Extract patterns.** Key mechanisms to study: how skill self-improvement works during use (not just post-hoc analysis), Honcho user modeling (could improve our MEMORY.md user memories), agentskills.io standard (interop), Atropos RL for trajectory generation. |
| Current overlap | No prior evaluation in our research/. High functional overlap but completely different stack (they're model-agnostic, we're Claude Code native). |
| Maintenance cost | Pattern extraction = zero. Dependency adoption = too divergent from our stack. |
| Verdict | **Extract patterns.** Deep-dive their skill self-improvement mechanism and Honcho user modeling. Check agentskills.io spec for interop. |

### 3. ChromeDevTools/chrome-devtools-mcp

| Field | Content |
|-------|---------|
| Repo | [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) (30,313 stars, Apache 2.0, TypeScript) |
| What it does | Official Google MCP server for Chrome DevTools. Puppeteer-based. Performance trace recording with actionable insights, network request analysis, screenshots, console messages with source-mapped stack traces. Slim mode for basic browser tasks. CrUX field data integration. |
| Why relevant | We use `claude-in-chrome` for browser automation. This is complementary — chrome-devtools-mcp adds performance profiling, network analysis, and DevTools-level debugging that page-interaction MCPs don't provide. Our QA skill could benefit from performance diagnostics. |
| Integration path | **Adopt (complementary).** Add to global MCP config alongside claude-in-chrome. Use chrome-devtools-mcp for debugging/QA performance analysis, claude-in-chrome for interaction. Slim mode available for lighter footprint. |
| Current overlap | We have claude-in-chrome MCP (page interaction, screenshots, form filling). No performance profiling, no network analysis, no source-mapped console traces. |
| Maintenance cost | Low — just MCP config entry. Node.js dep (already in environment). |
| Verdict | **Adopt.** Add to MCP config. Use `--slim` for basic, full for QA workflows. |

### 4. obra/superpowers

| Field | Content |
|-------|---------|
| Repo | [obra/superpowers](https://github.com/obra/superpowers) (98,908 stars, MIT, Shell) |
| What it does | Complete software development workflow as composable skills. 14 skills: brainstorming → spec → git worktree → plan → subagent-driven-development → TDD → code review → merge. Skills trigger automatically. Available as Claude Code plugin, Cursor plugin, Codex install, Gemini extension. |
| Why relevant | 98K stars = most popular agentic skills framework. Their "subagent-driven-development" pattern (fresh subagent per task, two-stage review: spec compliance then code quality) is worth studying. However, our skills are more domain-specific (epistemics, causal-dag, research, entity-management) while theirs are generic software dev methodology. |
| Integration path | **Extract pattern** (subagent-driven-development two-stage review loop). Don't adopt wholesale — our skills serve different purposes (domain-specific intelligence vs generic dev workflow). Could install as a plugin for pure software development tasks where our skills don't apply. |
| Current overlap | Partial overlap: our `brainstorm`, `code-review`, `qa` skills. Their "using-git-worktrees" overlaps with our worktree patterns. But scope is fundamentally different — they're a methodology, we're infrastructure + domain skills. |
| Maintenance cost | Plugin = zero if just installed. Pattern extraction = zero. |
| Verdict | **Watch + extract patterns.** Study subagent-driven-development review loop. Consider installing as plugin for pure dev tasks, but don't replace our domain skills. |

### 5. promptfoo/promptfoo

| Field | Content |
|-------|---------|
| Repo | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) (17,646 stars, MIT, TypeScript) |
| What it does | CLI for LLM prompt evaluation and red teaming. Declarative YAML configs for test suites. Model comparison. Red team/vulnerability scanning. CI/CD integration. Code scanning for LLM security. **Acquired by OpenAI March 16, 2026** (remains OSS/MIT). |
| Why relevant | Could complement our epistemic measurement scripts. Promptfoo tests prompt outputs (correctness, safety, consistency). Our scripts measure agent behavior (calibration, trace faithfulness, sycophancy, pushback). Different scope but potential overlap in eval infrastructure. |
| Integration path | **Complementary.** Could use promptfoo for regression testing of skill prompts or CLAUDE.md changes (does this instruction still produce the intended behavior?). Our epistemic scripts would remain for behavioral measurement. Red teaming capability is novel — we have nothing equivalent. |
| Current overlap | Different scope. Our calibration-canary.py, trace-faithfulness.py, pushback-index.py measure behavioral properties. Promptfoo measures output properties. No direct replacement. |
| Maintenance cost | npm dependency. OpenAI acquisition adds uncertainty about long-term direction. |
| Verdict | **Watch.** Useful for prompt regression testing if we ever need it. Red teaming capability unique. OpenAI acquisition makes long-term trajectory unclear. |

### 6. volcengine/OpenViking

| Field | Content |
|-------|---------|
| Repo | [volcengine/OpenViking](https://github.com/volcengine/OpenViking) (16,274 stars, Apache 2.0, Python) |
| What it does | "Context Database" for AI agents by ByteDance/Volcengine. Filesystem paradigm for organizing memories/resources/skills. L0/L1/L2 tiered context loading. Visualized retrieval trajectories. Automatic session compression + long-term memory extraction. Requires Python 3.10+, Go 1.22+, C++ compiler. |
| Why relevant | L0/L1/L2 tiered context loading mirrors our repo_tools_mcp's tiered approach (summary → outline → callgraph). "Visualized retrieval trajectory" for debugging context retrieval is interesting — we don't have observability into what context gets loaded and why. Automatic session compression → memory extraction is what our compaction + MEMORY.md attempts to do manually. |
| Integration path | **Extract pattern** (visualized retrieval trajectory, automatic memory extraction from sessions). Skip as dependency — Go + C++ + Python is too heavy, and our tiered loading already works. |
| Current overlap | repo_tools_mcp does tiered loading (L0 summary, L1 overview, L2 outline/callgraph/imports). No retrieval trajectory visualization. No automatic memory extraction from sessions. |
| Maintenance cost | Dependency = very high (Go + C++ + Python + VLM + embedding model). Pattern extraction = zero. |
| Verdict | **Extract patterns.** Retrieval trajectory visualization and auto-memory extraction are worth building natively. Skip as dependency. |

### 7. langchain-ai/deepagents

| Field | Content |
|-------|---------|
| Repo | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) (15,540 stars, MIT, Python) |
| What it does | "Batteries-included" agent harness by LangChain. Planning (write_todos), filesystem tools (read/write/edit/ls/glob/grep), shell access, sub-agents (task), auto-summarization for long contexts. Built on LangGraph. Also has CLI with web search, persistent memory, human-in-the-loop. |
| Why relevant | Feature set is strikingly similar to Claude Code itself — planning, file access, shell, sub-agents, context management. Their `task` tool = our Agent tool. Their `write_todos` = our plan files. Main value: it's how LangChain thinks about agent architecture, which is worth understanding as a reference. |
| Integration path | **Pattern extraction only.** Auto-summarization approach (save large outputs to files automatically) is a pattern we could steal. Task delegation with isolated context windows is done differently than our Agent tool. |
| Current overlap | Very high conceptual overlap with Claude Code + orchestrator. LangGraph dependency = incompatible stack. |
| Maintenance cost | N/A — not adopting. |
| Verdict | **Skip.** We already have this via Claude Code natively. Minor pattern: auto-save large outputs to files. |

### 8. topoteretes/cognee

| Field | Content |
|-------|---------|
| Repo | [topoteretes/cognee](https://github.com/topoteretes/cognee) (14,358 stars, Apache 2.0, Python) |
| What it does | Knowledge engine combining vector search + graph databases. Ingest data → LLM-based entity extraction → knowledge graph → semantic + graph search. Backends: Kuzu (embedded), Neo4j, NetworkX. Multi-tenant, OTEL tracing. |
| Why relevant | Competes with our knowledge substrate. |
| Integration path | See `research/cognee-technical-assessment.md` for full analysis. |
| Current overlap | **Already assessed in detail.** Verdict from prior assessment: "Your current substrate is better for specialized domains. Manual registration with provenance tracking produces higher-quality knowledge graphs than LLM auto-extraction for domains where precision matters." |
| Maintenance cost | 40+ transitive dependencies, pre-1.0 API, breaking changes. |
| Verdict | **Skip** (reaffirm prior assessment). If graph traversal needed, use Kuzu standalone (1 dep) instead of full Cognee (40+ deps). |

### 9. vectorize-io/hindsight

| Field | Content |
|-------|---------|
| Repo | [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) (5,083 stars, MIT, Python) |
| What it does | Agent memory system focused on learning, not just recall. SOTA on LongMemEval benchmark. Three-operation API: Retain (store), Recall (search), Reflect (disposition-aware response generation). Docker + PostgreSQL backend. LLM wrapper for automatic memory. |
| Why relevant | "Reflect" as a distinct operation from "Recall" is a novel pattern. Standard memory systems retrieve then generate; Hindsight generates responses that are memory-aware in a single step. Benchmarked with independent reproduction (Virginia Tech). |
| Integration path | **Extract pattern** ("Reflect" operation). Our memory system does recall (search MEMORY.md, read rules) but doesn't have a "generate response informed by learned dispositions" step. |
| Current overlap | Our memory: MEMORY.md + rules files + knowledge substrate. No "Reflect"-like operation. Docker + PostgreSQL = too heavy for our setup. |
| Maintenance cost | Dependency = high (Docker + PostgreSQL). Pattern extraction = zero. |
| Verdict | **Extract pattern.** The Retain/Recall/Reflect trichotomy is worth considering for our memory architecture. Skip as dependency. |

### 10. cocoindex-io/cocoindex

| Field | Content |
|-------|---------|
| Repo | [cocoindex-io/cocoindex](https://github.com/cocoindex-io/cocoindex) (6,559 stars, Apache 2.0, Rust + Python) |
| What it does | Declarative dataflow framework for data transformation. Rust core with Python API. Incremental processing (only recompute what changed). Data lineage out-of-box. No hidden state — all transformations observable. Exports to vector DBs, graph DBs. |
| Why relevant | Our data pipelines (runlog ingestion, session processing, research corpus building) are imperative Python scripts. CocoIndex's declarative + incremental approach could simplify re-processing on schema changes. |
| Integration path | **Pattern extraction** (incremental processing model). Our runlog.py and sessions.py already track "last imported" state. CocoIndex's approach is more systematic — track input hashes, reprocess only affected downstream. |
| Current overlap | Our pipelines use SQLite + custom "last_imported" tracking. CocoIndex requires PostgreSQL for state — blocker. |
| Maintenance cost | PostgreSQL dependency = blocker. Rust compilation adds build complexity. |
| Verdict | **Watch.** If they add SQLite backend, revisit. Pattern: hash-based incremental reprocessing is worth adopting in our scripts. |

---

## Patterns Observed

### 1. Agent memory is the hot category
Three of our top 10 are memory systems (OpenViking, cognee, hindsight). The ecosystem is converging on: memory should be structured (not just conversation history), should learn (not just store), and should be observable (not a black box).

### 2. Plugin ecosystems are maturing fast
Claude Code plugins, Superpowers (multi-platform), Hermes Agent skills. The "installable skill package" pattern is becoming standard across agent platforms. Our symlinked skills directory works but misses versioning, dependency management, and marketplace discovery.

### 3. Self-improvement loops are emerging independently
Hermes Agent's "skill creation from experience" and our session-analyst → improvement-log pipeline are convergent evolution. The pattern: observe agent behavior → extract learnings → create/improve skills → repeat. Multiple teams are arriving at the same architecture.

### 4. Tiered context loading is now a pattern
OpenViking L0/L1/L2, our repo_tools_mcp tiers, DeepAgents' context management. The "load only what you need, at the right granularity" pattern is becoming standard. We were early here.

### 5. Claude Code dominance in trending
4+ repos in trending are Claude Code-specific (plugins-official, superpowers as plugin, learn-claude-code, claude-hud, get-shit-done). The tooling ecosystem around Claude Code is exploding.

---

## Null Results

- **No new search/retrieval tools** worth adopting. Exa, Brave, S2, Perplexity remain the landscape.
- **No SQLite-native agent memory systems.** Everything uses PostgreSQL or vector DBs. Gap for lightweight memory.
- **No epistemic measurement tooling.** Promptfoo is closest but measures prompt outputs, not agent behavioral properties. Our calibration/trace-faithfulness/pushback scripts remain novel.
- **No cron-to-agent orchestrators** besides our orchestrator.py and Hermes Agent's built-in cron. Most agent frameworks assume human-initiated sessions.

---

## Action Items

1. **[high] Audit 5 overlapping skills vs official plugins:** claude-md-management, code-review, frontend-design, playground, skill-creator. Determine: are official versions better? Should we adopt, fork, or keep ours?
2. **[high] Deep-dive Hermes Agent self-improvement mechanism:** How does skill self-improvement during use work? What's the agentskills.io spec?
3. **[medium] Add chrome-devtools-mcp to global MCP config.** Complementary to claude-in-chrome.
4. **[medium] Study Superpowers subagent-driven-development pattern.** Two-stage review (spec compliance + code quality) for subagent work.
5. **[low] Consider plugin format for new skills.** Plugin distribution is the canonical mechanism now.
6. **[low] Build hash-based incremental reprocessing** for runlog/session ingestion (CocoIndex pattern).
