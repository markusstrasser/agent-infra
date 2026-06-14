# OpenCode Study — What agent-infra Can Appropriate

**STATUS: COMPLETE**

Date: 2026-06-14
Target: /Users/alien/Projects/best/opencode (SST's open-source AI coding agent, TypeScript)
Goal: Identify mechanisms agent-infra (Python/uv, runs ON Claude Code) can appropriate.

Standing vetoes to respect: repo-tools MCP (0 usage), PageRank symbol graph for code-nav, autobrowse-style auto skill-graduation.

---

## Architecture Map

### Monorepo layout (bun workspaces, Turbo, Effect-TS)
27 packages under `packages/`. Key ones:
- `opencode` — the agent runtime + CLI (largest). Subdirs: session, tool, permission, provider, lsp, mcp, skill, agent, server, share, snapshot, worktree, acp, bus, command, question.
- `core` — shared v2 substrate (Effect services): session, tool, permission, system-context, instruction-context, skill, database (drizzle-sqlite), pty, ripgrep.
- `llm` — provider/model abstraction (anthropic, openai, google, bedrock, azure, openrouter, xai, cloudflare, github-copilot, openai-compatible). route/ = transport+protocol+framing+auth.
- `server` — Hono HTTP server: routes grouped (session, message, permission, provider, model, pty, fs, agent, command, question). This is the **client/server split**: TUI/desktop/web are all clients of one local HTTP server.
- `sdk/js` — generated TS SDK from `packages/sdk/openapi.json` (OpenAPI → client). `AGENTS.md`: "To regenerate the JavaScript SDK, run ./packages/sdk/js/script/build.ts".
- `tui` (Go-ish opentui), `desktop` (Tauri-like), `app`/`web` (SolidJS), `plugin`, `slack`, `enterprise`, `console`, `stats`.

### Client/server split — WHY
The agent runs as a **local HTTP server** (Hono, `packages/server`); every UI (terminal TUI, desktop, web, Slack, ACP/editor) is a thin client over the same OpenAPI surface + an event bus. One agent core, many heads. The SDK is generated from the server's OpenAPI spec so all clients stay in lockstep. Sharing (`session/share`) extends the same model to a hosted read-only viewer.

### Model/provider abstraction (claims 300+ models)
- `packages/llm/src/provider.ts:19` — `Definition` is `{ id, model: ModelFactory, apis? }`. `make()` (`provider.ts:38`) is a structural validator (NoExtraFields).
- Providers are thin adapters (`providers/anthropic.ts`, `openai.ts`, `google.ts`, `openrouter.ts`, `openai-compatible.ts` …). The 300+ count comes from `openrouter` + `openai-compatible` + `models.dev` catalog metadata, NOT 300 hand-written adapters.
- `route/` separates **transport** (HTTP framing, SSE), **protocol** (provider wire encoding), **auth** (`route/auth.ts`), and **endpoint**. CONTEXT.md: "the selected protocol adapter alone owns provider wire encoding." Generation controls (sampling) are partitioned from provider-semantic options from compatibility-wire fields in the Catalog — a clean 3-domain split.

### LSP integration
`packages/opencode/src/lsp/` + `tool/lsp.ts` + `tool/lsp.txt`. LSP is exposed to the model AS A TOOL (diagnostics, hover). Separate from grep/glob/read which use ripgrep (`core/ripgrep`).

### Permission/approval system — last-match-wins wildcard ruleset (NOVEL vs CC)
- `packages/opencode/src/permission/index.ts:38` — `evaluate(permission, pattern, ...rulesets)` does `rulesets.flat().findLast((rule) => Wildcard.match(permission, rule.permission) && Wildcard.match(pattern, rule.pattern)) ?? {action:"ask", ...}`.
- `core/permission/schema.ts` (v2): a `Rule` is `{action, resource, effect: allow|deny|ask}`; a `Ruleset` is an ordered array. **Last matching rule wins** — so later/more-specific rules override earlier ones. Default when nothing matches = `ask`.
- Tools request permission declaratively: `ctx.ask({ permission: "skill", patterns: [name], always: [name], metadata })` (see `tool/skill.ts:28`). `always` lets the user grant a standing allow for that pattern.
- This is a unified, composable, ordered policy model. Claude Code's settings.json allow/deny is flatter (separate allow + deny lists, deny wins) and less expressive about ordering/override.

### System Context Registry + Context Sources + Context Epochs — THE standout mechanism (NOVEL)
Defined in CONTEXT.md (14KB glossary) + implemented in `core/src/system-context/`.
- `system-context/index.ts:32` — `Source<A>` = `{ key, codec, load: Effect<A|Unavailable>, baseline(A)→str, update(prev,cur)→str, removed?(prev)→str }`. Each contextual fact is an independently-observed typed value with a stable namespaced key (regex-branded, `index.ts:22`).
- `SystemContext.make<A>` (`index.ts:131`) closes over the value type → opaque composable carrier. `combine` (`:172`) rejects duplicate keys.
- `initialize` (`:194`) renders the **Baseline System Context** + a durable JSON **Snapshot** at the start of a **Context Epoch**. `reconcile` (`:214`) re-observes, diffs each source against the snapshot, and emits ONE **Mid-Conversation System Message** containing only what changed ("The available skills have changed. This list supersedes the previous list."). `replace` (`:279`) makes a fresh baseline on compaction/model-switch.
- **Unavailable** (`:28`, a Symbol) = stale-while-revalidate: a source that can't be observed keeps its prior admitted value and blocks a baseline replacement rather than silently dropping context.
- `registry.ts` — Location-scoped registry of ordered producers; `load()` sorts by key and combines concurrently so rendered context is deterministic.
- `builtins.ts` — env block + date are context sources. `skill/guidance.ts:59` — the available-skills list is a context source that emits an update message when the agent's permitted skill set changes. AGENTS.md/instructions are a context source (`instruction-context`).
- **Why it's novel:** instead of rebuilding the whole system prompt every turn (cache-busting) or letting it go stale, opencode keeps a cache-stable baseline and injects targeted "X changed" system messages mid-conversation, with durable snapshots that survive process restarts within an epoch. Compaction/model-switch is the only thing that rebuilds the baseline (because the provider cache prefix dies anyway).

### Subagent permission derivation (NOVEL, principled)
- `agent/subagent-permissions.ts:14` — `deriveSubagentSessionPermission` builds a child session's ruleset = parent's `deny` rules + `external_directory` rules, PLUS default deny on `todowrite` and `task` unless the subagent's own config grants them. Comment: "Parent agent restrictions only govern that agent; the subagent's own permissions determine its capabilities."
- `tool/task.ts:125-158` — at spawn, child gets `[...childPermission, ...childToolDenies]` where childToolDenies also strips `experimental.primary_tools`. So a subagent can't recursively spawn tasks or write todos by default — capability narrows monotonically down the tree.

### external_directory whitelist (filesystem scoping)
- `agent/agent.ts:104-115` — default `external_directory` policy is `{"*": "ask", <skillDirs>: "allow", <referenceDirs>: "allow", tmp: "allow", truncationDir: "allow"}`. Any read/write outside the project + known-safe dirs prompts. This is the data-protection concern agent-infra enforces via hooks, expressed as a declarative permission ruleset instead.

### Centralized tool-output truncation with adaptive spill hint
- `tool/truncate.ts:15-17,85-141` — the Tool Registry (`tool/tool.ts:131-144`) auto-truncates EVERY tool's output to `MAX_LINES=2000`/`MAX_BYTES=50KB` (configurable via `tool_output` in config), spills full text to a 7-day-retention managed file (`truncate.ts:13`, `RETENTION = Duration.days(7)`), and appends an adaptive hint: if the agent has a `task` tool → "Use the Task tool to have explore agent process this file… Do NOT read the full file yourself - delegate to save context" (`:130`); otherwise "Use Grep… or Read with offset/limit" (`:131`). Tools may pre-shape output but the registry enforces the final ceiling. Hourly background cleanup (`:143-148`).

### Agents as first-class typed config + LLM-generated agents
- `agent/agent.ts:34-55` — `Info` schema: `{name, description, mode: subagent|primary|all, permission: Ruleset, model?, variant?, prompt?, temperature?, topP?, steps?, hidden?}`. Agents live in `.opencode/agent/<name>.md` (markdown w/ frontmatter) per `customize-opencode.md:244`.
- `agent.ts:69-78` + `generate.txt` — `generate({description})` uses an LLM (`generateObject`) to author a new agent (`{identifier, whenToUse, systemPrompt}`) from a one-line description. Agent self-authoring.

### Plugin hook system — in-process typed JS callbacks (vs CC subprocess hooks)
- `plugin/src/index.ts` `Hooks` interface — typed async callbacks invoked in-process: `chat.params` (mutate temperature/topP/maxTokens/options), `chat.headers`, `permission.ask` (override allow/deny/ask), `tool.execute.before`/`tool.execute.after` (mutate args / output), `tool.definition` (rewrite a tool's description+params before the model sees it), `shell.env`, `experimental.chat.system.transform` (mutate the system prompt array), `experimental.chat.messages.transform`, `experimental.session.compacting` (customize compaction prompt), `experimental.compaction.autocontinue` (toggle the synthetic "continue" turn after compaction), `experimental.provider.small_model`. Plugins can also register `tool`, `auth` (OAuth/API flows), `provider` (dynamic model lists), and workspace adapters. All strongly typed against the SDK.

### AGENTS.md upward discovery as a re-loadable context source
- `instruction-context.ts:39-71` — discovery walks UPWARD from cwd to project root (`fs.up({targets:["AGENTS.md"], start, stop})`), dedupes with the global config AGENTS.md, honors `OPENCODE_DISABLE_PROJECT_CONFIG`. If a discovered file becomes unreadable → returns `unavailable` (keeps prior, doesn't drop). When the instruction set changes mid-session it emits "These instructions replace all previously loaded ambient instructions." (`:35`); when none remain, "Previously loaded instructions no longer apply." (`:36`).

### Client/server + generated SDK
- `packages/server` (Hono) is the single agent core; `packages/sdk/openapi.json` → generated TS client (`AGENTS.md`: "regenerate the JavaScript SDK, run ./packages/sdk/js/script/build.ts"). All UIs (tui/desktop/web/slack/acp) are clients. Event bus (`src/bus`, `EventV2`) pushes session/permission/message events to clients.

---

## Appropriation Candidates (ranked by value-to-agent-infra)

### 1. Subagent permission derivation — capability narrows monotonically down the tree
**What:** A pure function (`agent/subagent-permissions.ts:14`) that computes a child session's permission ruleset = (parent's deny + external_directory rules) + default-deny on recursion-enabling tools (`task`, `todowrite`) unless the child's own config opts in.
**Why agent-infra:** This is the *declarative* version of what agent-infra enforces with prose + hooks: "analysis subagents must not commit", "default isolation: worktree", "subagents have silently dropped test files." Agent-infra's subagent safety is currently instructions (CLAUDE.md `<subagent_usage>`) + a zero-output gate + worktree isolation. opencode's insight — *a subagent's blast radius should be a computed subset of its parent's, with recursion denied by default* — is a checkable invariant agent-infra lacks. Concrete fit: a PreToolUse `Agent`-dispatch hook (Python) that asserts the spawned agent's declared tool set ⊆ parent's, and denies nested `Agent`/commit tools unless the agent type is on an allowlist. This is architecture-over-instructions for the exact failure class agent-infra logs (8+ build-then-undo, dropped test files). NOT a veto, NOT native to CC (CC subagents inherit a flat tool allowlist, no parent-derived narrowing).

### 2. Centralized tool-output truncation w/ retention-managed spill + delegate-aware hint
**What:** Registry-level cap on EVERY tool's output (`truncate.ts`), full text → 7-day-retention file, hint adapts to whether a Task tool exists ("delegate to subagent, do NOT read it yourself" vs "Grep/Read offset").
**Why agent-infra:** Directly serves the declining-supervision/context-rot objective. agent-infra's context-budget rules fight always-loaded bloat but there is NO ceiling on *tool output* flooding a session — a single `git log`/`rg`/`cat` dump can blow context, and agent-infra has logged "search flooding" as a cascading-waste category (constitution Principle 2 table). A Python PostToolUse hook (Bash/Read/Grep) that, above N lines, writes the full output to a retention dir under `.claude/` and replaces it with a head+tail preview + "delegate to Explore agent" hint, is a near-direct port. The delegate-aware hint operationalizes agent-infra's own "subagents are context shields" rule at the point of overflow. The 7-day retention + hourly cleanup maps to the existing `reclaim-rotate` launchd job. Cheap, no-downside, recurring problem → fix-worthy. NOT a veto, NOT native to CC (CC truncates but doesn't spill-to-file with a delegate hint).

### 3. System Context Registry — context as typed, independently-refreshable sources with mid-conversation "X changed" deltas
**What:** `core/src/system-context/` — every contextual fact (env, date, AGENTS.md, skill list) is a `Source<A>` with a stable key, codec, loader, and baseline/update/removed renderers. A durable snapshot tracks last-admitted values; on each safe boundary, `reconcile` emits ONE delta system-message naming only what changed, keeping the cache-stable baseline intact until compaction/model-switch.
**Why agent-infra:** This is the principled answer to agent-infra's recurring "stale CLAUDE.md / context-rot" pain (context-budget-principles.md: "topically-close-but-stale text hurts MORE than irrelevant bulk… prune for staleness first"). agent-infra fights this with prune-and-slim discipline + a `postcompact-verify` hook; opencode instead *re-observes sources every turn and surfaces deltas* without cache-busting. BUT: agent-infra runs ON Claude Code and cannot inject mid-conversation system messages (CC owns the prompt loop) — so this is NOT directly portable as-is. The appropriable *idea*: treat agent-infra's own injected context (the `drift-digest.md`, `blindspot-digest.md`, `checkpoint.md` SessionStart surfaces) as keyed sources with explicit "this supersedes the prior" framing and removal messages, rather than re-dumping. Lower immediate ROI than #1/#2 because of the CC-owns-the-loop ceiling; valuable as a design lens for the surfacing scripts. Flag honestly: partial fit, ceiling-limited.

### Lower-priority / context only
- **Last-match-wins wildcard permission ruleset** (`permission/index.ts:38`): elegant, but CC already has settings.json allow/deny and agent-infra layers hooks on top. Adopting a new policy engine = rebuild risk for marginal gain. Skip as infra; borrow only the *mental model* (ordered override) if rewriting any permission prose.
- **Plugin hooks as typed in-process callbacks** (`plugin/index.ts`): genuinely cleaner than CC's subprocess-shell hooks (typed I/O, no JSON envelope parsing, can mutate the system prompt / compaction prompt). But agent-infra is committed to CC's hook contract (`hook-input-contract.md`, codex shim) and Python; porting the *transport* is a non-starter. Worth noting as evidence that the shell-hook envelope is a deliberate CC constraint, not a universal one. Skip (transport lock-in), but see Novel section.
- **LLM-generated agents** (`agent.ts:generate` + `generate.txt`): CC/agent-infra author agents by hand; auto-generation from a description is a minor convenience, not a leverage point. Adjacent to the autobrowse skill-graduation veto in spirit (auto-authoring config) — do not pursue.

## Novel vs Claude Code (things CC does NOT do that opencode does well)
1. **Context Sources + mid-conversation deltas** (`system-context/`): CC rebuilds the system prompt or lets CLAUDE.md sit static; opencode re-observes typed sources each turn and injects targeted "X changed, this supersedes the prior" messages while preserving the provider cache prefix. The stale-while-revalidate `unavailable` symbol (don't drop a source you merely failed to read) is a clean idea CC has no analogue for.
2. **Monotonic subagent capability narrowing** (`subagent-permissions.ts`): CC subagents get a flat tool allowlist; opencode computes the child's blast radius as a subset of the parent's and denies recursion (`task`/`todowrite`) by default.
3. **Registry-enforced tool-output bounding + managed spill files + delegate-aware hint** (`truncate.ts`): CC truncates inline; opencode spills to a retention-managed file and tells the model to delegate the full file to a subagent rather than reading it.
4. **One agent core, many UIs via local HTTP server + generated SDK** (`packages/server`, `sdk/openapi.json`): CC is a single CLI; opencode's client/server split makes TUI/desktop/web/Slack/editor (ACP) all thin clients of one OpenAPI surface with a shared event bus. Not relevant to appropriate (agent-infra wraps CC, doesn't replace it) but architecturally notable.
5. **Typed in-process plugin hooks that can rewrite the system prompt, tool definitions, compaction prompt, and the post-compaction auto-continue** (`plugin/index.ts`): far finer-grained than CC's subprocess hooks, especially `experimental.chat.system.transform`, `tool.definition`, and `experimental.session.compacting`/`compaction.autocontinue`.
6. **External-directory access as a declarative `*: ask` + whitelist ruleset** (`agent/agent.ts:104`) rather than hook-enforced data protection.
