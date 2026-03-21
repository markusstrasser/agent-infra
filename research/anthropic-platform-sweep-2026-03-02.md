# Anthropic Platform Sweep — 2026-03-02

## Summary

- **Claude Code v2.1.30→v2.1.63** (34 releases in 28 days): HTTP hooks, worktree isolation, Agent Teams preview, auto-memory, managed enterprise settings, 15+ new env vars for controlling effort/model/compaction/subagents
- **Platform API**: Compaction API (beta), Fast mode (beta, 6x pricing), Automatic caching (GA), Data residency (GA), Sonnet 4.6 launch (Feb 17), Sonnet 3.7 + Haiku 3.5 retired
- **Agent SDK v0.1.44**: `effort` param, `ThinkingConfig`, hooks via Python callbacks, 34 `ClaudeAgentOptions` parameters mapped — spike code ready
- **Financial-services plugins**: 5 core + 2 partner plugins, 41 skills, 11 MCP connectors (S&P, FactSet, Daloopa, Morningstar, Moody's, etc). equity-research and financial-analysis are directly relevant to intel
- **17 genuinely new findings** not in existing 7 research docs

## Methodology

- **Phase 1**: 1 agent, 28 tool calls. Sources: claude-code CHANGELOG, claude-agent-sdk-python git log, skills git log, WebFetch of 5 changelog/release-notes URLs, 2 WebSearches. Output: 50-row delta table, 17 new items, 20 URLs to deep-read.
- **Phase 2**: 4 parallel agents, 99 tool calls total. Agent 1 (Claude Code): 12 calls, CHANGELOG + hooks/settings/fast-mode docs. Agent 2 (API): 19 calls, compaction/fast-mode/effort/caching/residency docs + SDK changelog. Agent 3 (SDK spike): 36 calls, SDK source + demos + orchestrator + anthropic-sdk-python. Agent 4 (Financial plugins): 32 calls, all files in financial-services-plugins + knowledge-work-plugins.
- **Total pages fetched**: ~35 (within 40 cap)
- **Token estimate**: ~500K input, ~20K output across all agents

---

## Findings

### Claude Code (Agent 1)

| ID | Tag | Claim | Evidence | Impact | Action |
|----|-----|-------|----------|--------|--------|
| C1 | [NEW] | `CLAUDE_ENV_FILE` env var in SessionStart hooks: write export statements to persist env vars for entire session | hooks docs | 4 | Use in orchestrator SessionStart hook for task-specific env |
| C2 | [NEW] | PreToolUse `updatedInput` field: modify tool input before execution (combine with allow/ask decisions) | hooks docs, PreToolUse section | 4 | Enables input sanitization hooks (e.g., rewrite dangerous rm commands) |
| C3 | [NEW] | `CLAUDE_CODE_EFFORT_LEVEL` env var: low/medium/high controls reasoning effort | settings docs | 4 | Orchestrator can set per-task effort via env var instead of SDK param |
| C4 | [NEW] | `CLAUDE_CODE_SUBAGENT_MODEL` env var: override model used by subagents | settings docs | 3 | Cost control: set subagents to haiku for search tasks |
| C5 | [NEW] | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var: auto-compact threshold (1-100%) | settings docs | 3 | Tune compaction timing per orchestrated task |
| C6 | [NEW] | `CLAUDE_CODE_TASK_LIST_ID` env var: share task list across sessions | settings docs | 3 | Pipeline tasks could share a persistent task list |
| C7 | [NEW] | HTTP hooks: `type: "http"` POSTs JSON to URL. Fails open. Requires `allowedHttpHookUrls` allowlist | hooks docs + v2.1.63 | 4 | Remote hook execution — could wire Telegram bot approvals |
| C8 | [NEW] | SessionStart matcher values: `startup`, `resume`, `clear`, `compact` — compaction fires SessionStart with `compact` matcher | hooks docs | 3 | session-init.sh can differentiate startup vs compaction |
| C9 | [NEW] | `updatedMCPToolOutput` in PostToolUse: replaces MCP tool output with provided value | hooks docs | 3 | Could filter/transform MCP responses (e.g., truncate large outputs) |
| C10 | [NEW] | PermissionRequest `updatedPermissions` field + `interrupt: true` to halt Claude entirely on deny | hooks docs | 3 | Programmatic permission management via hooks |
| C11 | [NEW] | Hook timeout defaults: 600s command, 30s prompt, 60s agent. Tool hooks changed to 10min in v2.1.3 | hooks docs + CHANGELOG | 3 | Our hooks are well within limits |
| C12 | [NEW] | `auto:N%` MCP tool search threshold — tools exceeding N% of context deferred to MCPSearch. Default 10% | CHANGELOG v2.1.9/v2.1.7 | 3 | Relevant if we add many MCP servers |
| C13 | [NEW] | `last_assistant_message` in Stop/SubagentStop hook inputs | v2.1.47 CHANGELOG | 3 | stop-debrief.sh can read final response without transcript parsing |
| C14 | [NEW] | Fast mode pricing: $30/$150 MTok (<200K), $60/$225 (>200K). Billed to extra usage only | fast-mode docs | 3 | Too expensive for routine orchestrator tasks; useful for time-critical research |
| C15 | [NEW] | `CLAUDE_CODE_SHELL_PREFIX` env var: command prefix for logging/auditing all shell commands | settings docs | 3 | Audit trail for orchestrated tasks |
| C16 | [NEW] | `attribution.commit` and `attribution.pr` settings replace deprecated `includeCoAuthoredBy` | settings docs + CHANGELOG | 2 | We already suppress Co-Authored-By via commit hook |
| C17 | [NEW] | Sandbox network/filesystem configs: `allowedDomains`, `denyWrite`, `denyRead` with path prefixes | settings docs | 3 | Enterprise sandboxing — not needed for personal use |
| C18 | [CHANGED] | Hook snapshot security: hooks captured at startup, mid-session changes require review | hooks docs | 3 | Explains why hook edits don't take effect mid-session |
| C19 | [CHANGED] | BashTool skips login shell by default (was `CLAUDE_BASH_NO_LOGIN=true` required) | v2.1.51 CHANGELOG | 2 | One fewer env var to set |

### Platform API (Agent 2)

| ID | Tag | Claim | Evidence | Impact | Action |
|----|-----|-------|----------|--------|--------|
| A1 | [NEW] | Compaction API: `context_management.edits[{type:"compact_20260112"}]`. Trigger default 150K, min 50K. `pause_after_compaction`, custom `instructions`. Stop reason `"compaction"`. | platform docs | 5 | Critical for long agentic loops on raw API |
| A2 | [NEW] | Compaction billing via `usage.iterations[]` array. Top-level usage EXCLUDES compaction. Must sum iterations for true cost. | platform docs | 4 | Current cost tracking would undercount if using compaction |
| A3 | [NEW] | Automatic caching: top-level `cache_control: {"type": "ephemeral"}`. Auto-manages breakpoints. No block-level placement needed. | platform docs | 4 | Simplifies caching for any raw API usage |
| A4 | [NEW] | 1-hour cache TTL: `cache_control: {"type": "ephemeral", "ttl": "1h"}`. 2x base pricing (vs 1.25x for 5min). | platform docs | 3 | Useful for orchestrator side-tasks >5min between turns |
| A5 | [CHANGED] | Effort moved to `output_config.effort` (GA, no beta header). `max` Opus-only. Sonnet 4.6 recommended default: `medium` (not `high`). | platform docs | 4 | Orchestrator should use `medium` for Sonnet tasks |
| A6 | [NEW] | Fast mode: `speed: "fast"`, beta `fast-mode-2026-02-01`. 2.5x OTPS not TTFT. Cache prefixes NOT shared between speed modes. | platform docs | 3 | Cache miss on speed switch makes fallback patterns costly |
| A7 | [NEW] | Data residency: `inference_geo: "us"|"global"`. 1.1x pricing for US-only. Workspace-level defaults. | platform docs | 2 | Not needed for personal use |
| A8 | [CONFIRMED] | SDK v0.78.0: compaction. v0.79.0: fast-mode. v0.83.0: top-level cache_control. v0.84.0: MCP conversion helpers. | anthropic-sdk-python CHANGELOG | 3 | Python SDK is current with all features |

### Agent SDK (Agent 3)

| ID | Tag | Claim | Evidence | Impact | Action |
|----|-----|-------|----------|--------|--------|
| S1 | [NEW] | 34-param `ClaudeAgentOptions` fully mapped. `setting_sources=None` default = NO settings loaded. Critical gotcha. | SDK source | 5 | Must set `setting_sources=["user","project"]` for hooks to fire |
| S2 | [NEW] | Working spike code produced. `query()` → `TaskResult` with cost, tokens, session_id, structured_output. | SDK source + spike | 5 | Ready to integrate into orchestrator |
| S3 | [NEW] | Python hooks via `hooks` param: async functions dispatched in-process. Supported events: PreToolUse, PostToolUse, Stop, etc. | SDK source | 4 | Enables orchestrator-specific hooks without filesystem |
| S4 | [NEW] | `ResultMessage` does NOT expose `permission_denials`. Orchestrator's `done_with_denials` status needs alternative detection. | SDK source | 3 | Watch message stream for denial signals |
| S5 | [NEW] | Bundled CLI (v2.1.59 in v0.1.44). Uses own binary, not system `claude`. Override with `cli_path`. | SDK docs | 3 | Version may lag behind installed claude-code |
| S6 | [NEW] | `max_budget_usd` enforced by CLI. On exceed: `subtype="error_max_budget_usd"`, `is_error=True`. May exceed by one API call. | SDK source | 4 | Reliable cost cap for orchestrator |
| S7 | [NEW] | `output_format: {"type": "json_schema", "schema": {...}}` for structured output via SDK. | SDK source | 3 | Orchestrator could get structured task results |

### Financial Plugins (Agent 4)

| ID | Tag | Claim | Evidence | Impact | Action |
|----|-----|-------|----------|--------|--------|
| F1 | [NEW] | equity-research plugin: 9 skills + 9 commands. Earnings analysis, initiating coverage (782-line, 5-task pipeline), thesis tracker, idea generation (5 screening frameworks), earnings preview, morning notes. | financial-services-plugins repo | 5 | Install or adapt for intel |
| F2 | [NEW] | financial-analysis core: comps-analysis (628 lines), DCF model, competitive analysis, model auditor. 11 MCP connectors (S&P, FactSet, Daloopa, Morningstar, Moody's, MT Newswires, Aiera, LSEG, PitchBook, Chronograph, Egnyte). | financial-services-plugins repo | 5 | MCP connectors are the biggest win if we get subscriptions |
| F3 | [NEW] | partner/spglobal: tear-sheet skill (4 audience types) + earnings preview via S&P CIQ MCP. Intermediate-file protocol for data integrity. | financial-services-plugins repo | 4 | Entity profiling pipeline if S&P CIQ access obtained |
| F4 | [NEW] | All plugins are pure markdown, zero build steps, Apache 2.0. Install via `claude plugin install` or copy SKILL.md files. | financial-services-plugins repo | 4 | Low friction adoption |
| F5 | [NEW] | knowledge-work/data plugin: SQL queries, statistical analysis, visualization. Connectors: Snowflake, Databricks, BigQuery. | knowledge-work-plugins repo | 2 | Not needed — we have DuckDB pipeline |
| F6 | [NEW] | PE plugin unit-economics skill: ARR bridge, cohort analysis, LTV/CAC, revenue quality scoring. | financial-services-plugins repo | 3 | Useful for SaaS targets in intel coverage |

---

## Action Items

### Adopt Now (this week, ≤5 items)

1. **Commit SDK spike as `scripts/orchestrator_sdk_spike.py`**
   - File: `meta/scripts/orchestrator_sdk_spike.py`
   - Acceptance test: `uv run python3 scripts/orchestrator_sdk_spike.py` completes without import errors, runs test query
   - LOC: ~150 (spike already written)
   - Blocker: install `claude-agent-sdk` in meta's deps

2. **Set `CLAUDE_CODE_EFFORT_LEVEL` in orchestrator env per task type**
   - File: `meta/scripts/orchestrator.py` (add effort to task config, pass as env var)
   - Acceptance test: entity-refresh tasks run with `low`, research tasks with `high`
   - LOC: ~10
   - Also: `CLAUDE_CODE_SUBAGENT_MODEL=haiku` for search-heavy tasks

3. **Copy equity-research screening frameworks to intel skills**
   - Files: Copy `idea-generation/SKILL.md` and `earnings-preview/SKILL.md` to `intel/.claude/skills/`
   - Acceptance test: Skills appear in `/skills` list and produce structured output
   - LOC: 0 (copy + adapt existing files)

4. **Use `last_assistant_message` in stop-debrief.sh**
   - File: `~/Projects/skills/hooks/stop-debrief.sh`
   - Acceptance test: Debrief hook reads final response from hook input instead of transcript parsing
   - LOC: ~5 (read from `$HOOK_INPUT` JSON instead of transcript file)

5. **Update hook event count from "17" to "22" in CLAUDE.md**
   - File: `meta/CLAUDE.md` (reference data section)
   - Acceptance test: Grep shows "22 events" not "17 events"
   - LOC: 1

### Adopt Soon (this month)

- **Integrate financial-analysis MCP connectors**: Evaluate which data providers (S&P, FactSet, Morningstar) are worth subscribing to. Copy `.mcp.json` connector configs.
- **SDK migration (orchestrator Phase 5)**: Replace `run_claude_task()` subprocess with `run_claude_task_sdk()`. Handle `permission_denials` detection gap.
- **HTTP hooks for Telegram approvals**: Wire orchestrator `requires_approval` gate to HTTP hook → Telegram bot (C7).
- **Compaction API for raw API usage**: If building any direct API tool-use loops, use server-side compaction (A1) with `iterations[]` billing awareness (A2).
- **Automatic caching with 1h TTL**: For orchestrator tasks with >5min between turns (A4).
- **Adapt equity-research earnings-analysis citation enforcement**: Its verification checklist is stricter than intel's current source-check hook.
- **Install comps-analysis skill**: The 628-line comparable company analysis is more structured than anything in intel.
- **Evaluate partner/spglobal tear-sheet**: If S&P CIQ access is obtainable, this is a complete entity profiling pipeline.

### Watch

- **Agent Teams** (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): Multi-agent collaboration. Not stable enough for orchestrator yet.
- **Fast mode API** (6x pricing, beta): Too expensive for routine use. Watch for price drops.
- **`claude remote-control`**: Local environment serving for external builds. No current use case.
- **Managed settings via macOS plist**: Enterprise feature. Not relevant for personal use.
- **MCP conversion helpers in SDK v0.84.0**: Could simplify research-mcp integration. Needs investigation.

### Contradicts

- **SDK `setting_sources` default = None**: Our tooling landscape memo (§1) described SDK as drop-in replacement for `claude -p`. It's NOT — you must explicitly opt into settings loading. This is the #1 gotcha.
- **"17 hook events"**: We documented 17 in CLAUDE.md but the actual count is 22 (added TeammateIdle, TaskCompleted, WorktreeCreate, WorktreeRemove, ConfigChange). Our reference data was already partially updated but the count was stale.
- **Effort param location**: We had it as top-level. It's actually `output_config.effort` in the API. The SDK abstracts this.

---

## SDK Spike

See `scripts/orchestrator_sdk_spike.py` (committed separately).

Key design decisions in the spike:
- `anyio.run()` bridges async SDK into sync orchestrator
- `setting_sources=["user", "project"]` to preserve hook/CLAUDE.md behavior
- `system_prompt={"type": "preset", "preset": "claude_code"}` for Claude Code default behavior
- `TaskResult` dataclass mirrors current orchestrator's JSON parsing output
- `permission_denials` detection gap documented (not in `ResultMessage`)

---

## Sources

### Git repos read
- `~/Projects/best/claude-code/` (CHANGELOG.md, git log --since=2026-02-01)
- `~/Projects/best/claude-agent-sdk-python/` (full source, CHANGELOG.md, types, examples)
- `~/Projects/best/claude-agent-sdk-typescript/` (changelog comparison)
- `~/Projects/best/claude-agent-sdk-demos/` (usage patterns)
- `~/Projects/best/anthropic-sdk-python/` (CHANGELOG.md, compaction types)
- `~/Projects/best/financial-services-plugins/` (all files)
- `~/Projects/best/knowledge-work-plugins/` (all files)
- `~/Projects/best/skills/` (git log)

### Web pages fetched
- https://code.claude.com/docs/en/changelog
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/fast-mode
- https://code.claude.com/docs/en/settings
- https://platform.claude.com/docs/en/docs/release-notes
- https://platform.claude.com/docs/en/build-with-claude/compaction
- https://platform.claude.com/docs/en/build-with-claude/fast-mode
- https://platform.claude.com/docs/en/build-with-claude/effort
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- https://platform.claude.com/docs/en/build-with-claude/data-residency
- https://docs.anthropic.com/en/api/changelog
- https://www.anthropic.com/news/claude-sonnet-4-6

<!-- knowledge-index
generated: 2026-03-21T23:52:34Z
hash: 5ce647d74c42

table_claims: 40

end-knowledge-index -->
