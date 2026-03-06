# Human Instructions

> Things that can't be hooks, skills, or rules. Tricks, timing, judgment calls.
> This file is for YOU, not the agent. Read it when you sit down to work.

## Session Start

- **Glance at the status line.** If context% is yellow from a resumed session, `/compact` before doing anything complex.
- **Check cost after 10 minutes.** If >$1.50 and the agent is spinning, interrupt. The spinning-detector warns at 4 repeats but can't catch semantic loops (doing different-but-useless things).
- **Don't paste continuation summaries.** The agent reads `checkpoint.md` + git state. If it asks for context anyway, that's a bug — note it for session-analyst.

## When to Use What

| You want to... | Do this |
|----------------|---------|
| Refactor N files the same way | `/batch migrate X from Y to Z` — spawns parallel agents in worktrees |
| Clean up after implementing a feature | `/simplify` — 3 parallel review agents (reuse, quality, efficiency) |
| Stress-test an investment thesis | `/thesis-check TICKER` — 30-40 tool calls, expensive, max 2 parallel |
| Challenge an architecture decision | `/model-review` — cross-model adversarial (Gemini + GPT) |
| Deep research with source rigor | `/researcher topic` — effort-adaptive, anti-fabrication |
| Find behavioral anti-patterns | `/session-analyst project N` — dispatches to Gemini, appends to improvement-log |
| Audit wasted supervision | `/supervision-audit` — finds corrections/boilerplate that should be automated |
| Check what's available | `/context` — shows loaded skills, rules, context budget |
| See session analytics | `/insights` — LLM-generated analysis of recent sessions |
| Quick stats | `/stats` — usage visualization, streaks, model preferences |

## Model Routing (Your Preference)

- **Default to the smart model** (opus) for anything analytical — thesis checks, investigations, entity analysis, architecture decisions.
- **Cheaper model** (sonnet/haiku) is fine for: search, lookup, file discovery, mechanical refactoring, formatting.
- **The `model` field on skills** only works cleanly with `context: fork`. Inline skills inherit the session model. Don't pin inline skills to haiku — it drops the session model mid-conversation.
- **For subagents**, model is set in frontmatter: sql-reviewer→haiku (pattern matching), everything else→sonnet (good enough for most delegated work).

## Parallel Agents

- **Spawn parallel agents for independent tasks.** If they don't share state, parallelize.
- **Don't parallelize when they share mutable state.** DuckDB write lock, git checkout, same file — these collide.
- **Bash parallel calls are all-or-nothing.** One bad flag kills all siblings with "Sibling tool call errored." Don't parallelize when guessing flags.
- **`/batch` handles worktree isolation for you.** Each unit gets its own copy of the repo. Prefer this over manual parallel spawning for code changes.

## Research Sweeps

- **Not calendar-driven.** Do a sweep when: new model ships, you're stuck on a problem, steep improvement curve, or it's been >2 weeks since the last one.
- **Use Exa for recency** (date filtering). Use S2 for citation-weighted discovery (no date filtering).
- **Results citing Claude 3.5 Sonnet are outdated.** Constrain to recent dates for fast-moving fields.
- **Action produces information.** At some point, building and using beats reading papers. Switch when you notice diminishing returns from reading.

## Cost Management

- **Status line turns red at $2.00** (configurable in `~/.claude/cockpit.conf`).
- **Thesis-check is expensive** — 30-40 tool calls. Don't stack more than 2 in parallel.
- **`/batch` is expensive** — spawns N agents × M turns each. Use for real refactoring, not experiments.
- **Subagent delegation is cheap** when the subagent is on haiku/sonnet with limited turns.
- **If the agent hits "out of extra usage"**, it will spin trying to retry. No hook can catch this (system message, not tool output). Interrupt manually.

## Intervene Now

- **Red state means real failure, not just urgency.** `▲` is for repeated command/test failure. Interrupt and inspect before the agent burns more time.
- **Yellow state is your "look now" signal.** `◆` means input needed, compaction pressure, or cost threshold crossed.
- **If cost crosses the threshold without meaningful delta**, stop. "Meaningful delta" = tests passed, files changed for a reason, or evidence gathered that changes the plan.
- **If the same failure reappears after you already redirected once**, take over or narrow the task. Repeated steering on the same point is supervision debt.

## Codex / OpenAI Runs

- **Codex sessions now count as cockpit data.** `just dashboard` includes a Codex/OpenAI panel; it is no longer Claude-only.
- **Codex CLI gives you session facts, not API metadata.** You'll get model, reasoning effort, cached/reasoning tokens, tool-call count, project, and a rough task label from the transcript.
- **Stored Responses API objects can be imported** with `just agent-receipts import-openai path/to/responses.jsonl`.
- **If you care about project/task tags on raw API runs, set `metadata` when you create the response.** Otherwise the dashboard can only show what the raw object already contains.

## Post-Session

- **Retro on bad sessions.** If a session had reverted work, 5-hour runs that should have been 1-hour, or repeated corrections — that's signal. Run `/session-analyst` on it.
- **"Gotchas to eradicate"** — after a frustrating session, note the specific friction. If it recurs 2+ times, it becomes a hook or rule.
- **Don't run session-analyst on every session.** Run it after major work sessions or when something felt wrong. Weekly during active development.

## Things Only You Can Do

- **Creative direction.** The agent proposes, you steer. "Generate ideas to improve X" is a valid prompt — but the selection is yours.
- **Goal-setting.** GOALS.md is human-owned. The agent can propose changes but never modify.
- **Risk tolerance.** The agent sizes positions by Kelly but you set the circuit breakers and the "am I comfortable" threshold.
- **Connecting old projects.** The agent doesn't spontaneously connect intel findings to selve genomics to meta tooling. That cross-domain synthesis is your job (for now).
- **Deciding when research is done.** The agent will keep searching forever. You decide when there's enough evidence to act.

## Snippets That Stayed Manual

These were evaluated against skills/hooks and intentionally kept as human-triggered:

- **"Check ~/Projects/meta"** — judgment call about when meta improvements apply to current work.
- **"Generate ideas to improve X"** — direction-setting prompt. The value is in your selection, not the generation.
- **"Sanity check controversial takes"** — steering. You decide what's controversial.
- **"Parallel refactor agents"** — per-situation decision about what to parallelize (now partially replaced by `/batch`).

## Anti-Patterns to Watch For

- **Sycophantic compliance.** If you ask for something and the agent builds it without pushing back — and it turns out to be wrong — that's a sycophancy failure. The agent has instructions to push back but they're only ~50% reliable. Watch for it yourself.
- **Agent theater.** Performative work that looks productive but produces nothing. Long chains of searches that don't converge. Files written and immediately deleted. If it feels like busywork, interrupt.
- **Over-scoping.** You ask for a small fix, the agent proposes a refactor. Say no. The instruction says "don't over-engineer" but it doesn't always stick.
- **Token waste spirals.** Agent reads the same file 4 times, or runs 9 find commands with minor variations. The spinning-detector catches same-tool loops but not semantic repetition. Interrupt and redirect.

## The Endgame Check

From GOALS.md: "wake up to 30 great ideas, say yes/no, go back to sleep."

Every few weeks, ask: is meta making sessions better? Check:
- Are sessions getting closer to "optimal run"?
- Is the supervision rate trending down?
- Are corrections for things already taught once going to zero?
- Is the agent proposing improvements you hadn't thought of?

If the answers are yes, meta is working. If not, run `/session-analyst` and find out why.
