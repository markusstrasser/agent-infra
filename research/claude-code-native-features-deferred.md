# Claude Code Native Features — Deferred Adoption Items

**Date:** 2026-04-03 (updated)
**Source:** Manual changelog/ecosystem sweep of Anthropic repos (v2.1.63–v2.1.91, Agent SDK v0.1.55)
**Status:** Tracking — items here are viable but deferred for specific reasons

## 1. API-Level MCP Connector (Anthropic SDK v0.50+)

**What:** Declare remote MCP servers in API request config. The API handles connection, tool discovery, retries, and timeouts — no local subprocess management needed.

**Our current approach:** All 6 MCP servers are local subprocesses spawned via `.mcp.json`. For orchestrator SDK `query()` calls, this means the orchestrator process manages subprocess lifecycles.

**Why defer:** Our MCP servers are all local (research, meta-knowledge, context7, firecrawl, exa, brave-search). The API-level connector is designed for *remote* MCP servers. No benefit until we have a remote server to connect to. If we moved any MCP server to a remote deployment (e.g., research-mcp as a shared service), this would become relevant.

**Trigger to revisit:** When any MCP server needs to be shared across machines or deployed remotely.

## 2. Tool Output Compression (`updatedToolOutput`)

**What:** PostToolUse hooks that compress tool results before they enter conversation context. Community data: 60% of context tokens are tool results, 82% compressible. Currently works for MCP tools (`updatedMCPToolOutput`); built-in tool support is an open feature request (#32105).

**Our current approach:** No compression. Sessions hit context limits regularly. Statusline shows context rate and ETA to compaction.

**Why partially defer:** `updatedMCPToolOutput` works NOW for MCP tools. Built-in tool compression (Bash, Read, Grep results) is the bigger win but isn't shipped yet.

**What we could do now:**
- Build MCP-side result compression for our custom servers (meta-knowledge, research). These return markdown blobs that could be summarized.
- Write a PostToolUse hook that uses `updatedMCPToolOutput` to trim verbose MCP results.

**What requires the feature (#32105):**
- Compressing Bash output (git status, test results)
- Compressing Read output (full file dumps when only a section matters)
- These are the highest-volume context consumers

**Trigger to revisit:** When #32105 ships (subscribe to github.com/anthropics/claude-code/issues/32105).

## 3. Scoped Write-Access MCP Tools

**What:** Cookbook SRE agent pattern — MCP tools with built-in safety scoping: restricted directories, command allowlists, result validation. Pattern: "provide write access through narrow MCP tools with built-in safety checks, not broad permissions."

**Our current approach:** Orchestrator cross-project steps use `claude -p` with full permissions + constitutional approval gates. The agent gets broad tool access; the gate is at the human checkpoint.

**Why defer:** Our approval gates work. The scoped-MCP pattern is more relevant for production deployments where approval gates aren't practical (CI/CD, unattended operation). Our orchestrator is always supervised.

**Potential application:** If we move to unattended orchestrator ticking (launchd revival), scoped MCP tools per pipeline would replace the current approval gates with architectural constraints. Example: a `session-retro` pipeline gets an MCP server that can only write to `improvement-log.md` and `artifacts/session-retro/`.

**Trigger to revisit:** When we revive launchd-based orchestrator ticking or want to remove manual approval gates.

## 4. Agent Teams (Experimental)

**What:** Native multi-agent coordination: `TeamCreate`, `SendMessage`, `TeammateIdle`/`TaskCompleted` hooks, file-based inter-agent messaging. Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

**Our current approach:** Serial task queue (orchestrator.py) for scheduled work. Subagents (Agent tool) for within-session parallelism.

**Why defer:** Still experimental. Known issues: duplicate agent spawning when lead can't distinguish idle vs dead teammates (#29271), team state lost on compaction (#23620), memory GC destroys membership records. Community workarounds are fragile (heuristic-based, not event-driven).

**When it would help:** Ad-hoc parallel fan-out within a session where we want persistent coordination (e.g., multi-file code review with 5 specialists + 1 synthesizer). Current subagents are fire-and-forget; Teams enables ongoing dialogue.

**Trigger to revisit:** When the experimental flag is removed and idle/dead distinction is resolved.

## 5. `--bare` Flag for Orchestrator Tasks

**What:** Skips hooks, LSP, plugin sync, and skill directory walks for scripted `-p` calls. Requires `ANTHROPIC_API_KEY` directly.

**Why defer (slightly):** Our orchestrator uses SDK `query()`, not `claude -p`. The `--bare` flag is CLI-only. Relevant only for script-engine tasks that shell out to `claude -p`. Need to audit which orchestrator tasks would benefit.

**Trigger to revisit:** Next orchestrator performance audit, or if startup overhead becomes measurable.

---

## 6. `initialPrompt` Agent Frontmatter (v2.1.83)

**What:** Agents can declare their initial prompt in frontmatter — auto-submits first turn without passing prompt via CLI.

**Our current approach:** Both agents (researcher, session-analyst) receive task-specific prompts at invocation time. Prose preambles in the agent .md files serve as system instructions, not the initial message.

**Why defer:** Both agents need task-specific prompts ("research X", "analyze session Y"). A generic `initialPrompt` would either be ignored (invoker passes a prompt) or produce a suboptimal first turn.

**Trigger to revisit:** When creating a dedicated-purpose agent that always does the same thing (e.g., daily digest, nightly cleanup).

## 7. `CwdChanged` / `FileChanged` Hook Events (v2.1.83)

**What:** New hook events that fire on directory change or file modification. Enables reactive environment management (e.g., direnv).

**Why defer:** No concrete use case. Rules files reload per-turn already. We don't use direnv. Could enable detecting external edits to watched files (GOALS.md changed by another agent), but this is not a current pain point.

**Trigger to revisit:** When needing reactive environment management or external edit detection.

## 8. Agent SDK `task_budget` / `get_context_usage()` (v0.1.51-52) — TRIGGER MET

**What:** Release notes listed `task_budget` (token budget per task, API-side) and `get_context_usage()` (context window breakdown by category).

**Status (2026-04-03):** `get_context_usage()` confirmed present in Python SDK v0.1.55 (`ClaudeSDKClient` method). `task_budget` not found in `dir()` output — may be a `query()` parameter or TS-only. **Action:** upgrade SDK 0.1.44→0.1.55, integrate `get_context_usage()` into dashboard/cockpit context tracking.

**Trigger to revisit:** Triggered — upgrade and integrate.

## Already Adopted (from this sweep)

| Feature | Status | When |
|---------|--------|------|
| `effort` frontmatter | Done — 22 skills updated | 2026-03-23 |
| `StopFailure` hook (billing_error) | Already had | Pre-existing |
| `StopFailure` hook (rate_limit) | Done — backoff signal for orchestrator | 2026-03-23 |
| `rate_limits` in statusline | Already had | Pre-existing |
| `disallowedTools` | Evaluated, no use case — allowlists are stronger | 2026-03-23 |
| `TaskCreated` hook event | Done — async telemetry logging | Pre-existing |
| `PostCompact` hook event | Done — postcompact-verify.sh | Pre-existing |
| Hook `if` conditionals | Done — commit-check + ast-precommit narrowed to `Bash(git commit*)` | 2026-03-29 |
| `--bare` orchestrator fallback | Done — gated on `ORCHESTRATOR_BARE_FALLBACK` env var | 2026-03-29 |
| `maxResultSizeChars` MCP annotation | Available in CC 2.1.91 + SDK 0.1.55 — evaluate for research-mcp | 2026-04-03 |
| `PermissionDenied` hook event | Available in CC 2.1.89 — evaluate for auto-mode recovery | 2026-04-03 |
| `defer` PreToolUse permission | Available in CC 2.1.89 — evaluate for headless orchestrator | 2026-04-03 |
| Hook output >50K to disk | Available in CC 2.1.89 — automatic, no config needed | 2026-04-03 |
| `MCP_CONNECTION_NONBLOCKING` | Available in CC 2.1.89 — adopt for orchestrator `-p` calls | 2026-04-03 |
| Autocompact thrash detection | Available in CC 2.1.89 — automatic, prevents cost spiral | 2026-04-03 |
| Compound command `if` matching | Available in CC 2.1.89 — extends existing hook conditionals | 2026-04-03 |

## Not Applicable

| Feature | Why |
|---------|-----|
| `/remote-control` (VS Code) | Useful for user but not infrastructure |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | No custom models needed |
| Plugin system (marketplace, persistent state) | Using skills, not plugins |

<!-- knowledge-index
generated: 2026-04-03T19:21:48Z
hash: d56285ec7030


end-knowledge-index -->
