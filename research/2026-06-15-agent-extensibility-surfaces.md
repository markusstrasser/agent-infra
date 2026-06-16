---
title: AI Coding Agent Extensibility Surfaces — Cross-Platform Comparison
date: 2026-06-15
tags: [claude-code, cursor, codex, gemini, MCP, hooks, skills, architecture]
status: complete
---

# AI Coding Agent Extensibility Surfaces — Cross-Platform Comparison

**Question:** How do Claude Code, Cursor, Codex CLI, and Gemini CLI design their extensibility surfaces? Do they converge on a partition? What's unique per vendor?

**Sources:** Official docs + local entity files, pulled 2026-06-15.

---

## Summary Table

| Platform | Context (always-on) | Workflow/Knowledge | Enforcement | External data/actions | Distribution |
|---|---|---|---|---|---|
| **Claude Code** | CLAUDE.md | Skills (SKILL.md + frontmatter) | Hooks (31+ events, 5 handler types) | MCP (tools/resources/prompts) | Plugins |
| **Cursor** | Rules (.mdc, alwaysApply) | Skills (SKILL.md + frontmatter) | Hooks (18+ events, hooks.json) | MCP (.cursor/mcp.json) | Plugins + Marketplace |
| **Codex CLI** | AGENTS.md | Skills (SKILL.md; `~/.agents/skills`, `.agents/skills`) | Hooks (6 events, hooks.json or TOML inline) | MCP (config.toml) | Plugins (.codex-plugin/plugin.json) |
| **Gemini CLI** | GEMINI.md (per extension) | Custom commands (slash) | Hooks (hooks/hooks.json) + Policy engine (TOML) | MCP (gemini-extension.json) | Extensions (gemini-extension.json) |

---

## Per-Platform Deep Dive

### Claude Code

**Load model:**
- CLAUDE.md: always injected (user + project + local layers, merge semantics)
- Skills: frontmatter controls — `auto-invoke` (relevance-triggered), `/command` (manual), `isolated` (runs in subagent). As of 2026: commands/ and skills/ unified; skills/ preferred.
- Hooks: 31+ event types (PreToolUse, PostToolUse, Stop, SubagentStart/Stop, SessionStart/End, MessageDisplay, InstructionsLoaded, PermissionRequest, Compact…); 5 handler types: `command` (bash), `prompt` (Haiku, ~$0.001), `agent` (multi-turn subagent), `http` (POST), `mcp_tool`. Multiple hooks fire and merge per event.
- MCP: always available once configured; tools folded into tool-call surface; resources/prompts surfaced per MCP spec.
- Subagents: spun up on-demand; isolated context; summary returned. Nested up to 5 levels (2.1.172).
- Agent Teams: launched 2026-02 (Opus 4.6). Peer-to-peer messaging, shared task list, configured via prompt not YAML.
- Plugins: bundle skills + hooks + subagents + MCP servers; namespaced slash commands (`/plugin:skill`). Plugin-level hooks register as session-scoped when plugin is active.

**MCP trust boundary (important):** MCP skills are content-only — inline shell commands in MCP-sourced skill content do NOT execute (unlike local skill files where `!cmd` runs). [SOURCE: claude-code-from-source.com/ch12-extensibility]

**Agent-parseable surfaces:** Skills have YAML frontmatter (description, auto-invoke, isolated, hooks); hooks use JSON in settings.json; CLAUDE.md is freeform markdown; MCP is JSON-RPC.

[SOURCE: code.claude.com/docs/en/features-overview; claude-code-from-source.com/ch12-extensibility; pub.towardsai.net/claude-code-extensions-explained; arxiv.org/html/2604.14228v1]

---

### Cursor

**Load model:**
- Rules (.mdc files): three modes — `alwaysApply: true` (always injected), glob-scoped (injected when file matches), `description`-only (Agent Decides). Managed via Settings → Rules panel with per-rule toggle.
- Skills (SKILL.md): auto-invoke or `/skill-name`; same frontmatter pattern as Claude Code. Global (`~/.cursor/skills/`) and project (`.cursor/skills/`) scope.
- Hooks (hooks.json): 18+ events. Key events: `sessionStart/End`, `preToolUse/postToolUse/postToolUseFailure`, `subagentStart/subagentStop`, `beforeShellExecution/afterShellExecution`, `beforeMCPExecution/afterMCPExecution`, `beforeReadFile/afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse/afterAgentThought`. Two Tab-specific hooks (`beforeTabFileRead`, `afterTabFileEdit`). One app lifecycle hook: `workspaceOpen` (fires independently of sessions).
- MCP: `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global). `--approve-mcps` auto-trusts all.
- Plugins: bundle rules + skills + agents + commands + hooks + MCP servers. Plugin manifest `.cursor-plugin/plugin.json` with `additionalProperties: false` — controlled extension surface by design. Cursor Marketplace (manually reviewed). cursor.directory for community.
- Agents (subagent definitions): markdown files defining specialized subagent behavior.

**Unique: `workspaceOpen` hook** — fires when workspace opens, independent of agent sessions; can return plugin paths to load dynamically (plugins selected based on workspace context). No Claude equivalent.

**Unique: three CLI modes** (`agent`, `plan`, `ask`) exposed as first-class, including headless via `--mode`. Plan mode is a structured clarification phase, not just context. [SOURCE: 2026-06-14-cursor-cli-composer-integration.md]

**Agent-parseable:** Rules and skills use .mdc frontmatter; hooks JSON; MCP JSON; plugin manifests JSON Schema with strict validation.

[SOURCE: cursor.com/docs/plugins; cursor.com/docs/hooks.md; cursor.com/docs/reference/plugins; pyshine.com/Cursor-Plugins-AI-Code-Editor-Plugin-Specification; rafalsarniak.com/cursor-complete-guide]

---

### Codex CLI

**Load model:**
- AGENTS.md: auto-loaded project context (same role as CLAUDE.md). Symlinked from CLAUDE.md in multi-agent setups (our pattern).
- config.toml: primary config file; `[profiles]` for multi-environment; `[features]` for feature flags incl. `hooks = true/false`.
- Hooks: 6 events — `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `PermissionRequest`, `Stop`. Three outcomes: `proceed`, `block` (with message), `modify` (substitute input — blocked for LocalShell). Config locations: `hooks.json` (standalone) OR inline `[hooks]` in `config.toml`/`requirements.toml`; loading both in same layer warns.
- MCP: config.toml `[mcp_servers]`; runtime enable/disable (0.131+); OAuth for streamable-HTTP; `readOnlyHint` concurrent execution; `$ref`/`$defs`/`oneOf`/`allOf` schema preserved.
- Plugins: `.codex-plugin/plugin.json`; hooks loaded from plugin root `hooks/hooks.json` or overridden in manifest.

**Unique: enterprise trust model.** `requirements.toml` for admin-managed hooks (MDM delivery). `allow_managed_hooks_only = true` disables all user/project/session/plugin hooks — only admin hooks run. Hash-based trust gating: new or modified hooks are marked for review and skipped until user runs `/hooks` to inspect and trust. No other platform has this explicit review-before-run safety.

**Unique: `modify` outcome.** Hook can substitute the tool's input payload before execution (except LocalShell). Claude and Cursor hooks can only proceed/block, not rewrite input.

**Unique: `PermissionRequest` event.** Hook fires when the agent is about to ask the user for permission — can pre-approve or pre-deny, automating permission flows.

**No skills primitive.** Workflow knowledge lives in AGENTS.md or config instructions, not in discrete invokable skill files. The skills/workflow layer is absent — only context + hooks + MCP.

[SOURCE: developers.openai.com/codex/hooks; github.com/openai/codex/pull/11067; github.com/openai/codex/pull/18893; blakecrosley.com/codex-hooks; knightli.com/codex-hooks-advanced]

---

### Gemini CLI

**Load model:**
- GEMINI.md: loaded per-extension (via `contextFileName` in manifest), not a top-level project file. Context injected every session when extension is active.
- Extensions (gemini-extension.json): manifest-based distribution unit containing MCP servers, context files, custom commands, excluded tools, hooks. The primary distribution primitive.
- Hooks: `hooks/hooks.json` inside extension directory. NOT declared in gemini-extension.json — separate discovery. Events parallel to others (before/after tool, lifecycle). JSON stdin/stdout protocol. stderr for debug only.
- Policy engine (TOML rules): unique — extensions can contribute TOML policy rules to a tiered engine. Tier 2 = extension rules (higher than defaults, lower than user/admin). Extensions can BLOCK actions but **cannot AUTO-ALLOW** or enable yolo mode — security asymmetry hardcoded.
- `excludeTools`: extension can disable built-in tools (`run_shell_command`) or specific commands within them (`run_shell_command(rm -rf)`).
- Custom commands: slash commands that encapsulate prompts. Comparable to Claude/Cursor slash commands but without the skills frontmatter system.

**Unique: Policy engine with explicit tiers.** No other platform has a formal tiered policy system. Extensions contribute rules at tier 2; user/admin always wins. Security-asymmetric: extensions can restrict (block) but never expand (allow) beyond user permission.

**Unique: `excludeTools` at extension level.** Can selectively disable built-in tools or specific command patterns. Most fine-grained tool-surface control of any platform.

**No standalone skills primitive.** GEMINI.md is the "playbook" but it's a flat context file, not a structured invokable skill. Custom commands are close to skills but have no frontmatter auto-invoke system.

[SOURCE: google-gemini.github.io/gemini-cli/docs/extensions; github.com/google-gemini/gemini-cli/blob/main/docs/extensions/reference.md; blog.google/gemini-cli-extensions]

---

## MCP Primitives — Design Partition

MCP defines three primitives with a clean design partition [SOURCE: webmcpguide.com/mcp-tools-vs-resources-vs-prompts; llmbestpractices.com/mcp-protocol; jfokus.se MCP Beyond 101 talk]:

| Primitive | Direction | Who invokes | Side effects | Use for |
|---|---|---|---|---|
| **Tools** | Server → Client | LLM (model-invoked) | Yes | Actions, queries, state changes |
| **Resources** | Server → Client | LLM (model-invoked) | No | Read-only context: schemas, files, reference data |
| **Prompts** | Server → Client | User (typically) | No | Reusable templates, workflow guides; surfaced as slash commands |
| **Elicitation** | Client → Server | Server | No | Server requests structured user input mid-execution |
| **Sampling** | Client → Server | Server | No | Server requests LLM completion (coming soon in most clients) |

**Anti-patterns documented:** Don't use Tools for static data → use Resources. Don't embed workflows in tool descriptions → use Prompts. Don't use Resources for dynamic data → use Tools. [SOURCE: jfokus.se MCP Beyond 101]

**MCP support varies:** All four platforms support Tools universally. Resources and Prompts are supported by Claude Code and Cursor but their surface exposure differs. Codex CLI schema preservation (0.134+) is notable: `$ref`, `$defs`, `oneOf`, `allOf` preserved — important for complex tool schemas.

---

## Key Questions Answered

### 1. Do vendors converge on a partition?

**Partial convergence, not full.** The partition is real but the vocabulary varies:

| Layer | Claude Code | Cursor | Codex | Gemini |
|---|---|---|---|---|
| Always-on context | CLAUDE.md | Rules (alwaysApply) | AGENTS.md | GEMINI.md (per extension) |
| Workflow knowledge | Skills | Skills | *(absent)* | Custom commands / GEMINI.md |
| Enforcement/guardrails | Hooks | Hooks | Hooks | Hooks + Policy engine |
| External data/actions | MCP | MCP | MCP | MCP |
| Distribution | Plugins | Plugins | Plugins | Extensions |

**The convergence:** hooks=enforce, MCP=external, a context file=always-on. These three are universal.

**The divergence:** Skills as a discrete primitive (Claude + Cursor) vs. absent (Codex, Gemini). Rules as a loadable-on-match system (Cursor's globs) vs. a single always-on file (Claude's CLAUDE.md). Gemini adds a unique Policy engine tier not present elsewhere.

**Correction (2026-06-16):** Codex **does** have skills (open agent skills standard; same `SKILL.md` as Claude). See `research/2026-06-16-session-surface-errors-verified.md`. Real gaps: mount coverage (`~/.agents/skills` vs full Claude set) and ~8k description index budget, not a missing primitive.

---

### 2. What's unique per vendor — don't abstract away

| Platform | Preserve this |
|---|---|
| **Claude Code** | Hook handler types beyond bash: `prompt` (Haiku), `agent` (multi-turn subagent), `mcp_tool`. Skill-declared hooks that register session-scoped when skill is invoked. MCP trust boundary: content-only for MCP-sourced skills. Agent Teams (peer-to-peer, 2026). |
| **Cursor** | `workspaceOpen` hook (fires independent of sessions; returns plugin paths = dynamic plugin selection). Three CLI modes as first-class flags. `afterAgentThought` hook (observe reasoning, not just actions). |
| **Codex** | `modify` hook outcome (rewrite tool input, not just block). `PermissionRequest` event (pre-approve/deny permission dialogs). Enterprise trust model: hash-gated hook review + `allow_managed_hooks_only`. `requirements.toml` as admin override layer. |
| **Gemini** | Policy engine with explicit tiers (extensions can restrict, never grant). `excludeTools` at extension level (selective built-in tool disable, including sub-command patterns). Security asymmetry hardcoded: extensions cannot expand permissions. |

---

### 3. Where our cross-project architecture matches/fights vendor defaults

**Matches:**

- **Global CLAUDE.md + per-project CLAUDE.md** maps directly to the load model: global context always injected, project-level appended. Cursor's `alwaysApply` rules are the parallel. Codex AGENTS.md symlinks to CLAUDE.md — correct alignment with vendor intent.
- **Shared hooks in `~/Projects/skills/hooks/`** referenced by path in project settings.json — this is architecturally sound; hooks merge from all sources in all platforms.
- **Per-project rules in `.claude/rules/`** — matches Claude Code's rules/ directory discovery. Cursor's `.cursor/rules/` is identical in convention.
- **Skills in `~/Projects/skills/` + symlinks into `~/.claude/skills/`** — aligns with both Claude and Cursor's global skill load path. Cursor loads from `~/.cursor/skills/` globally.
- **Fail-open hooks** — all platforms default fail-open (Codex: "hook failures never block the session"). Our constitution matches the default.

**Fights or friction:**

- **Hook handler types:** Our hooks.json only uses `command` type. Claude Code supports `prompt`, `agent`, `mcp_tool` handlers — we're underusing the surface. A Haiku prompt hook costs ~$0.001 and can do semantic judgment we currently can't do with bash.
- **Codex `modify` outcome:** We use the hooks shim (`codex_hook_shim.py`) to bridge Claude hooks to Codex. But `modify` (input rewriting) has no Claude equivalent — any hook that needs to rewrite tool input in Codex is a Codex-specific capability we can't share.
- **Cursor rules vs Claude skills for context:** We use `.cursor/rules/` (Cursor) and `.claude/rules/` (Claude) as separate directories with separate content. The load models differ: Cursor rules have glob-scoped auto-load (e.g., only when editing `*.py`); Claude rules don't have glob-scoped loading for rules (that's skills frontmatter). We maintain both manually — this is correct given the divergence.
- **No skills in Codex:** Our shared skills (`~/Projects/skills/`) are Claude + Cursor concepts. Codex has no equivalent invocation mechanism. Any workflow we encode as a skill is Codex-invisible unless we flatten it into AGENTS.md.
- **Gemini's Policy engine:** We have no integration with Gemini's TOML policy tier. Our hooks-in-hooks.json approach would be Gemini hooks (compatible), but the policy engine is an orthogonal surface we don't use.
- **MCP Prompts primitive:** We use MCP for tools only. Resources and Prompts are available and underused — Resources especially suit our always-loaded reference data (research index, codebase maps) better than context files (they don't count against always-loaded context budget the same way).

---

## Architectural Implications

1. **Codex skills: sync coverage + budget, not AGENTS.md bridge.** Codex discovers `~/.agents/skills` and `.agents/skills` (via `codex_parity_sync`). Gaps: incomplete symlinks vs Claude (22 vs 41 global), combined description budget (intel session ~14k chars vs 8k ceiling). Agentlogs does not record Codex `Skill` tool calls — skill loads appear as `exec_command` reads of `SKILL.md`.

2. **MCP Resources deserve a look for our always-loaded context problem.** We have a ~30k always-loaded ceiling (drift-sentinel monitors this). Moving reference data (research-index, codebase maps) into MCP Resources means they're fetchable on-demand vs. always-injected.

3. **Prompt hooks (Claude Code, Haiku) are semantic guardrails at $0.001/call.** Our current hooks are all bash-deterministic. The `prompt` handler type is the right place for semantic judgment calls we currently can't enforce deterministically.

4. **Codex `modify` outcome is an untapped capability.** Rather than blocking and re-asking, a Codex `PreToolUse` hook that rewrites tool input can correct minor deviations without interrupting flow. No Claude equivalent — Codex-specific capability.

5. **Cursor `workspaceOpen` hook enables workspace-conditional plugin loading.** If we ever want project-type-aware plugin sets (e.g., load genomics skills only in genomics workspaces), `workspaceOpen` is the mechanism. Not available in Claude Code.
