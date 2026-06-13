# System Architecture

How the agent infrastructure works, end to end — the **durable narrative**: the
layer model, how a session loads, the self-improvement loop, the memory problem.

**For the live inventory — repos, launchd loops, hooks, MCP servers, skills,
doc freshness — run `just orient`.** That reads the source of truth each time and
cannot go stale. This doc deliberately holds NO hand-listed inventory: every count,
job name, and server name moved to `orient` precisely because this file once
described a deleted orchestrator as "live" for two months. Prose explains *why* the
layers exist; `orient` reports *what* is currently wired.

```
just orient      → what IS the system right now   (live map)
just doctor      → is it HEALTHY                   (validation)
just dashboard   → what HAPPENED recently          (activity / cost)
this doc         → WHY it is shaped this way        (durable narrative)
```

---

## 1. What This Is

A personal agent infrastructure spanning a hub repo (**agent-infra**) plus the
project repos it serves (intel, genomics, phenome, …) and shared layers
(`skills/`, `research-mcp/`, `llmx/`). Claude Code is the primary agent runtime;
Codex/Gemini/Kimi CLIs act as sub-agents and alternate interfaces. The system
layers on top of the runtime: hooks for guardrails, skills for capabilities, MCP
servers for tool access, launchd jobs for unattended loops, and measurement
scripts for self-improvement.

The goal (GOALS.md, constitution): agents get more autonomous over time, measured
by declining supervision — conditioned on whether the work has a clear verifier.

---

## 2. Layer Model

Six layers, loaded bottom-up into every session. Each is a different filesystem
location with different scope and governance. (`just orient` lists what currently
populates each.)

```
┌─────────────────────────────────────────────────────────┐
│  6. MCP Servers          (external tool access)          │
├─────────────────────────────────────────────────────────┤
│  5. Recurring loops      (launchd jobs + /loop sessions) │
├─────────────────────────────────────────────────────────┤
│  4. Project Config       (per-repo rules + hooks)        │
├─────────────────────────────────────────────────────────┤
│  3. Skills               (shared capabilities)           │
├─────────────────────────────────────────────────────────┤
│  2. Shared Hooks         (cross-project guardrails)      │
├─────────────────────────────────────────────────────────┤
│  1. Global Config        (universal rules + settings)    │
└─────────────────────────────────────────────────────────┘
```

**Layer 1 — Global Config (`~/.claude/`).** Loaded in every project, every
session: `CLAUDE.md` (universal rules), `settings.json` (hook wiring for all
events, status line, enabled plugins, env), `rules/` (auto-loaded operational
gotchas), `statusline.sh`, and `projects/<path>/memory/MEMORY.md` (the per-project
auto-memory index). MCP servers are configured here too, in `~/.claude.json`.

**Layer 2 — Shared Hooks (`~/Projects/skills/hooks/`).** Shell scripts referenced
by path from both global and per-project `settings.json`. Change once, affects
everywhere — which is exactly why deploying one that touches 3+ projects is a
human-gated boundary. Convention: exit 0 (pass), exit 2 (block with message),
stderr (advisory). Fail open unless on the explicit fail-closed list (protected
data writes, multiline bash, repeated-failure loops). `just orient` shows the live
event→count breakdown; `just hook-telemetry` shows what's actually firing.

**Layer 3 — Skills (`~/Projects/skills/`).** Each a `SKILL.md` with optional
`references/`. Symlinked into the global skills dir by `friend-sync.sh` so they load
in every project. Descriptions appear in the system-prompt skill list (budgeted —
see `context-budget-principles.md` §7); the body loads on `/invoke`. agent-infra
owns skill *quality* (authoring, testing, propagation) even though the directory
is separate.

**Layer 4 — Project Config (per-repo `.claude/`).** `CLAUDE.md` (domain identity +
constitution), `settings.json` (project hooks), `rules/` (domain indexes/checklists,
often path-scoped so they load only when relevant files are touched), `skills/`
(symlinks), `overviews/` (generated codebase summaries injected at start),
`plans/` + `checkpoint.md` (ephemeral handoff). `AGENTS.md`/`GEMINI.md` symlink to
`CLAUDE.md` for cross-vendor instruction parity.

**Layer 5 — Recurring loops.** The orchestrator (a cron task-runner) was
**eradicated 2026-06-07** — it ran unreliably and opaquely. Unattended work is now
two things: **local launchd jobs** (zero-API, deterministic — indexing, corpus
sync, retention, map refresh, etc.) and **`/loop` interactive sessions** (the human
runs Claude Code and loops recurring tasks like `/improve maintain`). Truly
unattended cloud work uses `/schedule` (Claude Code native cron). `just orient`
lists the live launchd jobs with their last-exit status; the canonical descriptions
live in CLAUDE.md's "Active launchd jobs".

**Layer 6 — MCP Servers.** External tool access, configured in `~/.claude.json`
(global) and per-project scope. `just orient` lists what's wired; the session's
deferred-tool list shows what's reachable via `ToolSearch`.

---

## 3. Information Flow

### Session startup (load order)

```
1.  ~/.claude/CLAUDE.md                         global rules
2.  ~/.claude/rules/*.md                         global gotchas (path-scoped load on match)
3.  {project}/CLAUDE.md                           project identity + constitution
4.  {project}/.claude/rules/*.md                  project rules (path-scoped load on match)
5.  ~/.claude/projects/{path}/memory/MEMORY.md    auto-memory index
6.  MCP servers start (~/.claude.json + project scope)
7.  SessionStart hooks fire:
      - write .claude/current-session-id, snapshot git baseline
      - PEER-SESSION warning if another claude shares the checkout
      - inject codebase overview INDEX block as additionalContext
      - inject incomplete-plan pointers
8.  Skill descriptions → system prompt
9.  Deferred MCP tool list (reachable via ToolSearch)
```

Always-loaded budget (rules + memory) measured ~16.7K tokens for an agent-infra
session (2026-06-13); skills, tool list, and overview add on top. Every subagent
spawn pays the always-loaded portion too. Measure live with `just context-budget`.

### During a session

```
User message → UserPromptSubmit hooks (context-warn, feedback intake, tab color)
  → model generates → for each tool call:
      PreToolUse hooks (matched by tool name) — may BLOCK (exit 2) or ADVISE
      → tool executes →
      PostToolUse hooks — warn / log / inject guidance
  → model stops → Stop hooks (plan-status, verify-claimed-work, uncommitted-warn)
```

### Compaction / session end

```
context near limit → PreCompact hook (saves nuance + prompts checkpoint.md)
  → summarize → PostCompact hook (verify claimed work survived; trust git not memory)
session ends → SessionEnd hooks (receipt log, overview refresh marker, session index)
```

---

## 4. Cross-Project Architecture

```
~/Projects/
├── agent-infra/        # the hub: constitution, hooks governance, measurement, research
├── intel/  genomics/  phenome/  …   # project repos served by the hub
├── skills/             # shared skills + skills/hooks/ (cross-project guardrails)
├── research-mcp/       # research paper MCP server
└── llmx/               # multi-model CLI transport (editable-installed)
```

Shared resources flow downward from `agent-infra` and `skills/`. Sub-projects don't
carry agent-infra's knowledge — they **query it on demand** via the `agent-infra`
MCP (scopes: all, hooks, failures, research, architecture, health, …). Propagation
is pull-based and organic: the human runs sessions from agent-infra that touch other
repos; cross-repo attestation is enforced at each repo's mutation gateway via a
transactional outbox (see CLAUDE.md `<cross_project_rules>`), not an agent ritual.

**Session/telemetry store:** `~/.claude/agentlogs.db` (cross-vendor: Claude + Codex
+ Gemini + Kimi), queried via `uv run agentlogs …`. JSONL side-logs:
`session-receipts.jsonl`, `hook-triggers.jsonl`, `event-log.jsonl`. (`runlogs.db`
and `runlog.py` are **dead** — see `.claude/rules/session-forensics.md`.)

---

## 5. Self-Improvement Loop

The feedback cycle that makes the system get better:

```
Sessions happen (human + agent work)
  ↓  SessionEnd hooks
reflect_capture.py        zero-LLM capture of correction signals + omission-probe firings
  ↓
reflect.py → fm.py        cluster signals, classify against the Failure-Mode taxonomy
  ↓  (+ /observe sessions for deep behavioral analysis)
improvement-log.md        findings appended; two streams — [obs] behavioral ledger
                          (mined for recurrence) and [ ] actionable queue
  ↓  recurs 2+ sessions AND checkable-predicate-or-architectural?
Implementation            hook / rule / skill / code change, committed with Evidence trailer
  ↓
gov.py + graders          governance shrink: re-run a scaffold's verifier with it removed;
                          if it still passes, the scaffold was training wheels → retire
```

Governance is **subtractive by design** (Gov-ID blocks carry goal + verifier +
blast_radius; see `.claude/rules/gov-id.md`) — the corpus is meant to shrink as model
capability rises, not just grow.

**Measurement scripts** (epistemic instrumentation, all in `scripts/`):
`supervision-kpi.py`, `calibration-canary.py`, `pushback-index.py`,
`trace-faithfulness.py`, `safe-lite-eval.py`, `epistemic-lint.py`, `fold-detector.py`.

**Deterministic RSI** (`scripts/autoresearch.py` + `experiments/`): mutates a small
editable surface, runs a *real locked eval*, keeps or discards. Boundary: RSI
improves code only where the evaluator is ground-truth-bound — a model-as-judge
proxy does not make taste work "verifiable" (a bad eval is worse than none).

---

## 6. The Memory Problem

The user observes that Claude Code over-relies on MEMORY.md — citing it when it
should read the actual codebase. This is **attention capture**, not classic context
rot, from three reinforcing mechanisms:

1. **Positional privilege.** MEMORY.md is injected near the top of context. Start-
   positioned info gets better recall than middle (Lost-in-the-Middle). It's always
   "in mind"; code requires active retrieval.
2. **Instructional reinforcement.** The memory system prompt tells the model to read
   memories when relevant and save when learning — making memory-checking a default,
   not a last resort.
3. **Zero-cost access.** Reading MEMORY.md costs no tool call; reading code costs
   latency + tokens + a decision about *what* to read. The rational-lazy strategy is
   "check context first" — correct in principle, but it creates staleness risk:
   MEMORY.md reflects when it was written, not current state.

**Consequence:** MEMORY.md assertions about file paths, function names, or flags may
be stale; the model may "remember" something exists without verifying it still does.

**Mitigations (in place):** keep MEMORY.md to an *index of pointers* not content;
the global rule "if memory names a specific file/function/flag, verify it still
exists before acting"; periodic pruning of entries now derivable from code. The
honest limit: position advantage is structural and can't be removed; there's no hook
for "cited memory without verifying" (semantic predicate) — cross-model review is the
only real check. **`just orient` is part of the fix:** when the question is "what
*is* the system," querying live ground truth beats trusting any cached prose.

---

## 7. Where to Find Things

| Question | Look here |
|----------|-----------|
| What is the system *right now*? | `just orient` (repos, loops, hooks, MCP, skills, doc freshness) |
| Is the infra healthy? | `just doctor` |
| What happened in recent sessions? | `just dashboard`, `uv run agentlogs recent\|search\|stats` |
| Why does a hook fire? | `~/.claude/settings.json` or project `.claude/settings.json` → hook path → read the script; `just hook-telemetry` for what's firing |
| What rules load for project X? | `{project}/CLAUDE.md` + `.claude/rules/` + the two global equivalents |
| What MCP tools exist? | `just orient` (MCP section) + the session's deferred-tool list |
| What skills exist? | `just orient` (count) + `~/Projects/skills/*/SKILL.md` |
| How is the corpus/science-graph wired? | `corpus-substrate-architecture.md` |
| How is search/retrieval wired? | `search-retrieval-architecture.md` |
| What was decided and why? | `decisions/*.md` (+ `.claude/rules/vetoed-decisions.md` for what NOT to rebuild) |
| Research on topic X? | `research/` (index: `.claude/rules/research-index.md`) |
| Is a doc stale? | `just orient` flags doc age + drift (live launchd jobs vs. CLAUDE.md) |
