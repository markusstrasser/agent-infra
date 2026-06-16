# Live /goal probe report (2026-06-15)

## Command

```bash
cd /tmp/goal-probe-live
env -u ANTHROPIC_API_KEY claude -p --permission-mode bypassPermissions \
  "/goal create a file named probe-ok.txt ... PROBE_OK ..."
```

First attempt with `--permission-mode dontAsk` failed (Write/Bash denied). Second attempt succeeded in ~21s.

## Transcript

- Path: `~/.claude/projects/-private-tmp-goal-probe-live/5eabb19d-aee7-4526-8972-6b346703d687.jsonl`
- Fixture copy: `tests/fixtures/goal-transcript-achieved-live.jsonl`
- Claude Code: **2.1.177**

## Verified marker schema

### Goal set (active)

```json
{
  "type": "attachment",
  "attachment": {
    "type": "goal_status",
    "met": false,
    "sentinel": true,
    "condition": "create a file named probe-ok.txt ..."
  },
  "timestamp": "2026-06-15T10:49:50.963Z"
}
```

Also: `<local-command-stdout>Goal set: ...</local-command-stdout>` user message.

### Goal achieved (authoritative)

```json
{
  "type": "attachment",
  "attachment": {
    "type": "goal_status",
    "met": true,
    "condition": "...",
    "reason": "The transcript shows the file was created ...",
    "iterations": 1,
    "durationMs": 15781,
    "tokens": 358
  },
  "timestamp": "2026-06-15T10:50:06.744Z"
}
```

### Not present in live probe

- `activeGoal` metadata block
- `"Goal achieved"` exact string (assistant said **"Goal met."** instead)
- `tengu_goal_achieved` telemetry string in transcript

## Parser result

```python
goal_state_from_transcript(live_lines)
# → status=achieved, source=claude_transcript,
#   evidence_ts=2026-06-15T10:50:06.744Z,
#   raw_ref=attachment.goal_status.met=true
```

## Codex

Not probed this session — Claude marker now fixture-backed. Codex path remains `thread/goal/get` with `status: complete`.
