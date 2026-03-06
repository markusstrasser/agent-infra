# Claude Code Architecture: Research Notes

**Date:** 2026-02-27, **updated 2026-03-05** (Jan-Mar 2026 changelog sweep, v2.1.68–2.1.70)
**Sources:** Anthropic engineering blog, claude-code-docs bundle, Trail of Bits config, incident.io blog, decodeclaude.com, community posts, 50+ GitHub repos (99%+ slop filtered out), official changelog (code.claude.com/docs/en/changelog), GitHub releases (anthropics/claude-code), Agent SDK Python changelog (anthropics/claude-agent-sdk-python)

---

## The Mental Model

Claude Code is a **context-limited agent**. Every design decision flows from one constraint: the context window is finite and recall degrades as it fills. The entire architecture — rules, skills, hooks, subagents, MCP — exists to manage what's in the window at any given moment.

**Progressive disclosure** is the organizing principle:
- CLAUDE.md: always loaded (~200 lines max, every line costs every turn)
- `.claude/rules/`: path-scoped, loaded only when relevant files are active
- `.claude/skills/`: on-demand, loaded only when invoked
- Hooks: deterministic, zero context cost (run outside the model)
- Subagents: isolated context windows, return 1-2K token summaries
- MCP servers: external tools, schema consumes context on first use

## What Anthropic Actually Does Internally

### Context Engineering (Sep 2025 blog)
- **Context rot is continuous, not a cliff.** Recall accuracy degrades as token count increases. n-squared pairwise relationships stretch thin.
- **Microcompaction**: Tool outputs (Read, Bash, Grep, etc.) go from "hot tail" (recent, inline) to "cold storage" (disk-referenced). Only the 5 most recently accessed files get re-read after compaction.
- **"If a human engineer can't definitively say which tool should be used, an AI agent can't either."** Bloated tool sets are worse than no tools. Limit MCP servers to 2-3 active.

### Long-Running Agents (Nov 2025 blog)
- **Two-agent architecture**: Initializer creates `init.sh` + `claude-progress.txt` + baseline git commit. Coding agent reads these on every new session. No fancy memory — just files and git.
- **Feature list as JSON with `passes` boolean**: Agents can only flip the flag, never delete features. Prevents premature "done" declarations.
- **One-shotting is the core failure mode**: Agents exhaust context mid-feature, leave undocumented half-work. Fix: force incremental, documented progress.
- **Browser automation (Puppeteer MCP) caught bugs unit tests missed.** Without e2e, Claude marks features "complete" prematurely.

### Internal Usage Data (Dec 2025 study)
- **67% increase in merged PRs/engineer/day**. But 27% of Claude-assisted work is entirely new tasks that wouldn't have been done otherwise.
- **Skill atrophy is real.** Senior Anthropic engineers flagged it explicitly: "When producing output is so easy, it gets harder to actually learn."
- **Supervision paradox**: Using Claude well requires skills that atrophy from using Claude.
- **Claude replaced colleague questions.** Junior engineers stopped asking seniors. Mentorship decreased measurably.
- **Variable time savings**: Some engineers spend MORE time debugging Claude's output than writing it themselves.

## Compaction System Internals

Source: decodeclaude.com reverse engineering + docs bundle.

### Three layers:
1. **Microcompaction**: Tool output → disk. Hot tail (recent) stays inline, older outputs become file references.
2. **Auto-compaction**: Triggers at ~64-75% context usage (not 90% as previously assumed). Reserves buffer for both output AND the compaction workflow itself.
3. **Manual**: `/compact` command.

### Compaction contract (what the summary MUST include):
- User intent (what are we trying to accomplish)
- Technical decisions made
- Files touched (read and modified)
- Errors encountered
- Pending tasks
- Next steps

### Rehydration sequence after compaction:
1. Boundary marker
2. Compressed summary
3. Re-read 5 most recently accessed files
4. Todo list state
5. Plan state
6. Hook outputs

### "Plan & Clear" as compaction alternative (product-native + community-validated):

Claude Code has a **native "clear context and execute plan (.md)"** option that appears at context limits. This is the product-validated version of the pattern: save a structured plan to a .md file, wipe the context window entirely, then execute from the clean plan file. No lossy summarization — the plan IS the state.

This is distinct from the other context-limit option ("summarize and continue") which is auto-compaction — lossy by definition.

**Three variants, worst to best:**

1. **Auto-compaction** ("summarize and continue") — the compaction algorithm decides what survives. Lossy, opaque, model-dependent. Community consensus: "error-prone and not well-optimized."
2. **Manual Document & Clear** — you tell Claude what to write to a handoff doc, then `/clear`. You control what survives. Community workaround.
3. **Native Plan & Clear** ("clear context and execute plan (.md)") — Claude writes a structured plan to .md, context clears, execution resumes from plan file. Product-native. Anthropic validated this as the right pattern by building it in.

**Why Plan & Clear beats compaction:** Compaction is lossy summarization (confirmed by RLM analysis, arXiv:2512.24601 — "never summarize, delegate instead"). Plan & Clear preserves structured intent, not a degraded summary. The plan file is also inspectable, editable, and version-controllable — you can read it, fix it, or reject it before execution resumes.

**Practical implication:** When context gets heavy, prefer the "clear context and execute plan" option over "summarize and continue." The plan file becomes a checkpoint you can audit.

[SOURCE: Claude Code native UI, blog.sshh.io, ykdojo/claude-code-tips, sankalp.bearblog.dev]

### Key insight (hyperdev.matsuoka.com):
Recent Claude Code performance improvements may come from **reserving more free context for reasoning** rather than better models. When Claude Code reported 10% remaining, independent measurement showed 36% free. The "completion buffer" prevents disruptive mid-operation compaction.

## Community-Validated Patterns (Feb 2026 Reddit/Blog Sweep)

Sources: [Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature), [Sankalp](https://sankalp.bearblog.dev/my-experience-with-claude-code-20-and-how-to-get-better-at-using-coding-agents/), [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips), [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code), r/ClaudeAI sweep.

### MCP Design: Data Gateways, Not API Mirrors
Abandon bloated MCPs that mirror REST endpoints. Each MCP should expose 1-2 high-level tools (raw data dump), not 15 CRUD operations. Let agents script against the data.

**Rule of thumb:**
- Stateful environments (Playwright, browsers, databases) → MCP
- Stateless integrations (Jira, AWS, GitHub, git) → CLI tools

This aligns with the MCP tool description study (arXiv:2602.14878): poor descriptions degrade agent performance. Fewer, well-described tools > many poorly-described ones. [SOURCE: blog.sshh.io]

### Parallel Bash Over Multi-Agent Orchestration
For large refactors, write bash scripts calling `claude -p "in /pathA change all refs from foo to bar"` in parallel. More scalable and controllable than a single agent managing dozens of subtasks or multi-agent orchestration.

**Why this works:** Google scaling study (arXiv:2512.08296) shows multi-agent improves parallelizable tasks +81%. Parallel bash IS parallelization — without coordination overhead, error amplification, or context sharing. Each instance gets a clean context window. [SOURCE: blog.sshh.io]

### GHA Logs → Meta-Analysis Loop
Claude Code in GitHub Actions returns full agent logs. Mine them for failure patterns:
```bash
query-claude-gha-logs --since 5d | claude -p "find common mistakes and suggest CLAUDE.md fixes"
```
This implements our regret tracking concept (agent-failure-modes.md) architecturally — measuring corrections from production data instead of manually cataloging failures. [SOURCE: blog.sshh.io]

### Token Budgeting in CLAUDE.md
Treat CLAUDE.md like ad space. Assign max token counts per tool's documentation. If you can't explain a tool concisely, it isn't ready for the monorepo. Only tools used by 30%+ of engineers warrant core-file inclusion; everything else lives in skills or external docs referenced with "For X usage, see path/to/docs.md."

Reference implementation: 13KB CLAUDE.md for a team consuming billions of tokens/month. [SOURCE: blog.sshh.io]

### Tool Outputs Bloat Context Faster Than Tool Calls
Each search, file read, and edit produces output that stays in context. Agents "token guzzle" from accumulated outputs, not from asking questions. This is the primary mechanism behind subagent effectiveness — 50 file reads stay in the subagent's context; only a 1-2K summary enters yours.

**Practical implication:** Deploy subagents earlier than feels necessary. The exploration cost in the main window is the real expense, not the subagent invocation overhead. [SOURCE: sankalp.bearblog.dev]

### System Reminders as Recitation Strategy
Updating todo.md repeatedly refreshes goals into the model's recent attention window. This combats lost-in-the-middle effects in long contexts. Adapted from Manus's technique.

This is the recitation strategy from Du et al. (EMNLP 2025, arXiv:2510.05381) applied to context management — they measured +4% on RULER from prompting models to recite retrieved evidence before answering. Training-free, model-agnostic. [SOURCE: sankalp.bearblog.dev]

### Anti-Patterns Confirmed by Community

**`@`-mentioning entire files in CLAUDE.md:** Embedding full docs bloats context on every run. Instead: pitch the agent on WHEN to read external files. "For X usage or Y error, see path/to/docs.md for troubleshooting." [SOURCE: blog.sshh.io]

**Negative-only constraints:** "Never use --foo-bar" makes the model fixate on that flag. Always provide alternatives alongside prohibitions. [SOURCE: blog.sshh.io]

**Over-relying on auto-compaction:** `/compact` is "opaque, error-prone, and not well-optimized." Explicit `/clear` + "Document & Clear" (dump progress to markdown, restart fresh) is more trustworthy. Aligns with RLM's "never summarize" finding (arXiv:2512.24601). [SOURCE: blog.sshh.io, ykdojo]

**Custom subagents for everything:** Shrivu argues against custom subagents because they "gatekeep context" and force rigid workflows. Prefers generic `Task(...)` clones with full CLAUDE.md access, letting the agent decide when and how to delegate. This aligns with "simpler beats complex under stress" (ReliabilityBench). [SOURCE: blog.sshh.io]

### Notable Community Tools (Feb 2026)

| Tool | What it does | Why it matters |
|------|-------------|----------------|
| **claude-esp** | Streams hidden Claude output (thinking, tool calls, subagents) to separate terminal | Real-time debugging of agent reasoning |
| **Dippy** | AST-parses bash commands to auto-approve safe ones, prompts for destructive | Solves permission fatigue without sacrificing safety |
| **recall** | Full-text search across all Claude Code sessions with terminal UI | Better than basic `/resume` for finding past work |
| **Trail of Bits Security Skills** | CodeQL/Semgrep via skills for code auditing | Professional security analysis in agent workflow |
| **Ralph for Claude Code** | Autonomous loop framework with circuit breakers | Prevents infinite execution cycles |
| **cc-tools** | High-performance Go linting, testing, statusline generation | Minimal overhead tooling |

---

## Hook System (updated 2026-03-03)

### Four execution types:
1. **Command** (`type: "command"`): Shell script. Fast, deterministic. Exit 0 = proceed, exit 2 = block + feed error back.
2. **HTTP** (`type: "http"`): POST JSON to URL, receive JSON response. Added v2.1.63 (Feb 28). Cannot block via HTTP status alone — must return JSON body with decision fields.
3. **Prompt** (`type: "prompt"`): Single Haiku LLM call. Good for fuzzy classification (is this command destructive?).
4. **Agent** (`type: "agent"`): Subagent with Read/Grep/Glob access, 50 turns max. Full reasoning but expensive.

### Hook events (18 total, 10 can block):

**Tool lifecycle:**
- `PreToolUse`: Before any tool call. Matcher regex on tool_name. Can block, allow, ask, modify input, inject `additionalContext`.
- `PostToolUse`: After tool call succeeds. Can't block (already ran). Can modify MCP output via `updatedMCPToolOutput`.
- `PostToolUseFailure`: After tool call fails. Can't block. Added ~Jan 30.
- `PermissionRequest`: When permission is needed. Can auto-allow/deny. Added ~Feb 4. Matches tool name.

**Session lifecycle:**
- `SessionStart`: On startup/resume/clear/compact. Provides `source`, `model`, `agent_type`. Can inject `additionalContext`. Access to `CLAUDE_ENV_FILE` for persistent env vars.
- `SessionEnd`: On clear/logout/exit. No blocking. Matches exit reason.
- `PreCompact`: Before auto/manual compaction. No blocking. Matches `manual`|`auto`.
- `ConfigChange`: When config files change. CAN block config changes (except policy). Added Feb 19 (v2.1.49). Matches config source.

**Agent lifecycle:**
- `Stop`: When Claude thinks it's done. Exit 2 = keep going. `last_assistant_message` in input (v2.1.47).
- `SubagentStart`: When subagent spawns. No blocking. Matches agent type.
- `SubagentStop`: When subagent completes. Can block. `last_assistant_message`, `agent_id`, `agent_transcript_path`, `agent_type` in input.

**User:**
- `UserPromptSubmit`: Before Claude processes user prompt. Can block/erase prompt, inject context.
- `Notification`: On permission prompts, idle prompts, auth events, elicitation dialogs. No blocking.

**Agent Teams:**
- `TeammateIdle`: When teammate about to go idle. Exit 2 = keep working. Added Feb 6 (v2.1.33).
- `TaskCompleted`: When task marked complete. Exit 2 = prevent completion. Added Feb 6 (v2.1.33).

**Worktrees:**
- `WorktreeCreate`: On worktree creation. Hook prints path. Non-zero fails. Added Feb 20 (v2.1.50).
- `WorktreeRemove`: On worktree removal. No blocking. Added Feb 20 (v2.1.50).

### New input fields (Jan-Mar 2026):
- `tool_use_id` on PreToolUse and PostToolUse
- `agent_id`, `agent_transcript_path`, `agent_type` on SubagentStop
- `last_assistant_message` on Stop and SubagentStop (v2.1.47)
- `additionalContext` on PreToolUse OUTPUT (v2.1.9) — injects context into Claude
- `updatedMCPToolOutput` on PostToolUse OUTPUT — modify MCP tool output before Claude sees it

### Hooks at commit-time, not write-time (Shrivu Shankar)
Blocking agents mid-plan with PreToolUse hooks "confuses or even frustrates" them. Instead, hook `git commit` with validation that checks `/tmp/agent-pre-commit-pass` files. This enforces state validation at completion milestones rather than disrupting reasoning mid-flow. Matches ReliabilityBench finding: simpler beats complex under stress. [SOURCE: blog.sshh.io]

### Non-obvious patterns (Marco Patzelt, Feb 2026):

**PreCompact backup hook**: Save full transcript to timestamped files before auto-compaction. Context is otherwise irreversibly lost.
```json
{
  "event": "PreCompact",
  "type": "command",
  "command": "cp $CLAUDE_TRANSCRIPT ~/.claude/transcripts/$(date +%s).json"
}
```

**Tool input modification**: PreToolUse hooks can silently rewrite command arguments. Force `--dry-run` on destructive operations, redirect paths to sandboxes, redact secrets. Claude sees the original; the modified version runs.

**Anti-rationalization Stop hooks**: Use a fast model (Haiku) to evaluate whether Claude is rationalizing premature completion. Relevant for any adversarial/investigation workflow.

**Async hooks** (`"async": true`, Jan 2026): Run backgrounded without blocking. No deduplication. Good for test suites and CI triggers, cannot block behavior.

## Skills Architecture

### What makes a good skill:
- **Progressive disclosure**: Metadata (~50 tokens) always loaded. Instructions (~200-500 tokens) on activation. Resources (examples/templates) on reference.
- **$ARGUMENTS injection**: Skill receives user arguments as template variable.
- **`allowed-tools`**: Restrict skills to read-only tools for safety.
- **SkillsBench finding**: Self-generated skills = 0% improvement. Curated human-authored = +16.2%.

### Skills vs Subagents vs MCP (decision framework, Ryan Smith):
| | Context Cost | Portability | Best For |
|---|---|---|---|
| **Skills** | 70-90% savings via progressive loading | Works across all Claude products | Workflows, methodologies, templates |
| **Subagents** | ~70% savings via context filtering | Claude Code only | Parallel research, isolated exploration |
| **MCP** | Highest (schema loaded upfront) | Claude Code only | External data, APIs, stateful services |

**Critical insight**: "Claude becomes dumber after compacting when extensive exploration stays in main conversation." Deploy subagents early, even for moderately complex tasks. The exploration stays in the subagent's window; only the summary enters yours.

## Agent Teams

Beyond subagents. Full peer-to-peer collaboration.

### 7 primitives:
TeamCreate, TaskCreate, TaskUpdate, TaskList, Task (spawn teammate), SendMessage, TeamDelete. All map to filesystem operations. File locking prevents double-claiming.

### Cost reality (Alexander Opalic, Feb 2026):
- Solo session: ~200K tokens
- 3 subagents: ~440K tokens
- 3-person team: ~800K tokens

Teammates are full context windows. Linear cost scaling. **Teammates do NOT inherit lead's conversation history** — only project context via CLAUDE.md.

### Effective pattern:
- Run `/plan` at ~10K tokens to produce breakdown
- Hand approved plan to team lead
- Planning checkpoint prevents expensive mid-swarm course corrections
- Mixed model strategy: Sonnet for teammates, Opus for lead

## Security (Trail of Bits, Feb 2026)

**Stars:** 1,202. Most security-conscious public config.

- **Project MCP servers disabled by default** (`enableAllProjectMcpServers: false`). Cloning a repo with malicious `.mcp.json` could execute arbitrary code.
- **Credential blocklists**: SSH, AWS, Docker, npm, kubeconfig, crypto wallet paths.
- **Hook-based `rm -rf` prevention**: Suggests `trash` instead.
- **Mutation logging**: Hooks classify every shell command as read/write and log to `~/.claude/bash-commands.log`.
- **Local model fallback**: Qwen3-Coder-Next (80B MoE, 3B active) via LM Studio with Anthropic-compatible endpoint.

## Best GitHub Repos (filtered from 99%+ slop)

| Repo | Stars | Why it matters |
|---|---|---|
| **trailofbits/claude-code-config** | 1,202 | Security-first config with anti-rationalization hooks |
| **wshobson/agents** | 29,531 | 112 agents across 72 plugins. Three-tier model strategy (Opus/Sonnet/Haiku by task type) |
| **affaan-m/everything-claude-code** | 51,900 | Kitchen-sink reference. Anthropic hackathon winner. Catalog, not template. |

## Parallel Development (incident.io, Jun 2025)

Real production team running 4-7 parallel Claude agents simultaneously:
- Custom `w` bash function for worktree management with auto-completion
- Voice-driven development via SuperWhisper for complex specs
- Plan Mode as psychological safety — teams leave Claude running without worrying about unauthorized changes
- **Claude overestimates its own work duration**: Estimated 2 hours for a task completed in 10 minutes

## Brad Feld's Configuration

Most sophisticated solo-developer setup found:
- **Session state as process memory**: `.claude-session/*.json` files survive context compaction. Include `blockedActions` array enforcing workflow mid-session. Circuit breaker blocks `git commit` if status = `awaiting_user_test`.
- **Deterministic port allocation**: `PORT = 3000 + (worktree * 10) + app_slot` for 8 concurrent worktrees.
- **MCP Tool Search as lazy loading**: Instead of all MCP schemas upfront, `ToolSearch({ query: 'linear issues' })` loads tools on-demand.

## Plugins (Evaluated 2026-02-27)

**GA since Claude Code 1.0.33 (Oct 2025).** 9,000+ plugins in marketplace as of Feb 2026.

### What they are
Distribution format that bundles skills + hooks + MCP servers + agents + LSP servers into a shareable, installable package. Manifest at `.claude-plugin/plugin.json`. Install via marketplace or `--plugin-dir`.

### What they solve
Team/community distribution. One `claude plugin install` replaces manual setup of skills, hooks, and MCP configs. Versioned releases, namespaced skills (`/plugin:skill`), marketplace discovery.

### What they DON'T support
- **No rules equivalent.** `.claude/rules/*.md` with conditional path-scoped loading has no plugin analog. This is a core part of our intel (10 rules files) and selve (6 rules files) setups.
- **No non-namespaced skills.** All plugin skills become `/plugin-name:skill-name`. Can't opt out.
- **No project-specific MCP config overrides.** A plugin's `.mcp.json` is static — can't point DuckDB at different databases per project.

### Assessment: NOT worth it for our setup

**Why it doesn't fit:**
1. Single developer, not a team. Symlinks already distribute to ourselves.
2. Namespacing breaks muscle memory (`/researcher` → `/alien-tools:researcher`). Zero conflict risk when we control all names.
3. Rules (conditional path-scoped loading) can't be pluginized. This is our most valuable extension point.
4. Hooks are project-specific by nature (intel cost gates ≠ selve quality gates ≠ anki permission whitelist).
5. MCP servers need project-specific config (DuckDB → Medicaid views, Selve MCP → personal knowledge graph).
6. Migration cost: 16+ skills, multiple hook/MCP configs to restructure.

**Where plugins WOULD make sense (not us, not now):**
- Publishing `researcher` / `epistemics` / `scientific-drawing` for community use
- Team onboarding (share your full setup with a collaborator)
- Exa MCP starter kit (if configuring it in 6 projects became painful — it isn't)

**What would change this calculus:**
- If plugins gained rules support (conditional loading by path)
- If plugins supported non-namespaced skills
- If we started collaborating with others on intel/selve
- If we needed to onboard someone to our tooling

**Current architecture (symlinks + per-project config) is better suited to a single-developer, heterogeneous project setup.**

[SOURCE: code.claude.com/docs/en/plugins, anthropic.com/news/claude-code-plugins (Oct 2025), morphllm.com/claude-code-plugins (Feb 2026)]

## Jan-Mar 2026 Changelog Summary (v2.1.2 — v2.1.70)

Added 2026-03-03. 40+ releases in 8 weeks. Major themes below.

### Milestone Releases

| Version | Date | What |
|---------|------|------|
| v2.1.3 | Jan 9 | Slash commands + skills merged. Hook timeout 60s -> 10min. |
| v2.1.7 | Jan 14 | MCP tool search auto mode default (>10% context -> MCPSearch). |
| v2.1.9 | Jan 16 | `PreToolUse` `additionalContext` output. `${CLAUDE_SESSION_ID}` in skills. `plansDirectory` setting. |
| v2.1.15 | Jan 21 | npm installation deprecated -> native installer. |
| v2.1.16 | Jan 22 | New task management with dependency tracking. |
| v2.1.27 | Jan 30 | `--from-pr` flag. Auto PR-session linking. Permission content-level `ask` > tool-level `allow`. |
| v2.1.30 | Feb 3 | PDF `pages` param on Read tool. MCP OAuth pre-configured credentials. `/debug` command. |
| v2.1.32 | Feb 5 | **Opus 4.6**. **Agent Teams (experimental)**. **Auto-memory**. "Summarize from here" partial compaction. |
| v2.1.33 | Feb 6 | `TeammateIdle`/`TaskCompleted` hook events. Agent `memory` frontmatter. `Task(agent_type)` restriction. |
| v2.1.49 | Feb 19 | `--worktree` CLI flag. `isolation: worktree`. `ConfigChange` hook. `background: true` agents. Ctrl+F kill agents. |
| v2.1.50 | Feb 20 | `WorktreeCreate`/`WorktreeRemove` hooks. `claude agents` CLI. Opus 4.6 fast 1M context. |
| v2.1.51 | Feb 24 | `claude remote-control`. SDK env vars (account/email/org UUID). Managed settings via macOS plist/Windows Registry. |
| v2.1.59 | Feb 26 | Auto-memory GA with `/memory` command. |
| v2.1.63 | Feb 28 | `/simplify` + `/batch` bundled skills. **HTTP hooks**. 12+ memory leak fixes. |

### SDK (claude-agent-sdk-python) Key Changes

- **0.1.0**: Renamed from Claude Code SDK. Breaking: `ClaudeAgentOptions`, merged `system_prompt`, no default system prompt, `setting_sources` isolation.
- **0.1.7**: Structured outputs, fallback model handling.
- **0.1.12**: `tools` option (specify available tools), `betas` option (1M context).
- **0.1.15**: File checkpointing + `rewind_files()`.
- **0.1.29**: `Notification`, `SubagentStart`, `PermissionRequest` hooks. `tool_use_id`, `additionalContext`, `updatedMCPToolOutput`.
- **0.1.31**: MCP tool annotations (`readOnlyHint`, `destructiveHint`, etc.).
- **0.1.36**: `ThinkingConfig` types (adaptive/enabled/disabled), `effort` option (low/medium/high/max).
- **0.1.40**: Forward-compatible unknown message type handling.

### MCP Improvements

1. **Tool search auto mode** (v2.1.7): default on, defers tool descriptions when >10% context.
2. **`auto:N` threshold** (v2.1.9): configurable % for auto-enable.
3. **OAuth**: step-up auth, discovery caching, pre-configured client credentials, race condition fixes.
4. **claude.ai MCP connectors** (v2.1.46): use claude.ai-configured servers in Claude Code.
5. **MCP tool annotations** (SDK 0.1.31): metadata hints for tool behavior.
6. **`updatedMCPToolOutput`** on PostToolUse: hooks can modify MCP output.
7. **LSP `startupTimeout`** (v2.1.50): configurable timeout.

### Agent/Subagent Features

- `isolation: "worktree"` in agent definitions and `--worktree` CLI flag.
- `memory` frontmatter: `user`|`project`|`local` scope persistent memory.
- `background: true`: always run as background task.
- `Task(agent_type)` restriction in agent `tools` frontmatter.
- `claude agents` CLI command to list configured agents.
- Agent Teams (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).
- `TeammateIdle`/`TaskCompleted` hooks for quality gates.
- Ctrl+F to kill background agents (two-press confirmation).

### Experimental/Alpha/Beta

| Feature | Status | Enable |
|---------|--------|--------|
| Agent Teams | Experimental | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` |
| Native binary installer | Alpha | `claude install` |
| GitHub Actions | Beta | `anthropics/claude-code-action@beta` |
| Remote Control | Expanding | `claude remote-control` |
| 1M context | GA (was beta) | Default on Opus 4.6 fast. Disable: `CLAUDE_CODE_DISABLE_1M_CONTEXT` |

### Direction Signals

1. **Multi-agent is the frontier.** Agent Teams, teammate hooks, worktree isolation, agent memory, background tasks — all shipped in 3 weeks.
2. **Hooks becoming a full control plane.** 9 -> 18 events, 4 hook types, HTTP hooks, ConfigChange, PermissionRequest.
3. **SDK decoupling from Claude Code.** Rename to Agent SDK, setting isolation, tools option, structured outputs, file rewind.
4. **Native memory.** Auto-memory GA, persistent agent memory, worktree config sharing.
5. **Plugin ecosystem.** npm registries, git SHA pinning, OS-level managed settings (plist/Registry).
6. **Performance/stability.** 20+ memory leak fixes. Long session scaling is clearly a production concern.
7. **Context management.** PDF pages, tool results to disk, partial compaction, MCP tool search auto-mode, skill budget scaling.

## v2.1.68–2.1.70 Notable Changes (Mar 2026)

### New Hook Events and Fields
- **`InstructionsLoaded`**: fires when CLAUDE.md / `.claude/rules/*.md` load. No decision control — diagnostic/logging only.
- **`agent_id` and `agent_type`** now reliably present in ALL hook events (previously only SubagentStop). Enables agent-differentiated hook behavior (e.g., lenient bash-loop-guard for subagents).
- **`worktree` field in status line commands**: provides `name`, `path`, `branch`, `original_repo_dir`.
- **`TeammateIdle`/`TaskCompleted`** now support `{"continue": false, "stopReason": "..."}` to stop teammates.
- **`WorktreeCreate`/`WorktreeRemove`** plugin hooks now work (were previously broken).

### New Settings and Variables
- **`includeGitInstructions: false`**: disables built-in git instructions (~600 tokens of generic branch/PR/Co-Authored-By workflow). Useful when projects have custom git conventions that conflict with defaults.
- **`${CLAUDE_SKILL_DIR}`**: skills can reference their own directory in SKILL.md content. Enables skills that bundle companion files (templates, configs) without hardcoding paths.

### Performance and Stability
- **~16MB baseline memory reduction** from dependency optimizations.
- **74% fewer prompt re-renders** — significant reduction in redundant processing.
- **12+ memory leak fixes** across long sessions, subagents, and hook accumulation (continuing from v2.1.63 fixes).
- **ToolSearch empty response fix**: no longer returns empty results spuriously.

### Compaction Changes
- **Images preserved through compaction** (v2.1.70): previously dropped during auto/manual compaction.
- **No preamble recap after compaction** (v2.1.69): post-compaction context is cleaner, no redundant restatement of what was discussed.
- **Skill listing not re-injected on `--resume`** (v2.1.69): saves ~600 tokens per resume.

---

## Design Principles Summary

1. **Context is your scarcest resource.** Every token in the window competes with reasoning capacity. Minimize always-loaded content.
2. **Progressive disclosure > monolithic instructions.** CLAUDE.md → rules → skills → subagents. Load what's needed when it's needed.
3. **Hooks are free.** They run outside the model. Use them for deterministic enforcement (formatting, security, workflow gates).
4. **Subagents protect the main window.** Exploration-heavy tasks should be delegated early. The summary is cheaper than the exploration.
5. **Git is the memory system.** Not databases, not vector stores. Files + commits + diffs. Anthropic's own long-running agents use this pattern.
6. **Compaction is lossy. Plan & Clear is the escape hatch.** When Claude offers "clear context and execute plan (.md)" at context limits, prefer it over "summarize and continue." The plan file is a checkpoint you can audit and edit. Auto-compaction is opaque. Backup transcripts via PreCompact hooks regardless.
7. **SkillsBench: human-authored skills work, self-generated don't.** Invest in writing good skills. Don't let Claude write its own.
8. **Two-agent architecture for multi-session work.** Initializer writes plan + progress file. Worker reads and continues. No state beyond files.
9. **Anti-rationalization is a real failure mode.** Stop hooks that evaluate completion claims catch premature "done" declarations.
10. **Security by default.** Disable project MCP servers, blocklist credentials, log mutations, prefer `trash` over `rm`.
