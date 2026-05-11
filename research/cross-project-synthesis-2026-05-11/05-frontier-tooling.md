# Frontier Agent Tooling Sweep — 2026-02 to 2026-05

Research conducted 2026-05-11. Quota note: Perplexity and Exa APIs returned auth/quota errors; this sweep is sourced primarily from Brave Search results pointing at vendor changelogs, GitHub releases, and dated independent writeups. Vendor primary sources were preferred where available.

## "Hair mass" decoded

The user almost certainly meant **harness** — the term-of-art for the orchestration layer around a coding LLM (the part that isn't the model: prompts, hooks, tools, sandbox, memory). It's all over 2026 writing — e.g., "the agent harness matters less than the model quality" ([Nimbalyst comparison](https://nimbalyst.com/blog/claude-code-vs-codex-vs-opencode-definitive-comparison/)), "+16pt harness effect most comparisons ignore" ([Jock comparison](https://thoughts.jock.pl/p/ai-coding-harness-agents-2026)). Lee et al. (arXiv:2603.28052) calls the field "harness engineering."

Less likely but possible: **Hermes CLI** — a coding-agent CLI now in the wild (one of 16 detected on PATH by [open-design](https://github.com/nexu-io/open-design)). It runs alongside Claude Code, Codex, Cursor, Gemini, OpenCode, Qwen, Kimi, Kiro, Kilo, DeepSeek TUI, Pi, etc. No clear "Hermes" vendor identified in this sweep; if the user said "Hermes" specifically, ask which one.

## TL;DR — Adopt This Week

- **Claude Code task budgets** (beta header `task-budgets-2026-03-13`, Opus 4.7): give the model a running token countdown for the whole agentic loop. Directly addresses our "stop searching by turn 18" instruction-only enforcement. ([API docs](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-7))
- **Claude `/less-permission-prompts` skill**: scans transcripts and proposes a prioritized allowlist for `.claude/settings.json`. Replaces our manual allow-list curation. ([changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md))
- **PostToolUse `updatedToolOutput` for all tools** (was MCP-only): we can now rewrite Bash/Read/Edit output in-flight from a hook — directly enables a stronger source-tagging or claim-suppression pass. ([changelog](https://releasebot.io/updates/anthropic/claude-code))
- **Codex `/goal` mode** (CLI 0.128.0, 2026-04-30): persistent objectives that survive interrupts; "ralph loop" built in, with pause/resume/clear TUI controls. Best fit for our `/loop` long-running tasks and queued orchestrator work. ([Simon Willison link post](https://simonwillison.net/2026/Apr/30/codex-goals/))
- **Claude managed-agent memory (public beta)** under `managed-agents-2026-04-01` header — first-party cross-session memory. Worth piloting against `~/.claude/agent-memory/` to evaluate whether our hand-rolled memory system can be retired for at least the researcher subagent. ([Anthropic release notes](https://platform.claude.com/docs/en/release-notes/overview))

## Claude Code — Recent Features (Feb–May 2026)

Changelog cadence has been ~30 releases in 5 weeks (v2.1.83 → v2.1.128). Verified items from the official [CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) and [release notes](https://platform.claude.com/docs/en/release-notes/overview):

- **Opus 4.7** (2026-04-16). Same $5/$25 pricing as 4.6. New `xhigh` effort level (between high and max). 3× higher vision resolution. Improved instruction following. Default model on Max; Pro stayed on Sonnet 4.6 until 2026-04-23. The tokenizer changed — same prose now bills 1.0–1.35× ([ClaudeLog](https://claudelog.com/claude-news/)).
- **Task budgets** (beta `task-budgets-2026-03-13`): model sees a token countdown for the whole loop and prioritizes finishing gracefully. The most architecturally interesting feature in this window for our turn-budget problem.
- **Temperature/top_p locked to defaults** on Opus 4.7 — non-default values return 400. Migration: drop these params.
- **Advisor tool** (`advisor-tool-2026-03-01`): pair a fast executor model with a higher-intelligence advisor that injects strategic guidance mid-generation. Long-horizon agentic workloads get close to advisor-solo quality at executor-rate token costs.
- **Auto mode GA on Max** with Opus 4.7 — permission classifier in production (Haiku fast path + Opus thinking path on ambiguous). `PermissionDenied` hook can return `{"retry": true}` to rerun the tool. ([Lima cheatsheet](https://angelo-lima.fr/en/claude-code-cheatsheet-april-2026-update/))
- **Computer Use in the CLI** (April 2026 per Lima). Verify before relying on it.
- **Hook additions**:
  - `TeammateIdle` and `TaskCompleted` events for multi-agent workflows (v2.1.32-era).
  - `ConfigChange` hook fires when config files mutate during a session.
  - **HTTP hooks** (v2.1.63, 2026-02-28): POST JSON to a URL and receive JSON back instead of running shell.
  - `PermissionDenied` hook.
  - Hooks now receive `effort.level` and `$CLAUDE_EFFORT`.
  - PostToolUse can now replace tool output for **all** tools via `hookSpecificOutput.updatedToolOutput`.
  - Tool hook execution timeout raised from 60s to 10 minutes.
- **Slash command additions**: `/simplify`, `/batch`, `/effort` slider, `/ultrareview`, `/less-permission-prompts`, `/skills` type-to-filter, `/fast`, `/tui` fullscreen toggle.
- **Skills**: hot-reload in `~/.claude/skills` and `.claude/skills` (v2.1.0). Type-to-filter search box added recently.
- **SDK**: `SDKRateLimitInfo` and `SDKRateLimitEvent`. `Task(agent_type)` lets agents restrict which sub-agents they spawn. New `memory` frontmatter field with user/project/local scope.

## Codex `/goal` & Autonomous Modes

**Codex CLI 0.128.0 shipped 2026-04-30** ([release notes](https://releasebot.io/updates/openai/codex), [Simon Willison](https://simonwillison.net/2026/Apr/30/codex-goals/)):

> "Added persisted /goal workflows with app-server APIs, model tools, runtime continuation, and TUI controls for create, pause, resume, and clear." (PRs #18073–#18077, #20082)

Mechanics ([Kingy.ai](https://kingy.ai/ai/openai-codex-goal-the-new-long-horizon-mode-for-agentic-coding/), [Bawankule](https://www.adityabawankule.io/blog/codex-goal-meta-prompting)):

- A goal is a persisted task contract, not just a long system prompt. Lives at app-server level; survives process restart, network drop, deliberate pause.
- Active goals auto-pause on interrupt and auto-reactivate on resume (outside plan mode).
- TUI commands for create / pause / resume / clear. Terminal title shows an action-required indicator when the agent stalls.
- `codex update` for self-update without losing in-progress goals (persistence layer is binary-independent).
- Plan mode itself landed earlier in v0.122.0 (2026-04-20) and `/goal` builds on it.
- **Caveat** ([J.D. Hodges 2026-05-08](https://www.jdhodges.com/blog/codex-goal-feature-review/), [LaoZhang](https://blog.laozhang.ai/en/posts/codex-goal)): As of 2026-05-04, OpenAI's public CLI slash-command docs still don't list `/goal` — the 0.128.0 release and source tree are the stronger availability signal. Treat the feature as experimental and not safer than a regular Codex run; vague goals can burn weekly quota.
- Defaults changed: GPT-5.4 became default 2026-03-05; GPT-5.4 mini added 2026-03-17. Promo $100 Pro plan gives 10× Plus quota until 2026-05-31, then 5×.

Direct comparison ([DevToolPicks](https://devtoolpicks.com/blog/codex-goal-command-vs-claude-code-agents-2026), [Ralphable](https://ralphable.com/blog/codex-goal-command-ralph-loop-openai-built-in-autonomous-coding-agent-2026)): Codex `/goal` has no equivalent in Claude Code as of 2026-05. Anthropic's nearest analog is the Auto mode + Plan mode pairing, but it doesn't persist goal state across restarts. Closest non-OpenAI competitor: Factory's Droid "Missions."

**For us**: `/goal` is the right tool for the orchestrator queue items the user explicitly takes hours-to-days on. The persistence boundary maps directly onto our `decisions/` journal pattern.

## Gemini CLI

Current stable: **v0.41.0 (2026-05-08)**. v0.40.0 (2026-04-28) was the headline release ([Discussion #26216](https://github.com/google-gemini/gemini-cli/discussions/26216)):

- **Tiered Memory**: persistent memory primitive baked into the CLI.
- **Local Gemma for Model Routing** (experimental): use a local Gemma model to do intelligent routing among remote models. Path toward fully local Gemma execution.
- **Task Tracker (experimental)**: internal persistent task graph for complex objectives — Gemini's equivalent of Codex's `/goal` plumbing.
- **Topic Narrations**: replaces "I'll do this…" preamble with concise headings — directly attacks token waste.
- **Sub-agents** for parallel workflows (~v0.36+), enhanced plan mode with review steps.

Operational changes ([Discussion #22970](https://github.com/google-gemini/gemini-cli/discussions/22970)): Starting 2026-03-25, **Gemini Pro is paid-only**; free tier limited to Flash. Traffic prioritized by license type and account standing. Our `--lite` Gemini routing already lives on Flash/Pro paid path; nothing to change, but worth re-checking whether free-tier sessions are silently downgraded.

## OSS Alternatives Worth Watching

**OpenCode** (sst/opencode) is the surprise of 2026:

- 147K stars by April 2026 (up from 100K in Feb), 6.5M monthly developers, growing ~4.5× faster than Claude Code in star velocity ([MightyBot](https://mightybot.ai/blog/coding-ai-agents-for-accelerating-engineering-workflows/)).
- Go-based, MIT-licensed, 75+ model providers, **natively reads existing `CLAUDE.md` and skills directory** ([XDA](https://www.xda-developers.com/i-use-opencode-over-claude-code-and-its-every-bit-as-good/)) — migration cost near zero.
- Auth via API key, but also accepts ChatGPT Plus, GitHub Copilot, GitLab Duo subscriptions.
- Reported 82.7% on Terminal-Bench 2.0 vs Opus 4.7 at 69.4% per XDA — treat this benchmark claim cautiously, it's a single-source figure and not cross-verified.
- Active plugin ecosystem at [awesome-opencode](https://github.com/awesome-opencode/awesome-opencode), including Claude-Code-compatible hooks and background-agent plugins.
- Spinoff worth noting: [openwork](https://github.com/different-ai/openwork) — Claude Cowork clone built on OpenCode.

**Other contenders in the harness landscape** (from cross-references): Pi (RPC mode, primitives-first), Devin for Terminal, Cursor Agent, Qwen Code CLI (v0.15.6), Kimi CLI, Kiro CLI, Kilo, Mistral Vibe, DeepSeek TUI, Hermes CLI, Factory Droid (with "Missions" — Codex `/goal` competitor). Aider and Cline still active but no longer the fastest-growing.

**Recommendation**: try OpenCode for one Modal Genomics session. If `CLAUDE.md` + skills load cleanly and the LSP-aware feedback is meaningfully better, we have a fallback when Claude Code/Codex are rate-limited. Don't migrate from Claude Code wholesale — the hook/skill ecosystem is still ahead.

## Background / Scheduled / Persistent-Goal Patterns

| Vendor | Mechanism | Persistence | Notable |
|---|---|---|---|
| Codex CLI | `/goal` (0.128.0) | App-server layer; survives binary updates | Pause/resume; verified test loop |
| Claude Code | Auto mode + Plan mode + TaskCompleted hook | None at goal level | Multi-agent via `Task()` |
| Gemini CLI | Task Tracker (experimental) | Persistent task graph | Local Gemma router |
| Factory | Droid Missions | Closed | Closest commercial `/goal` peer |
| Community | Ralph loop (bash) | Whatever you write | Now superseded for Codex users |

Our manual `scripts/orchestrator.py` queue is conceptually the right primitive — `/goal` validates that we shouldn't replace it with something less structured. The interesting move is to **wrap our orchestrator items as Codex `/goal` invocations** for jobs where state should survive a laptop closing.

## Memory & Attestation Patterns

The "have we already done this work?" problem (our recurring sin) has acquired two vendor-shipped answers in this window:

- **Anthropic managed-agent memory** (public beta, header `managed-agents-2026-04-01`): Claude Platform-side memory store usable from Claude Code and the Agent SDK. Worth a side-by-side against our `agent-memory/researcher/MEMORY.md` for the deduplication-of-prior-work case specifically.
- **Gemini CLI Tiered Memory** (v0.40.0): explicit memory tiers in the CLI itself.

Caveats (verify before adoption): neither vendor's docs in this sweep describe an attestation/provenance model. They look more like opaque KV stores than the cite-and-quote pattern our `MEMORY.md` enforces. Hand-rolled wins on auditability for now.

OpenCode's `awesome-opencode` directory references several memory plugins (Mem0, Memos, custom stores). No clear standard.

## MCP Ecosystem

State of the protocol as of May 2026:

- **Streamable HTTP** is the production transport. SSE deprecated (spec 2025-03-26). Stdio remains for local. WebSocket transport proposed but not in spec.
- **OAuth 2.1 PKCE** is the standard auth path for remote servers.
- **Elicitation** (server prompts user for input mid-task) is shipping in Claude Code with auto-dialogs and an Elicitation hook to auto-respond. Strong primitive for our hooks.
- **MCP Apps (SEP-1865)** formalized — UI extension to MCP.
- **Governance**: jointly run by Anthropic, OpenAI, and Google as of 2026 ([BuildBetter](https://blog.buildbetter.ai/mcp-vs-rest-api-why-product-teams-are-switching-in-2026/)). MCP Dev Summit NA April 2026, ~1,200 attendees.
- Reported **97M installs by March 2026**; 10K+ community servers; OpenAI deprecating Assistants API in favor of MCP (mid-2026 sunset). Treat these aggregate figures with skepticism — single-source from byteiota; the trend direction is uncontested but the absolute numbers aren't independently verified here.
- 2026 roadmap priorities: transport scalability, **agent-to-agent (A2A) communication**, governance maturity, enterprise readiness ([Tedt.org](https://tedt.org/MCPs-2026-Roadmap/)).

Practical: our `.mcp.json` still uses stdio servers. No urgent need to migrate, but new MCP work should be Streamable HTTP if it's likely to be shared across machines or projects.

## Speculation Section (clearly labeled)

- **Anthropic will ship a `/goal` analog within Q3 2026.** Multiple commentators ([Ralphable](https://ralphable.com/blog/codex-goal-command-ralph-loop-openai-built-in-autonomous-coding-agent-2026)) flag it as inevitable. Not in any official roadmap I could surface.
- **OpenCode benchmark claims need independent replication.** 82.7% on Terminal-Bench 2.0 vs Opus 4.7's 69.4% is single-source and "harness over model" is exactly the kind of claim that benefits from selective reporting. The model in OpenCode for that score isn't clear from the article.
- **OpenAI Codex CLI `/goal` docs are lagging the implementation.** As of 2026-05-04, `/goal` was not in the public slash-command docs ([LaoZhang](https://blog.laozhang.ai/en/posts/codex-goal)) despite shipping 2026-04-30. Could be an experimental gate; could be docs drift. Don't rely on it for any production workflow until OpenAI ships docs.
- **"Hermes CLI"**: I found references to a "Hermes" coding agent in [open-design](https://github.com/nexu-io/open-design)'s 16-CLI detection list but did not surface a primary source for what it is or who runs it. If the user named it, ask them where they saw it.
- **Claude managed-agent memory may make our hand-rolled `MEMORY.md` redundant** for some subagents — but the docs in this sweep don't show enough about how content is structured or queried for me to commit to that. Pilot before migrating.
- **Cross-CLI standardization on `CLAUDE.md` / skills**: OpenCode reads them natively, open-design uses 16-CLI auto-detection. There's a real chance the directory layout becomes a de facto cross-vendor standard within the year. If so, we have already invested in the right format.

## Sources

Vendor changelogs / primary:
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://platform.claude.com/docs/en/release-notes/overview
- https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-7
- https://github.com/google-gemini/gemini-cli/discussions/26216 (v0.40.0)
- https://github.com/google-gemini/gemini-cli/discussions/22970 (traffic prioritization)
- Codex release notes via https://releasebot.io/updates/openai/codex

Independent / dated commentary:
- https://simonwillison.net/2026/Apr/30/codex-goals/ (Codex /goal)
- https://angelo-lima.fr/en/claude-code-cheatsheet-april-2026-update/ (Claude Code April update)
- https://allthings.how/claude-code-changelog/ (Claude Code 2.1.x walkthrough)
- https://ralphable.com/blog/codex-goal-command-ralph-loop-openai-built-in-autonomous-coding-agent-2026
- https://kingy.ai/ai/openai-codex-goal-the-new-long-horizon-mode-for-agentic-coding/
- https://www.jdhodges.com/blog/codex-goal-feature-review/ (2026-05-08, skeptical take)
- https://nimbalyst.com/blog/claude-code-vs-codex-vs-opencode-definitive-comparison/
- https://mightybot.ai/blog/coding-ai-agents-for-accelerating-engineering-workflows/ (OpenCode growth numbers)
- https://www.xda-developers.com/i-use-opencode-over-claude-code-and-its-every-bit-as-good/
- https://thoughts.jock.pl/p/ai-coding-harness-agents-2026 ("harness" term-of-art, +16pt effect)
- https://tedt.org/MCPs-2026-Roadmap/
- https://en.wikipedia.org/wiki/Model_Context_Protocol

<!-- knowledge-index
generated: 2026-05-11T04:07:29Z
hash: d7ab10666436


end-knowledge-index -->
