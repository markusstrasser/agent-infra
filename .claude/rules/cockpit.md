---
paths:
  - "scripts/cockpit*.sh"
  - "scripts/*statusline*.sh"
  - "scripts/codex-tab-title.sh"
  - "scripts/codex_hook_shim.py"
  - "scripts/hutter-fleet-cache.sh"
  - "scripts/fleet.sh"
  - "cockpit.md"
---

# Cockpit (pilot HUD)

Full reference: `cockpit.md`. This rule is the edit-time cheat sheet.

## What each vendor gets

- **Claude:** `scripts/claude-statusline.sh` → 2-line TUI HUD + Ghostty tab. Installed: `~/.claude/statusline.sh` symlink.
- **Cursor:** `scripts/cursor-statusline.sh` → same grammar, `◇` vendor marker. Config: `~/.cursor/cli-config.json` `statusLine.command` (absolute path).
- **Codex:** **no statusline API** — only `codex-tab-title.sh` + `codex_hook_shim.py` TTY flush. Never read `/tmp/claude-cockpit-*` in Codex hooks; use rollout JSONL.

## Shared module

`scripts/cockpit_common.sh` — aggregate scan, rate limits, `cockpit_ghostty_title`, hutter fleet, loop badges. Source with **realpath** of script dir:

```bash
COCKPIT_DIR="$(python3 -c "import os; print(os.path.dirname(os.path.realpath(os.path.expanduser('${BASH_SOURCE[0]}'))))")"
source "$COCKPIT_DIR/cockpit_common.sh"
```

Symlinked `~/.claude/statusline.sh` breaks naive `dirname BASH_SOURCE[0]`.

## Line 2 is steering only

Include: loop, ↺compact, git dirty, stale?, hutter fleet, `others:[◆◐]`, `⚑` attention projects.  
Exclude: cache%, ctx growth rate, Δ lines, throughput, session duration.

## PID / TTY gotchas

- Statuslines: `$PPID` for `/tmp/claude-tab-*` and `claude-agent-$PPID`.
- Codex shim sets `COCKPIT_AGENT_PID` + `COCKPIT_TTY` — hooks must use `cockpit_agent_pid()`, not raw `$PPID`.
- `cockpit_ghostty_title` writes `/tmp/cockpit-tab-pending-$pid`; shim flushes OSC 2 post-hook.
- No `[[ -w /dev/tty ]]` — fails or blocks in subprocesses.

## Performance

Claude `refreshInterval: 5` — aggregate loop must prune dead `claude-agent-*` (`kill -0` + rm). Regressions → stale HUD frame (ctxpct updates, display doesn't).

## After editing

```bash
echo '<json>' | ~/.claude/statusline.sh | sed 's/\x1b\[[0-9;]*m//g'   # must exit 0, <3s
bash scripts/fleet.sh
```

Sync `~/.codex/hooks/codex-tab-title.sh` from `scripts/codex-tab-title.sh` when changing Codex path.
