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

## Runlog Forensics

```
uv run python3 scripts/runlog.py stats                  # health check
uv run python3 scripts/runlog.py query runs_touching_path --param path_like=%foo% --format json
uv run python3 scripts/runlog.py query supervision_ratio_by_vendor_week --format json
uv run python3 scripts/runlog.py query tool_usage_by_mcp_server --param vendor=codex --format json
```

## Things Only You Can Do

- **Creative direction.** Agent proposes, you select.
- **Goal-setting.** GOALS.md is human-owned.
- **Risk tolerance.** Agent sizes by Kelly; you set circuit breakers.
- **Cross-domain synthesis.** Agent doesn't connect intel to genomics to meta. That's yours (for now).
- **Deciding when research is done.** Agent searches forever. You call it.

## The Endgame Check

Every few weeks: is meta making sessions better?
- Sessions closer to "optimal run"?
- Supervision rate trending down?
- Corrections for taught things going to zero?
- Agent proposing improvements you hadn't thought of?

If yes, working. If not, `/session-analyst`.
