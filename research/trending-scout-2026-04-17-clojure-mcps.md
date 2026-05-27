# Trending Scout — Clojure MCPs & UI Debugging (2026-04-17)

**Focus:** Clojure + Claude Code / Codex / Gemini CLI, cljs tooling, REPL-driven agent workflows, UI debugging.
**Window:** ~Oct 2025 – Apr 2026.
**Sources:** Exa, Brave, GitHub (bhauman, hugoduncan, Bigsy, ChromeDevTools).

---

## Headline

bhauman's **clojure-mcp** is the clear leader (723★, v0.3.1 on 2026-03-14) and has split into two philosophies: the full MCP server and a new **clojure-mcp-light** that *does not* replace native Claude Code tools and instead sits on hooks + CLIs. For UI/cljs debugging, the interesting pairing is bhauman's shadow-cljs REPL bridge + Google's **Chrome DevTools MCP** (Sept 2025 public preview) — together these close the "agent codes blindfolded in the browser" gap.

---

## New Findings (ranked)

### 1. clojure-mcp-light (new, bhauman) — ⭐ highest interest

| Field | Content |
|-------|---------|
| URL | https://github.com/bhauman/clojure-mcp-light |
| What | Three Babashka CLI tools: `clj-nrepl-eval` (REPL eval with persistent session), `clj-paren-repair-claude-hook` (PreToolUse hook that auto-fixes delimiters before Write/Edit hits disk), `clj-paren-repair` (on-demand CLI for Codex / Gemini CLI). |
| Why relevant | Matches our harness philosophy exactly: *"work **with** the client's native tools instead of replacing them."* Paren repair as a PreToolUse hook = **zero token cost**, preserves Claude Code's diff UI. This is the pattern we already use for data-guard / append-only-guard. |
| Integration path | **Adopt if we ever have a Clojure project.** The hook design is also a reusable pattern for other syntactically-picky languages (OCaml, Nix, Racket). |
| Overlap | None — we have no Clojure in the stack today. Pattern overlap with our pretool hooks. |
| Verdict | **Extract pattern** (PreToolUse-based syntax repair, zero-token) + **Watch** repo. |

### 2. clojure-mcp v0.3.1 (bhauman, 2026-03-14)

| Field | Content |
|-------|---------|
| URL | https://github.com/bhauman/clojure-mcp |
| What's new in 0.3.x | `:enable-tools` / `:disable-tools` / `:add-tools` / `:remove-tools` via CLI and `main/start` — no config files needed. `:config-profile :cli-assist` = minimal toolset tailored for Claude Code / Codex / Gemini CLI. `deps_grep` now requires `:type` and filters binaries. |
| shadow-cljs | Issue #150 (closed 2026-03-14): CLJS-mode status message prepended to every eval result. bhauman kept it after trying removal — without it, Claude guessed wrong REPL and burned tokens running `lsof` looking for nREPL ports. Configurable via `:shadow-cljs-repl-message false`. |
| Verdict | **Watch** — canonical answer if Clojure ever enters the stack. |

### 3. Chrome DevTools MCP (Google, Sept 2025 preview)

| Field | Content |
|-------|---------|
| URL | https://github.com/ChromeDevTools/chrome-devtools-mcp |
| What | MCP server wrapping Chrome DevTools Protocol via Puppeteer. Gives agents native access to: network traffic, DOM, console, performance traces. No more screenshot / paste-the-error dance. |
| Why relevant | For any cljs / React / Svelte / plain-web UI work — this is the "eyes for the agent" tool. Pairs naturally with bhauman's shadow-cljs REPL: agent evaluates CLJS → observes the resulting DOM / console via DevTools MCP → iterates. Full-stack cljs debugging loop without human in the middle. |
| Overlap | We have `claude-in-chrome` (browser automation extension) in the global harness — overlaps on DOM/console access. DevTools MCP goes deeper (network, perf traces, CDP primitives) but requires Puppeteer lifecycle. |
| Verdict | **Watch** — worth a probe session next time we do browser QA work. |

### 4. Supporting Clojure MCPs (minor)

| Repo | Purpose | Note |
|------|---------|------|
| `Bigsy/clj-kondo-MCP` | clj-kondo linting via MCP | Fills gap for clients without built-in lint (Claude Desktop). Claude Code already lints via shell, so lower value. |
| `Bigsy/Clojars-MCP-Server` | Clojars dep lookup | Useful for agents proposing libraries. |
| `hugoduncan/mcp-clj` | Alt MCP server in Clojure (`clj-eval`, `ls`) | Small scope; bhauman's is more mature. |

---

## Version Bumps

| Tool | Prev known | Current | Source |
|------|-----------|---------|--------|
| clojure-mcp | n/a (first time tracked) | v0.3.1 (2026-03-14) | GitHub releases |
| clojure-mcp-light | n/a (new) | pre-release (CLAUDE.md in repo) | GitHub |

---

## Takeaway for Our Harness

1. The **hook-based syntax repair** pattern in clojure-mcp-light generalizes — consider it the next time we touch a language that needs structural edits (e.g., if we ever need TS JSX repair, or YAML/TOML balancing).
2. The **shadow-cljs tokens-for-state-clarity** tradeoff (bhauman kept the "NOT in CLJS mode" banner because removing it wasted more tokens via `lsof` probes) is a nice data point for our own `source-check` / status-banner hooks: stable context reduces exploration cost.
3. **Chrome DevTools MCP** is the bigger deal for us than any Clojure-specific MCP — it's a generic UI-debugging capability. Worth probing even without cljs.

---

## Search Log

- Exa: clojure-mcp REPL ✓, cljs UI debugging shadow-cljs ✓, Chrome DevTools MCP ✓
- Brave: clojure MCP Claude 2026 ✓
- Not searched: arxiv (out of scope), alphaXiv (out of scope).
- Gaps: no info on Codex-specific Clojure integrations beyond bhauman's `:cli-assist` profile.

<!-- knowledge-index
generated: 2026-04-17T21:13:37Z
hash: 42db1bf61ad7


end-knowledge-index -->
