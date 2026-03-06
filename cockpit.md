# Cockpit — Agent Ops Interface

The "cockpit" is the set of tools that keep the human operator informed, oriented, and in control across interactive agent runs. Claude Code is the deepest integration today, but the dashboard and receipt model now also cover Codex CLI sessions and stored OpenAI Responses API runs.

Design principle: the human should never have to ask "what's happening?" — the answer should already be visible.

## Deployed Components

### Status Line (`~/.claude/statusline.sh`)
Persistent bar inside Claude Code TUI. Updates after every assistant turn.

**Shows:** state glyph · model/branch · $cost ($/min) · context bar/tokens · tool · elapsed

**Line 2:** throughput · cache% · context growth · ETA to compact · lines · other agents

**Visual grammar:** 4 states, 4 glyphs, restrained palette
- `working` → `◐` (dim/default)
- `attention` → `◆` (yellow)
- `error` → `▲` (red)
- `done` → `●` (green)

**Thresholds:**
- Context bar: green <50%, yellow 50-80%, red >80%
- Cost: turns red at threshold (default $2.00, set in cockpit.conf)
- Context >80%: shows `→ /compact` inline guidance
- Error state is reserved for actual failure signals; high context alone is attention, not error

**Also:** updates Ghostty tab title via OSC 2 (`glyph · project · short status · $cost · ctx%`).

### Idle Notification (`~/.claude/hooks/stop-notify.sh`)
Stop hook. Sends macOS notifications via `osascript`, but only for classified state transitions.

**Events:**
- `needs_input`
- `tests_failed`
- `background_complete`
- `cost_threshold_crossed`

Notification dedupe is session-local. `working` clears the prior event marker; repeated identical stop events without new work do not re-fire.

**Toggle:** `~/.claude/cockpit.conf` → `notifications=on|off`

### Spinning Detector (`~/.claude/hooks/spinning-detector.sh`)
PostToolUse hook. Tracks consecutive same-tool calls via `/tmp/claude-spinning-$PPID`.

- **4 repeats:** advisory note ("agent may be repeating itself")
- **8 repeats:** stronger warning ("likely stuck in a loop")

### Session Receipt (`sessionend-log.sh`)
SessionEnd hook (enhanced). Writes two logs:
1. `~/.claude/session-log.jsonl` — backwards-compatible event log
2. `~/.claude/session-receipts.jsonl` — enriched flight receipt with cost, model, branch, context%, lines

Cost data flows: status line persists to `/tmp/claude-cockpit-{session_id}` → SessionEnd reads it.

### Agent Receipts (`meta/scripts/agent_receipts.py`)
Normalizes non-Claude OpenAI runs into the same dashboard vocabulary.

**Sources:**
- Codex CLI session JSONL under `~/.codex/sessions/`
- Stored OpenAI Responses API objects imported manually

**Commands:**
```bash
uv run python3 scripts/agent_receipts.py sync-codex --days 7
uv run python3 scripts/agent_receipts.py import-openai path/to/responses.jsonl
```

**Normalized fields:** `response_id` (when present), `status` / `background_state`, `reasoning_effort`, `reasoning_output_tokens`, `cached_input_tokens`, `tool_call_count`, `project`, `task_label`, `task_tags`.

### Dashboard (`meta/scripts/dashboard.py`)
Reads Claude receipts plus Codex/OpenAI receipts. Shows weekly/all-time stats and a provider-specific panel for OpenAI/Codex runs.

```
uv run python3 scripts/dashboard.py          # last 7 days
uv run python3 scripts/dashboard.py --days 30
```

### Config (`~/.claude/cockpit.conf`)
```
notifications=on       # macOS notifications on idle
cost_warning=2.00      # cost threshold for red visual
```

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         Claude Code TUI          │
                    ├─────────────────────────────────┤
 status line ──────│ Opus main · $0.42 · ▓▓▓▓░░ 67%  │
                    └──────────┬──────────────────────┘
                               │
           ┌───────────────────┼───────────────────────┐
           │                   │                        │
    ┌──────▼──────┐   ┌───────▼───────┐   ┌───────────▼──────────┐
    │  OSC 2 tab  │   │  /tmp state   │   │  cockpit.conf        │
    │  title      │   │  file         │   │  (toggles/thresholds)│
    └─────────────┘   └───────┬───────┘   └──────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  SessionEnd hook  │
                    │  → receipt JSONL  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ agent_receipts.py │
                    │ Codex/OpenAI norm │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  dashboard.py     │
                    │  Agent ops view   │
                    └───────────────────┘
```

## Ideas Backlog

### Ship Next

- **Project-specific SessionStart hooks** — per-project reminders on session start. Intel: "check market hours". Genomics: "check Modal credits". Could use a `~/.claude/project-reminders/` directory with `project-name.txt` files.

- **Session templates** — pre-configured `.claude/session-start.md` files per project that set context for common task types (debugging, research, feature work).

- **Agent-type stop hook verifier** — use a `type: "agent"` Stop hook (has Read/Grep/Glob access) to verify output quality before session ends. E.g., check that all new files have tests, or that MEMORY.md wasn't corrupted.

- **Multi-session sidebar** — cmux (Ghostty-based terminal wrapper) provides vertical tabs with per-pane context. Worth evaluating if running parallel sessions regularly.

- **Responses API import automation** — hook or helper that archives raw response objects automatically so OpenAI API runs appear without manual import.

### Maybe Later

- **UserPromptSubmit preprocessing** — hook that analyzes user input before Claude sees it. Could detect pasted AI output and add a warning tag. Complex, unclear value.

- **PermissionRequest class-based hooks** — intercept permission dialogs by category (destructive, network, file write) instead of tool-by-tool. Cleaner than current Bash text matching but requires understanding the permission model deeply.

- **Ghostty status bar widget** — blocked on Ghostty feature request #2421. When available, would allow persistent info display in terminal chrome separate from Claude Code's TUI.

### Won't Do For Now

- **OpenTelemetry export** — full metrics pipeline to Prometheus/Grafana. Overkill for a single-user terminal cockpit.
- **Always-notify stop hooks** — generic "assistant stopped" notifications. Low signal compared to state-classified transitions.
