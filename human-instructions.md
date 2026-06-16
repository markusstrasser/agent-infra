# Human Instructions

> Decision guide for the operator. Organized by situation, not topic.
> The agent handles execution. This file is about when YOU need to act.

## Starting a Session

1. Context% yellow from resume? `/compact` before anything complex.
2. Check cost after 10 minutes. If spending with no meaningful delta (no commits, no evidence gathered, no tests passing), interrupt.

## Choosing the Right Tool

**Research/analysis** (use the smart model — Opus):
- `/thesis-check TICKER` — adversarial stress-test (30-40 tool calls, expensive, max 2 parallel)
- `/model-review` — cross-model adversarial (Gemini + GPT)
- `/researcher topic` — effort-adaptive, anti-fabrication
- `/session-analyst project N` — behavioral anti-patterns (dispatches to Gemini)

**Mechanical work** (cheaper model fine):
- `/batch migrate X from Y to Z` — parallel agents in worktrees
- `/simplify` — 3 parallel review agents post-feature

**Monitoring**:
- `/context` — loaded skills, rules, context budget
- `/insights` — LLM-generated session analytics
- `/stats` — usage visualization

## Mid-Session: When to Intervene

| Signal | Action |
|--------|--------|
| Same failure reappears after you redirected once | Take over or narrow the task. Repeated steering = supervision debt. |
| Agent reads the same file 4+ times or runs similar searches | Interrupt and redirect. Spinning detector catches tool loops, not semantic repetition. |
| Long chain of searches that don't converge | Agent theater. Interrupt. |
| You ask for a small fix, agent proposes a refactor | Say no. |
| Agent builds something without pushing back — and it's wrong | Sycophancy failure. Note for session-analyst. |
| "Out of extra usage" message | Agent will spin retrying. No hook catches this. Interrupt manually. |

## Parallel Agents

- Independent tasks with no shared state: parallelize.
- DuckDB write lock, git checkout, same file: don't parallelize.
- `/batch` handles worktree isolation. Prefer it for code changes.
- Bash parallel calls are all-or-nothing. One bad flag kills all siblings.

## Research Sweeps

- Not calendar-driven. Do when: new model ships, you're stuck, steep improvement curve, or >2 weeks since last.
- Exa for recency (date filtering). S2 for citation-weighted discovery.
- Results citing Claude 3.5 Sonnet are outdated.
- At some point, building beats reading. Switch on diminishing returns.

## Post-Session

- Run `/session-analyst` after major work sessions or when something felt wrong. Not every session.
- If a session had reverted work, 5-hour runs that should have been 1-hour, or repeated corrections — that's signal.
- Friction that recurs 2+ times becomes a hook or rule.

## Codex / OpenAI Runs

- `just dashboard` includes Codex/OpenAI panel.
- Codex CLI gives session facts: model, reasoning effort, tokens, tool-call count, project, task label.
- Import stored Responses API objects: `just agent-receipts import-openai path/to/responses.jsonl`.

## Session Forensics

```
uv run agentlogs stats                  # health check
uv run agentlogs query runs_touching_path --param path_like=%foo% --format json
uv run agentlogs query supervision_ratio_by_vendor_week --format json
uv run agentlogs query tool_usage_by_mcp_server --param vendor=codex --format json
```

## Things Only You Can Do

- **Creative direction.** Agent proposes, you select.
- **Goal-setting.** GOALS.md is human-owned.
- **Risk tolerance.** Agent sizes by Kelly; you set circuit breakers.
- **Cross-domain synthesis.** Agent doesn't connect intel to genomics to agent-infra. That's yours (for now).
- **Deciding when research is done.** Agent searches forever. You call it.

## CLI Power-User Tips

**Session management:**
- `/branch` — fork current session (keeps context, diverges from here)
- `claude --resume <session-id> --fork-session` — fork from CLI
- `/btw` — side query while agent works (doesn't interrupt main task)
- `/voice` — voice input; hold spacebar in CLI, or use dictation on iOS/Desktop

**Parallel work:**
- `claude -w` — start session directly in a new git worktree
- `/batch` — fan out to dozens/hundreds of worktree agents for large migrations
- `--add-dir path/to/other/repo` — give Claude access to another repo (also `/add-dir` mid-session)

**Performance:**
- `--bare` — skip CLAUDE.md, settings, MCPs on startup (up to 10x faster). For non-interactive `claude -p`, prefer **subscription OAuth** (strip inherited `ANTHROPIC_API_KEY`) or `llmx chat --subscription`; vendor `--bare` docs assume API-key billing — use only when explicitly requested.

**Remote:**
- `/schedule` — schedule Claude to run remotely on a cron (up to a week). Use for babysit loops, code review, rebase.
- Dispatch (claude.com) — remote control for Claude Desktop from phone. Uses your MCPs, browser, files.

## The Endgame Check

Every few weeks: is agent-infra making sessions better?
- Sessions closer to "optimal run"?
- Supervision rate trending down?
- Corrections for taught things going to zero?
- Agent proposing improvements you hadn't thought of?

If yes, working. If not, `/session-analyst`.
