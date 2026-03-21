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

1. ~~**[high] Audit 5 overlapping skills vs official plugins.**~~ DONE — see Skill Overlap Audit below. Only 2 actual overlaps; 3 are already official-only.
2. ~~**[high] Deep-dive Hermes Agent self-improvement mechanism.**~~ DONE — see Hermes Agent Patterns below.
3. **[medium] Add chrome-devtools-mcp to frontend-heavy project configs.** Not global — scoped per user preference. Complementary to claude-in-chrome.
4. **[medium] Study Superpowers subagent-driven-development pattern.** Two-stage review (spec compliance + code quality) for subagent work.
5. **[low] Consider plugin format for new skills.** Plugin distribution is the canonical mechanism now.
6. **[low] Build hash-based incremental reprocessing** for runlog/session ingestion (CocoIndex pattern).

---

## Skill Overlap Audit (2026-03-19)

Compared our 5 skills with official Anthropic counterparts in `anthropics/claude-plugins-official`.

### State Before Audit

| Our skill | Official plugin | Already installed? |
|-----------|----------------|-------------------|
| `skill-authoring` (meta-local, 223 lines) | `skill-creator` (479 lines) | No |
| `code-review` (shared, 214 lines) | `code-review` (92 lines) | No |
| (none) | `frontend-design` (41 lines) | Yes |
| (none) | `playground` (76 lines) | Yes |
| (none) | `claude-md-management` (179+55 lines) | Yes |

3 of 5 "overlaps" were false — we never had custom versions of frontend-design, playground, or claude-md-management. Those are already purely official plugins.

### Verdicts

**1. skill-authoring (ours) vs skill-creator (official) → KEEP BOTH, complementary**

| Dimension | Ours (skill-authoring) | Official (skill-creator) |
|-----------|----------------------|------------------------|
| Focus | Design principles: progressive disclosure, per-step constraints, frontmatter reference, anti-patterns, L2/L3 extraction rubric | Eval-driven iteration: parallel with/without-skill runs, grading agents, benchmark aggregation, HTML viewer, description optimization |
| Teaches | HOW to design a good skill (architecture) | HOW to iterate until a skill works (measurement) |
| Unique value | Agent-Diff citation (+3.4 known vs +19 novel), L3 extraction decision rubric, constraint type taxonomy | Parallel baseline comparison, blind A/B testing, train/test description optimization, eval viewer HTML |
| Length | 223 lines (now ~240 with cross-reference) | 479 lines + agents/ + scripts/ + assets/ |

**Action taken:** Installed `skill-creator@claude-plugins-official`. Updated our `skill-authoring` to reference the official plugin for eval/iteration. Workflow: design with ours → iterate with `/skill-creator`.

**2. code-review (ours) vs code-review (official) → KEEP BOTH, different scope**

| Dimension | Ours | Official |
|-----------|------|----------|
| Purpose | Continuous proactive code quality review | PR-specific review |
| Model cost | Free (Gemini/Codex CLI) | Claude Code agents (Haiku + 5× Sonnet) |
| Workflow | Scout → validate → fix → commit | Triage → 5 parallel review angles → confidence score → PR comment |
| Trigger | `/loop` auto-rotation, 25-day cycle | Per-PR, responds to GH PRs |
| Input | Entire codebase, focused by topic | PR diff |
| Output | JSONL findings + committed fixes | PR comment with linked code |

Zero functional overlap. Ours is a continuous quality scanner using free models. Theirs is a PR reviewer using Claude Code's own agents. Both are useful — ours for proactive quality, theirs for reactive PR review (if we ever use PRs; currently all-main workflow).

**Not installed:** The official `code-review` plugin. Would only be useful if we adopt PR-based workflow.

**3-5. frontend-design, playground, claude-md-management → N/A**

We never had custom versions. Already using official plugins exclusively. No action needed.

### Summary

Only 2 actual overlaps out of 5. Both are complementary rather than competitive. No skills to retire. One plugin installed (skill-creator). The official code-review plugin serves a different use case (PRs) that doesn't apply to our all-main workflow.

---

## Hermes Agent Patterns (2026-03-19)

Extracted from `NousResearch/hermes-agent` (9.1K stars, MIT, Python).

### Skill Self-Improvement: Three-Layer Detection

Hermes uses entirely LLM-judged detection — no automated staleness analysis, no diff-based detection, no runtime eval framework.

**Layer 1: System prompt instructions** (`SKILLS_GUIDANCE` + `build_skills_system_prompt`)
- Injected into every agent turn when `skill_manage` tool is loaded
- Instructions: scan skills before acting, load matching skills, fix broken skills during use via `skill_manage(action='patch')`, offer to save complex tasks as skills
- Key quote: "Skills that aren't maintained become liabilities"

**Layer 2: Iteration-based nudge** (counter in `run_agent.py`)
- Tracks tool-calling iterations per agent turn
- After N iterations (default 15, configurable via `skills.creation_nudge_interval`), injects system message into next user message:
  > "Save the approach as a skill if it's reusable, or update any existing skill you used if it was wrong or incomplete."
- Counter resets when `skill_manage` is actually called

**Layer 3: Tool schema description** (in `skill_manage` tool definition)
- Create triggers: 5+ tool calls, errors overcome, user-corrected approach
- Update triggers: stale instructions, OS-specific failures, missing steps/pitfalls found during use
- 6 actions: create, patch (preferred), edit, delete, write_file, remove_file

**Security:** Every skill write runs through `skills_guard.py` — trust levels for builtin/trusted/community/agent-created. Agent-created skills blocked on "dangerous" findings, allowed on safe+caution.

### Comparison to Our Pipeline

| Aspect | Hermes | Our infrastructure |
|--------|--------|-------------------|
| Detection timing | During use (real-time) | Post-hoc (session-analyst) |
| Detection method | LLM-judged prompts | Structured analysis of transcripts |
| Improvement actor | Same agent that found the issue | Human reviews → implements in target repo |
| Quality gate | Security scan only | 2+ recurrence, checkable predicate, not already covered |
| Skill creation | Agent creates directly | Human designs, agent assists |

**Assessment:** Hermes's real-time skill patching is faster but lower quality — no recurrence requirement, no human review. Our post-hoc pipeline is slower but produces higher-quality improvements (constitutional principle: "instructions alone = 0% reliable"). Their iteration nudge (inject reminder after N tool calls) is a pattern worth considering — it's essentially a timeout-based prompt to reflect.

### agentskills.io Standard

The open standard (originally from Anthropic) is now adopted by ~30 products including Claude Code, Codex, Cursor, GitHub Copilot, Gemini CLI, JetBrains Junie, and others.

**Format:** Identical to our SKILL.md format — YAML frontmatter (name + description required) + Markdown body + optional scripts/, references/, assets/ directories. The 3-tier progressive disclosure model matches ours exactly. We are already compliant.

**Client implementation guide** specifies:
- Discovery: scan `.<client>/skills/` and `.agents/skills/` (cross-client convention)
- Project-level skills override user-level (our symlinks already do this)
- Trust gating for project-level skills from untrusted repos

**Eval framework** (`evals/evals.json`): Test cases with prompts, expected outputs, files, and assertions. Separate offline process for skill authors — matches what the `skill-creator` plugin automates.

**Hermes extensions** (not in base standard):
- Conditional activation: `fallback_for_toolsets`, `requires_toolsets` (show skill only when certain tools available/unavailable)
- Platform restrictions: `platforms: [macos, linux]`
- Env var setup on load: `required_environment_variables` with prompts
- Multi-registry hub integration with security scanning

**Implications for us:**
1. Our skills are already agentskills.io compliant — no format changes needed
2. The `skill-creator` plugin now provides the eval framework the standard recommends
3. Hermes's conditional activation (`requires_toolsets`) is a pattern we lack — could be useful for skills that depend on specific MCPs
4. Publishing our unique skills (researcher, epistemics, causal-dag, brainstorm, entity-management) to the standard ecosystem is technically trivial — they're already in the right format

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: aa6d4beb1151

cross_refs: research/cognee-technical-assessment.md

end-knowledge-index -->
