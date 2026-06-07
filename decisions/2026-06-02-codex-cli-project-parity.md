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

## Revision 2026-06-07 — Codex hook firing matrix (corrects an over-claim)

The original note assumed Claude hooks "port over" once tool-name matchers were
mirrored. **That is wrong**, per OpenAI's own `migrate-to-codex/references/
differences.md` (bundled with codex-cli **0.137**). The bridge faithfully *copies*
hooks, but Codex only *fires* a subset:

| Claude hook | Fires under Codex 0.137? | Note |
|---|---|---|
| `PreToolUse` matcher `Bash` | ✅ LIVE | shell commands only |
| `PostToolUse` matcher `Bash` | ✅ LIVE | only Bash matched |
| `SessionStart` / `UserPromptSubmit` / `Stop` (matcher-less) | ✅ LIVE | matcher ignored |
| `PreToolUse`/`PostToolUse` matcher `Write`,`Edit`,`Read`,`Agent`,`Skill`,`WebSearch`,`WebFetch`,`mcp__*` | ❌ INERT | **runtime never invokes them** |

Measured on the generated mirrors: intel had **4 LIVE / 13 INERT**, phenome **3 / 3**.
The inert matchers are copied, pass `codex-hook-compat` (valid JSON / exit codes), and
still **never run**. So Codex's subagent tool is `spawn_agent`, but there is *no*
pre-dispatch hook point — `PreToolUse:Agent` (and the new
`pretool-inventory-dispatch.py`) are **Claude-only by Codex's design**, not a bridging
gap. Symlinks cannot fix a hook the runtime won't call.

**Consequences for "make tooling work on Codex":**
- Write/Edit enforcement that must run under Codex has to be re-expressed as a **Stop
  hook** (OpenAI's explicit guidance) — e.g. the append-only guard, source-remind, and
  provenance-warn hooks are currently inert under Codex.
- Subagent-dispatch guards (subagent-gate, inventory-before-dispatch) have **no Codex
  equivalent** until Codex extends `PreToolUse` beyond shell. Accept as Claude-only.

**Proposed (NOT YET BUILT — shared infra, needs cross-model review per Constitution
Principle 12):** a *capability-aware* pass in `codex_parity_sync.py` that, instead of
copying every matcher, (1) emits a per-repo **LIVE/INERT coverage report** so the inert
reality is visible each sync (report-only first — Principle 3), and (2) optionally
**remaps** a small allowlist of critical Write/Edit guards to `Stop` hooks so they
actually enforce under Codex. Until then, the firing matrix above is the authoritative
reference — no per-hook re-derivation.

## CORRECTION 2026-06-07 (same day) — the Revision above is WRONG; primary source overrides

The Revision was built on the bundled `migrate-to-codex/references/differences.md`
("PreToolUse runs for shell commands only"). **That doc is STALE.** Verifying against the
shipped Rust **at the exact installed tag `rust-v0.137.0`** (`core/src/tools/hook_names.rs`,
`registry.rs`, `hook_runtime.rs`) shows the opposite:

- PreToolUse/PostToolUse fire for **all function tools** — `dispatch_any` →
  `run_pre_tool_use_hooks` for every invocation, not shell-only.
- Codex ships **built-in Claude-style matcher aliases**: `apply_patch()` →
  `["Write","Edit"]`, `spawn_agent()` → `["Agent"]`. So `Write|Edit` and `Agent`
  matchers **DO fire** under Codex 0.137. The change landed in PR #23757
  ("Default function tools into tool hooks", 2026-05-23); differences.md predates it.

**Net:** the ORIGINAL bridge (copy Claude matchers verbatim) was correct — Codex's own
aliases handle the translation, so **no capability-aware remap is needed**. The
LIVE/INERT-report and Write/Edit→Stop proposals above are **withdrawn** (their premise was
false). Residual genuinely-inert matchers are only `Read`/`WebSearch`/`WebFetch` (Codex has
no identically-named tool) — minor, not worth a sync change. The corrected firing matrix
now lives in `scripts/codex_parity_sync.py`'s module docstring.

Lesson (logged): a bundled vendor *doc* lost to the vendor's own *source at the installed
tag*. Verify hook/runtime behavior against the shipped binary's source, not migration
guides. This is the `<ai_text_policy>` "verify vendor claims before asserting" rule biting
in practice.
