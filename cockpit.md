# Cockpit — Multi-Vendor Pilot HUD

The cockpit keeps the operator oriented across **10–20 parallel Ghostty tabs** (Claude Code, Codex CLI, Cursor Agent CLI) without asking "what's happening?"

**Design principle:** steer signals on line 2, telemetry on line 1. Width-capped — no wrap into Vim/status chrome.

**Canonical source:** `agent-infra/scripts/` — installed via symlinks / `~/.cursor/cli-config.json`, not copied monoliths.

## Vendor matrix

| Vendor | In-TUI HUD | Ghostty tab title | Fleet aggregate | Rate limits (5h/7d) |
|--------|------------|-------------------|-----------------|---------------------|
| **Claude Code** | 2-line `statusline.sh` | OSC 2 from statusline | yes (`others:` / `⚑`) | right-aligned line 1 |
| **Cursor CLI** | 2-line `cursor-statusline.sh` | OSC 2 from statusline | yes | right-aligned line 1 |
| **Codex CLI** | **none** (no API) | OSC 2 via hooks + shim flush | yes (tab title only) | ctx% in tab title |

Codex hooks cannot write to a TTY directly — `codex_hook_shim.py` resolves the agent PID + tty, runs the hook, then flushes `/tmp/cockpit-tab-pending-$pid`.

## File map

| File | Role |
|------|------|
| `scripts/cockpit_common.sh` | Shared helpers: aggregate scan, rate limits, Ghostty title, hutter fleet cache, loop badges |
| `scripts/claude-statusline.sh` | Claude 2-line HUD + tab title |
| `scripts/cursor-statusline.sh` | Cursor 2-line HUD + tab title |
| `scripts/codex-tab-title.sh` | Codex Ghostty tab title (hooks only) |
| `scripts/codex_hook_shim.py` | Codex hook wrapper + TTY flush for tab titles |
| `scripts/hutter-fleet-cache.sh` | Async `loop_health.py` → `/tmp/hutter-fleet-cache` |
| `scripts/fleet.sh` | Terminal fleet overview (all vendors) |

**Install paths**

```text
~/.claude/statusline.sh          → agent-infra/scripts/claude-statusline.sh (symlink)
~/.cursor/cli-config.json        → statusLine.command = cursor-statusline.sh
~/.codex/hooks/codex-tab-title.sh → copy or symlink from agent-infra/scripts/
~/.codex/hooks.json              → all hooks wrapped with codex_hook_shim.py
```

## HUD layout (Claude / Cursor)

**Line 1:** `◐ state · model/effort · project · $cost · ctx bar · tool · elapsed ····· 5h% · 7d%`

**Line 2 (steering only):** `🔁 loop · ↺compact · git:N · stale? · fleet:hutter · others:[◆◐] · ⚑ proj1,proj2`

**Removed from line 2** (pilot noise): cache%, ctx +%/m, Δ+lines, session duration, throughput.

**Visual grammar**

| State | Glyph | Tab emoji |
|-------|-------|-----------|
| working | ◐ | 🔵 |
| attention | ◆ | 🟡 |
| error | ▲ | 🔴 |
| done | ● | 🟢 |
| idle | · | ⚪ |

Context bar: green &lt;50%, yellow 50–80%, red &gt;80% (+ `→/compact` inline on line 1).

## Shared state (`/tmp`)

Written by hooks + statuslines; read by aggregate scan and notifications.

| Pattern | Writer | Reader |
|---------|--------|--------|
| `claude-agent-$PPID` | statuslines | `cockpit_scan_aggregate`, `fleet.sh` |
| `cockpit-agent-{vendor}-$pid` | `cockpit_write_agent_state` | aggregate (multi-vendor) |
| `claude-tab-state-$PPID` | `tab-color.sh`, hooks | statusline, `stop-notify.sh` |
| `claude-tab-tool-$PPID` | `tool-tracker.sh` (PreToolUse) | statusline line 1 |
| `claude-tab-loop-$PPID` | `/loop` skill | loop badge |
| `claude-tab-prompt-$PPID` | UserPromptSubmit / working | elapsed / stale? |
| `claude-tab-perm-$PPID` | `permission-auto-allow.sh` | ◆ perm |
| `claude-ctxpct-$session_id` | statusline | compact diagnostics |
| `claude-cockpit-$session_id` | statusline | `stop-notify.sh`, SessionEnd receipt |
| `claude-postcompact-$session_id` | PostCompact hooks | ↺compact badge |
| `cockpit-tab-pending-$pid` | `cockpit_ghostty_title` | `codex_hook_shim` flush |
| `codex-rollout-$pid` | `codex-tab-title.sh` | Codex ctx% cache |
| `hutter-fleet-cache` | `hutter-fleet-cache.sh` | line 2 when `project==hutter` |

Aggregate loop prunes dead PIDs (`kill -0`) — orphaned `claude-agent-*` files caused 9s statusline runs and stale HUD before 2026-06-14 fix.

## PID discipline

| Context | Use |
|---------|-----|
| Claude/Cursor statusline | `$PPID` (statusline child of agent) |
| Codex hooks via shim | `$COCKPIT_AGENT_PID` / `$CLAUDE_PID` from shim — **not** hook `$PPID` |
| `stop-notify.sh` | `COCKPIT_AGENT_PID` when called through shim |

Never `CLAUDE_PID=$PPID` when re-invoking child scripts from inside a shimmed hook.

## Config (`~/.claude/cockpit.conf`)

```ini
notifications=on       # macOS stop notifications (classified events only)
tab_colors=off         # disable Ghostty tab emoji/title updates
# COST_VEL_ALERT=1.0   # 🟠 tab dot threshold ($/min)
```

## Timing / refresh

| Setting | Value | Note |
|---------|-------|------|
| Claude `statusLine.refreshInterval` | 5s | statusline must finish &lt;5s or frame goes stale |
| Cursor `statusLine.updateIntervalMs` | 5000 | |
| Cursor `statusLine.timeoutMs` | 3000 | kill if aggregate scan regresses |

**Gotcha:** `~/.claude/statusline.sh` is a symlink — `COCKPIT_DIR` must use `realpath(BASH_SOURCE[0])`, not `dirname` of the symlink path.

**Gotcha:** never `[[ -w /dev/tty ]]` in subprocesses — can block; attempt OSC write with `2>/dev/null || true`.

## Codex hook events → tab title

`codex-tab-title.sh` fires on `UserPromptSubmit`, `Stop` (via `stop-notify.sh`), and
`SessionStart` (via `session-init.sh` -> idle). It is deliberately excluded from
`PreToolUse`: tab decoration is not allowed to tax the command feedback path.

Context % parsed from Codex rollout JSONL (`~/.codex/sessions/...`), not `/tmp/claude-cockpit-*` (Claude-only).

## Smoke test

```bash
# Claude HUD (via symlink path)
echo '{"context_window":{"used_percentage":19,"context_window_size":1000000},"model":{"display_name":"Opus 4.8"},"cost":{"total_cost_usd":1.5,"total_duration_ms":600000},"session_id":"test","workspace":{"current_dir":"/Users/alien/Projects/genomics"},"rate_limits":{"five_hour":{"used_percentage":89},"seven_day":{"used_percentage":50}}}' \
  | ~/.claude/statusline.sh | sed 's/\x1b\[[0-9;]*m//g'

# Fleet
bash ~/Projects/agent-infra/scripts/fleet.sh

# Codex shim + tab title (prompt-boundary smoke; needs live codex pid/tty for flush)
CODEX_HOOK_EVENT=UserPromptSubmit python3 ~/Projects/agent-infra/scripts/codex_hook_shim.py \
  '~/.codex/hooks/codex-tab-title.sh working' <<< '{"tool_name":"Read"}'
```

## Architecture

```text
 Ghostty tabs
 ┌─────────────┬─────────────┬─────────────┐
 │ Claude TUI  │  Codex TUI  │ Cursor TUI  │
 │ 2-line HUD  │ (no HUD)    │ 2-line HUD  │
 └──────┬──────┴──────┬──────┴──────┬──────┘
        │             │             │
        ▼             ▼             ▼
 claude-statusline  codex-tab-title  cursor-statusline
        │             │             │
        └──────────┬──┴─────────────┘
                   ▼
           cockpit_common.sh
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
 /tmp/claude-agent-*   OSC 2 tab title   cockpit.conf
     │
     ▼
 fleet.sh · stop-notify · dashboard receipts
```

## Other cockpit components

### Idle notification (`~/.claude/hooks/stop-notify.sh`)
Classified macOS notifications: `needs_input`, `tests_failed`, `background_complete`. Deduped per session.

### Session receipt
Statusline writes `/tmp/claude-cockpit-{session_id}` → SessionEnd hook → `~/.claude/session-receipts.jsonl`.

### Dashboard (`scripts/dashboard.py`)
```bash
uv run python3 scripts/dashboard.py          # last 7 days
uv run python3 scripts/dashboard.py --days 30
```

### Agentlogs
Cross-vendor forensics: `uv run agentlogs recent|search|stats`. See `.claude/rules/session-forensics.md`.

## Agent rule

Working on cockpit scripts: read `.claude/rules/cockpit.md` (path-scoped). Cursor: `.cursor/rules/cockpit.mdc`.
