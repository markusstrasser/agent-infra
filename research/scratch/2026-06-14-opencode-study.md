# OpenCode Study — What agent-infra Can Appropriate

**STATUS: STUDY IN PROGRESS**

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

## Appropriation Candidates
(in progress)

## Novel vs Claude Code
(in progress)
