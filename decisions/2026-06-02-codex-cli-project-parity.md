---
date: 2026-06-02
concept: cross-tool-parity
status: implemented
relates_to:
  - cross-project-architecture
  - AGENTS.md-symlink-convention
---

# Codex CLI gets a generated `.codex/` mirror of each repo's `.claude/` assets

## Context

intel/genomics/phenome keep their tooling under `.claude/` (skills, hooks) and
`.mcp.json`. The cross-tool story so far was only `AGENTS.md → CLAUDE.md`
(instructions). Codex CLI (0.135) does **not** read `.claude/` or `.mcp.json`, so
Codex sessions in those repos were missing project MCP tools, project hooks, and
(nominally) project skills.

## What Codex 0.135 actually loads (verified empirically, not just docs)

- **Instructions:** `AGENTS.md` (+ `~/.codex/AGENTS.md`). Already wired via symlink.
- **MCP:** global `~/.codex/config.toml [mcp_servers]` **+** project `.codex/config.toml`
  (trusted projects only). Project servers **MERGE** with global (union); same-id
  project entry **overrides** global. *Tested:* dropped a project `.codex/config.toml`,
  `codex mcp list` showed all 18 global servers **plus** the project's `corpus`, and
  intel's `duckdb` flipped to the motherduck override.
- **Skills:** auto-discovered from `.agents/skills/` (cwd→repo root), `~/.agents/skills`,
  `/etc/codex/skills`, bundled. NOT `.claude/skills`. (These repos already had
  `.agents/skills -> .claude/skills` symlinks since Apr 2026.)
- **Hooks:** global `~/.codex/hooks.json` **+** project `.codex/hooks.json` (or `[hooks]`
  in `.codex/config.toml`). Hooks **MERGE** with global. Same contract as Claude Code:
  events (`SessionStart`/`UserPromptSubmit`/`PreToolUse`/`PostToolUse`/`Stop`/…),
  `$CLAUDE_TOOL_INPUT`, **exit-2 + stderr** to block, `additionalContext` to inject, and
  **Claude-style tool-name matchers** (`Bash`, `Write|Edit`→`apply_patch`,
  `mcp__server__tool`) which Codex normalizes to. *Tested:* a `codex exec` shell turn ran
  the full lifecycle — `PreToolUse` ×18 fired **before** the `zsh -lc` exec, then
  `PostToolUse`, then `Stop`. Hooks appear to run in a restricted FS sandbox (a probe's
  `/tmp` write didn't land though the hook fired) — block/advisory paths don't need FS
  writes, so this doesn't affect gates.

## Decision

Generate the Codex-local mirror with `scripts/codex_parity_sync.py`; keep the source of
truth in each repo's **committed** `.claude/` + `.mcp.json`.

- `.codex/config.toml` = **delta** MCP servers only (missing-from-global + explicit
  intentional overrides). Relying on merge avoids re-emitting secret-bearing global
  servers. The delta servers (corpus, genomics-consumer, domains, paperclip, intel
  duckdb) carry no secrets.
- `.codex/hooks.json` = project hooks with `$CLAUDE_PROJECT_DIR` and relative
  `.claude/hooks`/`scripts/hooks` paths **absolutized** (Codex runs hooks at session cwd).
- `.codex/` is **gitignored** (like the pre-existing `.agents/`): it's a derived,
  machine-local artifact with absolute paths. friend-sync regenerates it daily;
  `just codex-parity[ --check]` on demand; `--check` is in `just smoke`.

### Rejected

- **Commit `.codex/`** — would bake machine-specific absolute paths into git. The
  AGENTS.md *symlink* travels with the repo; a generated config with absolute hook paths
  should not.
- **Full mirror of `.mcp.json` into `.codex/config.toml`** — would duplicate (and risk
  leaking) secret-bearing global servers; merge makes delta-only correct.
- **Auto-override every `.mcp.json`↔global difference** — global is often the canonical
  one (e.g. genomics' `.mcp.json` still names the deprecated
  `@modelcontextprotocol/server-brave-search` vs global's `@brave/brave-search-mcp-server`;
  exa's global URL has the real key + an extra tool). Differences are **reported as
  divergences**, overridden only via an explicit allowlist (`intel: duckdb`).

## Separate finding (not fixed here — needs interactive auth)

Codex sessions on this machine **stall** when MCP is loaded: `rmcp ... TokenRefreshFailed
("invalid_grant: Refresh token is invalid or expired")`. The only OAuth remote MCP is
**scite**; with MCP cleared (`-c 'mcp_servers={}'`) a `codex exec` turn completes in
seconds. Fix: `codex mcp login scite` (or disable the scite server). Flagged to operator.
