# Claude Code mods (function-hook plugins)

In-process TypeScript plugins for Claude Code 2.1.289+ (early-access API: it changes
between releases; `claude plugin validate <dir>` and `claude plugin test <dir>` are the
checks). Enforcement stays in the shell hooks, which Codex shares through
`codex_hook_shim.py`; mods are for what shell hooks cannot do: UI, rewrites, in-session
timers and forks.

| Mod | What it does | Entry points |
|---|---|---|
| `control-plane` | Band above the prompt with the control-plane queue (questions, RSI close, quarantine, drift), read from `pulse funnel --json`, `questions_view --json` and the inbox. The questions pane writes HUMAN.md answers through `scripts/human_md_answer.py` | `/questions`, `/control-plane` |
| `tick` | Local wakeups: `$.clock` + `$.prompt.submit`. Uses none of the account routine quota and dies with the process | `/tick`, tool `mcp__tick__wake` |
| `ablation` | Per-session harness A/B: drops the instruction files named in `~/.claude/harness-ablation.json` in a hashed treatment arm and records the arm in `~/.claude/harness-ablation/<session>.json` | `/ablation` |
| `drift-fork` | Every 10 main-thread turns, a `$.model.fork` side question (is the session drifting?), answered from the prompt cache. Toast on drift; tokens per check in `~/.claude/drift-fork/<session>.json` | `/drift` |
| `fleet` | Pane listing subagents, background tasks, `bgrun` jobs and lanes that are not DONE | `/fleet` |

Load for one session: `claude --plugin-dir ~/Projects/agent-infra/mods/<mod>` (repeatable).
Load everywhere: list the folders in `CLAUDE_CODE_PLUGIN_DIRS`.
