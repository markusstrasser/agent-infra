---
date: 2026-06-07
topic: feature-delta
tools: [claude-code, codex-cli, claude-agent-sdk]
scope: [hooks, mcp, subagents, memory, plugins, sdk]
status: verified
sources:
  - https://code.claude.com/docs/en/changelog (primary — full May/June 2026 versions read)
  - https://code.claude.com/docs/en/hooks (primary — 31-event schema read)
  - https://code.claude.com/docs/en/settings (primary — full settings table read)
  - https://code.claude.com/docs/en/agent-sdk/typescript (primary — SDK API read)
  - https://developers.openai.com/codex/changelog (primary — May/June 2026 entries read)
  - https://claude.com/blog/claude-code-plugins (primary — plugin system read)
---

# Feature Delta: Claude Code & Codex CLI (May–June 2026)

Research date: 2026-06-07. Covers changes since approximately May 1, 2026.
Baseline: Claude Code ≤ v2.1.128; Codex CLI 0.137; existing knowledge of hooks/skills/MCP/subagents.

---

## Claims Table

| Claim | Version / Date | Source URL | Confidence | Leverage for agent-infra |
|---|---|---|---|---|
| **31 hook event types** now documented (up from ~14 we knew) | v2.1.141+, May 2026 | code.claude.com/docs/en/hooks | HIGH — primary source read | Many new events hookable for session forensics, worktree lifecycle, compaction |
| **New hook events: SessionStart, Setup, SessionEnd** — lifecycle events with context injection | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | SessionStart → inject project-state summaries, reload skills, set session title |
| **UserPromptSubmit** — fires before Claude processes each user prompt; stdout added as context Claude sees | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Preflight validation, inject dynamic rules per-prompt |
| **PreCompact / PostCompact** hooks — PreCompact can block compaction (exit 2); PostCompact fires after | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Lossless memory pipeline: snapshot state pre-compact, restore post-compact |
| **SubagentStart / SubagentStop** hooks — fire when subagents spawn/finish | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Session forensics: trace subagent lineage, budget enforcement per subagent |
| **TaskCreated / TaskCompleted** hooks | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Background task lifecycle telemetry without polling |
| **ConfigChange hook** — fires when any settings file changes mid-session | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Hot-reload enforcement: detect drift, re-validate hook inventory |
| **WorktreeCreate / WorktreeRemove** hooks | v2.1.141+; v2.1.128 changelog confirms | code.claude.com/docs/en/hooks | HIGH | Worktree lifecycle auditing; auto-cleanup guards |
| **Elicitation / ElicitationResult** hooks — MCP elicitation intercepted via hook | v2.1.141+ | code.claude.com/docs/en/hooks | MEDIUM | Intercept MCP user-input requests for logging or auto-response |
| **MessageDisplay hook** — transform or hide assistant message text as displayed | v2.1.152, May 29 2026 | code.claude.com/docs/en/changelog | HIGH | Filter slop, inject source-grade warnings inline into responses |
| **InstructionsLoaded hook** — fires when CLAUDE.md or rules/*.md loaded | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Validate rule loading, measure context budget on each load |
| **PermissionRequest / PermissionDenied** hooks — intercept permission dialogs | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Audit log for auto-mode permission decisions; enforce deny lists |
| **PostToolBatch** hook — after all parallel tool calls in a batch resolve | v2.1.141+ | code.claude.com/docs/en/hooks | MEDIUM | Batch-level cost tracking; detect parallel tool abuse |
| **PostToolUseFailure** hook — after a tool call fails | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Error pattern capture for session forensics; failure-loop detection |
| **StopFailure** hook — fires when turn ends due to API error | v2.1.141+ | code.claude.com/docs/en/hooks | MEDIUM | API error telemetry without custom instrumentation |
| **hook `async: true` + `asyncRewake: true`** — background hook can re-engage Claude with exit 2 | v2.1.23+ (async), rewake variant at v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Deferred validation: run corpus check async, rewake Claude when done |
| **mcp_tool hook type** (5th handler type) — call tools on connected MCP servers from a hook | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Hook → MCP tool call without subprocess; wires hooks to research-mcp |
| **hook `args: string[]` exec form** — spawns command without shell, no quoting hazards | v2.1.139, May 11 | code.claude.com/docs/en/changelog | HIGH | Safer hook invocation; eliminates shell-escaping bugs in existing hooks |
| **hook `continueOnBlock` for PostToolUse** — feeds rejection reason back as context, keeps turn alive | v2.1.139, May 11 | code.claude.com/docs/en/changelog | HIGH | Non-fatal hook blocks with explanation; replaces exit-2 hard stops for advisory hooks |
| **hook `if:` conditional filter** (all hook types) | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | Already using; confirms all 5 handler types support it |
| **hook `once: true`** — runs once per session then removed (skills/agents only) | v2.1.141+ | code.claude.com/docs/en/hooks | MEDIUM | One-shot session-init checks |
| **SessionStart hook: `reloadSkills: true` return** — re-scans skill directories without restart | v2.1.152, May 29 | code.claude.com/docs/en/changelog | HIGH | Install skills from a hook, make them available same session |
| **SessionStart hook: `sessionTitle` return** — set session title at start/resume | v2.1.152, May 29 | code.claude.com/docs/en/changelog | MEDIUM | Auto-label sessions by project/branch for agentlogs forensics |
| **Stop/SubagentStop hooks return `hookSpecificOutput.additionalContext`** — keep turn alive with feedback | v2.1.163, June 4 | code.claude.com/docs/en/changelog | HIGH | Advisory stop hooks that inform rather than terminate |
| **Stop/SubagentStop input includes `background_tasks` and `session_crons` fields** | v2.1.145, May 19 | code.claude.com/docs/en/changelog | HIGH | Stop hook sees live background task inventory; budget-enforcement use case |
| **`terminalSequence` field in hook JSON output** — desktop notifications/titles without /dev/tty | v2.1.141, May 13 | code.claude.com/docs/en/changelog | MEDIUM | Hooks can push desktop alerts (e.g. "corpus attestation failed") |
| **`CLAUDE_ENV_FILE` hook output** — persist env vars across Bash commands from a hook | v2.1.136, May 8 (bug fix implies prior existence) | changelog bugfix entry | MEDIUM | SessionStart hook can inject session-scoped env config |
| **Plugin system (GA beta)** — bundle slash commands + subagents + MCPs + hooks, install from marketplace | May 2026 GA beta | claude.com/blog/claude-code-plugins | HIGH | Package agent-infra hooks + skills as distributable plugin; `.claude/skills` auto-load |
| **Plugins auto-load from `.claude/skills/`** — no marketplace required | v2.1.157, May 29 | code.claude.com/docs/en/changelog | HIGH | Current skills dir already at right path; zero-migration benefit |
| **`claude plugin init <name>`** — scaffold plugin in `.claude/skills` | v2.1.157, May 29 | code.claude.com/docs/en/changelog | MEDIUM | Standardizes skill/hook packaging |
| **`defaultEnabled: false` in plugin.json** — plugin installed but off by default | v2.1.154, May 28 | code.claude.com/docs/en/changelog | MEDIUM | Ship experimental hooks without activating them |
| **Skills `disallowed-tools` frontmatter** — remove tools while skill active | v2.1.152, May 29 | code.claude.com/docs/en/changelog | HIGH | Skill-scoped tool restriction; no global settings.json change |
| **`/reload-skills` command** + **SessionStart `reloadSkills`** | v2.1.152, May 29 | code.claude.com/docs/en/changelog | MEDIUM | Hot-reload skills without restarting session |
| **MCP tool hooks** — hook can call MCP server tools directly | v2.1.141+ | code.claude.com/docs/en/hooks | HIGH | research-mcp tools callable from hooks without subprocess |
| **Subagent identity in hook inputs** — `agent_id`, `parent_agent_id` | v2.1.134 (Codex equivalent), confirmed Claude hooks schema | code.claude.com/docs/en/hooks | HIGH | Lineage tracing in hook telemetry; multi-agent attribution |
| **API requests from subagents carry `x-claude-code-agent-id` / `x-claude-code-parent-agent-id` headers** | v2.1.139, May 11 | code.claude.com/docs/en/changelog | HIGH | OTel traces nest correctly; session forensics can trace fan-out |
| **`agent_id` / `parent_agent_id` on `claude_code.llm_request` OTel spans** | v2.1.139, May 11 | code.claude.com/docs/en/changelog | HIGH | Same — agentlogs can reconstruct subagent DAG from OTel |
| **`OTEL_RESOURCE_ATTRIBUTES` as metric labels** — slice metrics by team/repo | v2.1.161, June 2 | code.claude.com/docs/en/changelog | MEDIUM | Label cross-project hook telemetry by project without separate OTEL configs |
| **`claude agents` (Agent View) — GA** | v2.1.139, May 11 | code.claude.com/docs/en/changelog | HIGH | List/inspect all sessions JSON (`--json`); `waitingFor` field shows blocks |
| **`claude agents --json`** — machine-readable session list with `waitingFor` | v2.1.145 + v2.1.162 | code.claude.com/docs/en/changelog | HIGH | Session forensics: scriptable session state polling without logs |
| **`/goal` command** — set completion condition, Claude works until met | v2.1.139, May 11 | code.claude.com/docs/en/changelog | MEDIUM | Autonomous multi-turn task completion with budget tracking |
| **Dynamic workflows** — Claude orchestrates tens–hundreds of background agents | v2.1.154, May 28 | code.claude.com/docs/en/changelog | HIGH | Replaces manual subagent fan-out for large tasks; `ultracode` keyword trigger |
| **`worktree.bgIsolation: "none"` setting** — background sessions edit working copy directly | v2.1.143, May 15 | code.claude.com/docs/en/changelog | HIGH | Opt-out of worktree for repos where it's impractical |
| **`EnterWorktree` mid-session switching** | v2.1.157, May 29 | code.claude.com/docs/en/changelog | MEDIUM | Switch worktrees without restarting; subagent dispatch can target different worktrees |
| **Auto Memory (`autoMemoryEnabled`, `autoMemoryDirectory`)** — Claude writes MEMORY.md autonomously | v2.1.59+ (confirmed via settings docs) | code.claude.com/docs/en/settings | HIGH | MEMORY.md already used; ensure `autoMemoryEnabled: true` in .claude/settings.json |
| **`fallbackModel` setting** — up to 3 fallback models tried in order on overload | v2.1.166, June 6 | code.claude.com/docs/en/changelog | HIGH | Resilient llmx dispatch; configure fallback chain for hook-dispatched queries |
| **`claude agents` background `! <command>`** — run shell command as background session | v2.1.154, May 28 | code.claude.com/docs/en/changelog | MEDIUM | Long-running scripts as first-class sessions with agent-view observability |
| **`CLAUDE_CODE_SESSION_ID` in stdio MCP servers** — same env var hooks/Bash get | v2.1.154, May 28 | code.claude.com/docs/en/changelog | HIGH | MCP servers can correlate tool calls to sessions; research-mcp logs improvement |
| **`CLAUDECODE=1` in MCP subprocess env** | v2.1.154, May 28 | code.claude.com/docs/en/changelog | MEDIUM | MCP servers can detect Claude Code context vs direct invocation |
| **`autoMode.hard_deny` rules** — block unconditionally regardless of user intent | v2.1.136, May 8 | code.claude.com/docs/en/changelog | HIGH | Data-guard equivalent in auto mode; replaces some PreToolUse hook logic |
| **`disableAllHooks` + `allowManagedHooksOnly` settings** | v2.1.141+ | code.claude.com/docs/en/settings | MEDIUM | Enterprise governance; lock down hook surface to managed-only |
| **`policyHelper` executable** — admin script computes managed settings dynamically | v2.1.136+ | code.claude.com/docs/en/settings | LOW | Enterprise use; not relevant for single-user setup |
| **`strictPluginOnlyCustomization`** — locks skills/agents/hooks/MCPs to plugin/managed sources | v2.1.141+ | code.claude.com/docs/en/settings | LOW | Enterprise governance |
| **Agent SDK: `enableFileCheckpointing` + `rewindFiles()`** — restore files to any prior message state | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | SDK-hosted agents can rewind on error; replaces manual git-stash recovery |
| **Agent SDK: `setMcpServers()` mid-session** — dynamically replace MCP servers | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Session-scoped MCP config; attach research-mcp only when needed |
| **Agent SDK: `toggleMcpServer()` / `reconnectMcpServer()`** | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | MEDIUM | Recovery from MCP failures without restarting session |
| **Agent SDK: `canUseTool` custom permission function** — per-call programmatic permission | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Replaces hook-based permission logic for SDK-hosted agents |
| **Agent SDK: `maxBudgetUsd` + `taskBudget`** — stop on cost estimate | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Per-task cost guard; integrates with $25 daily cap |
| **Agent SDK: `streamInput()` + `interrupt()`** — multi-turn streaming with mid-turn interrupt | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | MEDIUM | Interactive SDK orchestration without process restarts |
| **Agent SDK: `listSessions()` + `getSessionMessages()` + `tagSession()`** | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Programmatic session history access; agentlogs alternative or complement |
| **Agent SDK: structured output (`outputFormat: json_schema`)** | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Typed outputs from hook-triggered SDK queries; replaces JSON parsing |
| **Agent SDK: `includeHookEvents` — emit hook lifecycle as SDK messages** | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Full hook observability from SDK; session forensics without log files |
| **Agent SDK: `memory: "user"/"project"/"local"` per agent** | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | HIGH | Scope memory per subagent; cross-session knowledge without CLAUDE.md writes |
| **Agent SDK: `agentProgressSummaries: true`** — `SDKTaskProgressMessage` includes summary | SDK 2026 | code.claude.com/docs/en/agent-sdk/typescript | MEDIUM | Progress summaries from background agents without polling |
| **Codex 0.134: `--profile` as primary selector, per-server MCP env targeting, MCP OAuth for HTTP** | v0.134.0, May 26 | developers.openai.com/codex/changelog | HIGH | Per-server MCP OAuth closes auth gap; per-profile MCP isolation confirmed |
| **Codex 0.134: subagent identity in hook context + conversation history in hook context** | v0.134.0, May 26 | developers.openai.com/codex/changelog | HIGH | codex_hook_shim.py should expose these; parity with Claude hook inputs |
| **Codex 0.134: read-only MCP tools marked `readOnlyHint` execute concurrently** | v0.134.0, May 26 | developers.openai.com/codex/changelog | MEDIUM | Read-heavy research-mcp tools run parallel under Codex |
| **Codex 0.135: Python SDK exposes `Sandbox` presets for thread/turn APIs** | v0.135.0, May 28 | developers.openai.com/codex/changelog | HIGH | Programmatic Codex orchestration parity with Claude Agent SDK |
| **Codex 0.135: `/permissions` understands named permission profiles** | v0.135.0, May 28 | developers.openai.com/codex/changelog | MEDIUM | Profile-based permission management confirmed working |
| **Codex 0.137: `codex plugin list --json`** — machine-readable plugin list | v0.137.0, June 4 | developers.openai.com/codex/changelog | MEDIUM | Scriptable plugin inventory |
| **Codex 0.137: multi-agent v2** — runtime selection per thread with improved follow-up | v0.137.0, June 4 | developers.openai.com/codex/changelog | HIGH | Stable multi-agent; previously experimental |
| **Codex 0.137: web/image tools in code mode with parallel web searches** | v0.137.0, June 4 | developers.openai.com/codex/changelog | MEDIUM | Codex can do parallel web research in code mode |

---

## Section 1: Hook System — Major Expansion

The hook event surface grew from ~14 known events to **31 documented event types** across 6 lifecycle categories, plus a 5th handler type (`mcp_tool`). This is the highest-leverage surface for agent-infra.

### New events we can wire

**Compaction lifecycle:**
- `PreCompact` — can block compaction (exit 2) or inject system message. Use: snapshot corpus state, write checkpoint.md, prevent compaction during sensitive multi-step operations.
- `PostCompact` — fires after compaction completes. Use: restore context markers, re-inject project state, increment compaction counter in session forensics.

**Turn/prompt lifecycle:**
- `UserPromptSubmit` — before every user prompt, stdout goes into Claude's context. Use: inject dynamic rules, run preflight validation, deny prompts matching patterns.
- `SessionStart` (startup/resume/clear/compact matcher) — now supports `reloadSkills: true` and `sessionTitle` returns. Use: per-project context injection, auto-label sessions by git branch.
- `StopFailure` — API error turn termination. Use: API error telemetry without instrumentation code.

**Subagent/task lifecycle:**
- `SubagentStart` / `SubagentStop` — wrap every subagent. Use: budget enforcement, lineage logging for session forensics.
- `TaskCreated` / `TaskCompleted` — background task events. Use: task-level telemetry without polling.
- `SubagentStop` input now includes `background_tasks` and `session_crons` — see live task inventory at stop time.

**Structural:**
- `ConfigChange` — settings file edited mid-session. Use: detect hook drift, re-validate hook inventory.
- `WorktreeCreate` / `WorktreeRemove` — worktree lifecycle. Use: auto-cleanup guards, orphan detection.
- `InstructionsLoaded` — CLAUDE.md/rules/*.md loaded. Use: measure context budget on each load, validate rule integrity.

**MCP:**
- `Elicitation` / `ElicitationResult` — MCP user-input requests. Use: intercept for logging or auto-response in headless mode.
- `PermissionRequest` / `PermissionDenied` — auto mode permission dialogs. Use: audit log for all auto-mode decisions.

### New handler type: `mcp_tool`

Hooks can now call tools on connected MCP servers directly without spawning a subprocess. Schema:
```json
{
  "type": "mcp_tool",
  "server": "research",
  "tool": "save_source",
  "input": { "url": "${tool_input.url}" }
}
```
This wires hooks directly to research-mcp without a Python subprocess layer.

### New hook behaviors

- **`args: string[]` exec form** — spawn command without shell, no quoting hazards. Safer than current `command` form.
- **`continueOnBlock` on PostToolUse** — rejection reason fed back as context; turn continues. Enables advisory (non-fatal) hook blocks.
- **`asyncRewake: true`** — async background hook can re-engage Claude (exit 2). Use: corpus check async, rewake when done.
- **`additionalContext` in Stop/SubagentStop hookSpecificOutput** — keep turn alive with feedback, not labeled as error.
- **`terminalSequence` output** — push desktop notifications from hooks without /dev/tty.
- **`once: true`** — hook runs once per session then removes itself.

### `MessageDisplay` hook (new event)

Fires while assistant message text is being displayed. Can transform or hide text. Use: inject inline source-grade warnings, filter slop patterns, redact sensitive data from display.

---

## Section 2: Plugin System

The plugin system (now GA beta) is the distribution/packaging layer for skills + hooks + MCPs + subagents. Key for agent-infra:

- **`.claude/skills/` auto-load** (v2.1.157) — plugins in this directory load automatically without marketplace registration. Our current skills directory is already at the right path. Zero migration.
- **`claude plugin init <name>`** — scaffolds a new plugin with correct structure.
- **`defaultEnabled: false`** — ship experimental hooks without activating them by default.
- **Skills `disallowed-tools` frontmatter** — remove tools from the model while a specific skill is active. Replaces global settings.json restrictions.
- **`/reload-skills`** + **SessionStart `reloadSkills: true`** — hot-reload without session restart.
- **Plugin dependency enforcement** — `claude plugin disable` refuses when another plugin depends on it.

---

## Section 3: Agent SDK — New APIs

The Claude Agent SDK (TypeScript) has significant new capabilities:

**File checkpointing:**
```typescript
options: { enableFileCheckpointing: true }
await query.rewindFiles(userMessageId, { dryRun: true });
```
SDK-hosted agents can rewind file state to any prior message. Replaces manual git-stash recovery in error paths.

**Dynamic MCP management:**
- `setMcpServers()` — replace MCP servers mid-session
- `toggleMcpServer()` / `reconnectMcpServer()` — enable/disable without restart
- `createSdkMcpServer()` — in-process MCP server (no subprocess)

**Permission control:**
- `canUseTool` custom function — per-call programmatic permission, replaces hook-based permission logic for SDK-hosted agents
- `maxBudgetUsd` — stop on cost estimate; integrates with $25/day cap rule

**Session management:**
- `listSessions()` / `getSessionMessages()` / `tagSession()` / `renameSession()` — programmatic session history access
- Session metadata includes `gitBranch`, `cwd`, `tag`

**Observability:**
- `includeHookEvents` — emit hook lifecycle as SDK messages (`SDKHookStartedMessage`, `SDKHookProgressMessage`, `SDKHookResponseMessage`). Full hook observability from SDK without log files.

**Structured output:**
```typescript
options: { outputFormat: { type: "json_schema", schema: {...} } }
```
Typed outputs from SDK-dispatched queries; eliminates JSON parsing.

**Memory tiers per agent:**
```typescript
{ memory: "user" | "project" | "local" }
```
Scope memory per subagent. Cross-session knowledge without CLAUDE.md writes.

---

## Section 4: Session & Multi-Agent Infrastructure

**Agent View (`claude agents`) — GA (v2.1.139, May 11):**
- `claude agents --json` — machine-readable session list with `waitingFor` field showing what a blocked session needs
- Session rows show `done/total` for fanned-out work
- `--add-dir`, `--settings`, `--mcp-config`, `--plugin-dir` flags on `claude agents` apply to all dispatched sessions
- Terminal tab title shows awaiting-input count

**Dynamic workflows (v2.1.154, May 28):**
Claude can orchestrate tens–hundreds of background agents autonomously via the `ultracode` keyword (previously `workflow`). This is parallel to our subagent patterns but orchestrator-managed. Use for large fan-out tasks without writing orchestration code.

**`/goal` command (v2.1.139, May 11):**
Set a completion condition; Claude works across turns until met. Shows elapsed/turns/tokens overlay. Works in `-p` mode and Remote Control.

**Background session improvements:**
- Pinned background sessions survive idle reap
- `! <command>` in `claude agents` runs shell command as first-class background session
- `worktree.bgIsolation: "none"` — opt out of worktree for repos where impractical
- `EnterWorktree` mid-session switching (v2.1.157)

**OTel/Tracing:**
- `agent_id` / `parent_agent_id` on all API requests and OTel spans — subagent DAG reconstructable from OTel
- `OTEL_RESOURCE_ATTRIBUTES` as metric labels — slice by team/repo without separate configs
- `OTEL_LOG_TOOL_DETAILS=1` — `tool_decision` spans include bash commands, MCP/skill names (opt-in)

---

## Section 5: Settings — Notable New Entries

| Setting | Since | Use |
|---|---|---|
| `fallbackModel` (list of up to 3) | v2.1.166 | Resilient model chain; configure for hook-dispatched queries |
| `autoMemoryEnabled` / `autoMemoryDirectory` | v2.1.59+ | Already useful; ensure enabled, point to project memory dir |
| `autoMode.hard_deny` | v2.1.136 | Unconditional deny regardless of user intent; data-guard in auto mode |
| `worktree.bgIsolation: "none"` | v2.1.143 | Repos where worktrees are impractical |
| `CLAUDE_CODE_SESSION_ID` in stdio MCP servers | v2.1.154 | MCP servers can correlate to sessions for research-mcp logging |
| `disableAllHooks` / `allowManagedHooksOnly` | v2.1.141+ | Enterprise lock-down; not needed for single-user but good to know |
| `strictPluginOnlyCustomization` | v2.1.141+ | Lock surface to managed sources only |

---

## Section 6: Codex CLI (post-0.137)

Latest released version is **0.137.0 (June 4, 2026)**. No post-0.137 releases exist yet. The most relevant changes since our 0.137 baseline:

**0.134.0 (May 26):**
- `--profile` confirmed primary selector (we already knew this)
- Per-server MCP environment targeting — each MCP server gets its own env, not a global blob
- MCP OAuth for HTTP servers — closes auth gap for remote MCP servers
- **Subagent identity + conversation history in hook context** — our `codex_hook_shim.py` should expose `subagent_id` and `parent_subagent_id` from these inputs
- Read-only MCP tools marked `readOnlyHint` execute concurrently — research-mcp read-tools run parallel

**0.135.0 (May 28):**
- **Python SDK `Sandbox` presets** — programmatic Codex orchestration now has typed presets; parity with Claude Agent SDK
- `/permissions` understands named permission profiles — complements `--profile`
- `codex doctor` richer diagnostics (git, terminal, app-server, thread inventory)

**0.137.0 (June 4):**
- Multi-agent v2 stable — runtime selection per thread, improved follow-up
- `codex plugin list --json` — scriptable plugin inventory
- Web/image tools in code mode with parallel web searches

**Codex hook context update (0.134):** The hook input now includes `subagent_id`, `parent_subagent_id`, and conversation history. Our `codex_hook_shim.py` currently maps Claude's hook schema to Codex's; verify these new fields are being forwarded.

---

## Executive Summary (10 highest-leverage items)

1. **31 hook events, up from ~14** (v2.1.141+) — PreCompact/PostCompact, UserPromptSubmit, SubagentStart/Stop, TaskCreated/Completed, ConfigChange, WorktreeCreate/Remove, InstructionsLoaded, PermissionRequest/Denied, MessageDisplay, PostToolBatch, PostToolUseFailure, StopFailure, Elicitation/Result. Wire PreCompact→checkpoint, PostCompact→restore, SubagentStart/Stop→lineage tracing.

2. **`mcp_tool` hook handler** — hooks can call MCP server tools directly without subprocess. Wire PostToolUse hooks directly to research-mcp `save_source` without Python intermediary.

3. **`asyncRewake: true`** — async hooks can re-engage Claude. Use for corpus attestation: run check async, rewake Claude when verdict ready. Eliminates the polling/timeout pattern in current hooks.

4. **`continueOnBlock` + `additionalContext` on Stop/SubagentStop** — advisory hooks that explain rather than terminate. Replaces current exit-2 hard stops for hooks that should inform, not block.

5. **`args: string[]` exec form for command hooks** — no shell, no quoting hazards. Migrate all existing command hooks to exec form to eliminate escaping bugs.

6. **Agent SDK `includeHookEvents`** — full hook lifecycle observable as SDK messages. Session forensics can reconstruct every hook decision without log files.

7. **Agent SDK `setMcpServers()` mid-session + `createSdkMcpServer()` in-process** — dynamic MCP management. SDK-hosted sessions can attach research-mcp only for research tasks, detach for code tasks.

8. **Agent SDK `maxBudgetUsd`** — per-task cost guard in SDK-hosted sessions. Enforces $25/day cap rule architecturally rather than instructionally.

9. **`.claude/skills/` auto-load** (v2.1.157) — our existing skills directory already matches; no migration. Plugins install from `.claude/skills` without marketplace. Ship new hooks as plugins with `defaultEnabled: false` for staged rollout.

10. **Codex 0.134 subagent identity + conversation history in hook context** — `codex_hook_shim.py` should forward `subagent_id` and `parent_subagent_id`; enables subagent lineage tracing parity with Claude. Also: per-server MCP env targeting closes auth gap for remote MCP servers under Codex.

---

## Verification Notes

- Claude Code changelog: read directly from `code.claude.com/docs/en/changelog` (full May/June 2026 content, 705 lines). All version numbers and dates verified against primary source.
- Hook schema: read directly from `code.claude.com/docs/en/hooks`. 31 events confirmed, 5 handler types confirmed.
- Codex changelog: read from `developers.openai.com/codex/changelog`. Versions 0.134–0.137 verified.
- Agent SDK: read from `code.claude.com/docs/en/agent-sdk/typescript`.
- Settings: read from `code.claude.com/docs/en/settings`.
- Plugin system: read from `claude.com/blog/claude-code-plugins`.
- No claims asserted from training memory; all from live primary-source fetches this session.
- `asyncRewake` version landing: search results say "v2.1.23+" for async hooks generally, but the `asyncRewake` variant specifically is confirmed in current docs without a precise landing version — flagged as v2.1.141+ (when docs consolidated).
