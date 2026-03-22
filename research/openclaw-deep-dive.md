---
title: OpenClaw Architecture Deep Dive — Research Memo
date: 2026-03-21
---

# OpenClaw Architecture Deep Dive — Research Memo

**Question:** How does OpenClaw actually implement its memory, heartbeat, pre-compaction flush, command queue, skills, hooks, and philosophy files — and what architectural lessons apply to Claude Code-based agent infrastructure?
**Tier:** Deep | **Date:** 2026-03-01
**Ground truth:** No prior research in corpus. Our own Claude Code hook system documented in meta CLAUDE.md.

## Architecture Summary

OpenClaw (242K stars, TypeScript, MIT) is a personal AI assistant running on-device. The agent runtime is derived from **pi-mono** (`badlogic/pi-mono`) — Mario Zechner's minimal coding agent with 4 tools (Read, Write, Edit, Bash). OpenClaw wraps Pi with a gateway that adds multi-channel messaging (WhatsApp, Telegram, Discord, etc.), heartbeats, memory, skills, hooks, and a command queue.

Key insight: OpenClaw is a **gateway** around Pi, not a modified Pi. The Pi agent core stays minimal; OpenClaw orchestrates sessions, memory, delivery, and scheduling around it.

---

## 1. Memory System Implementation

### Architecture: Three Layers

**Layer 1: Markdown Files (source of truth)**
- `MEMORY.md` — curated long-term memory (optional, loaded only in private/DM sessions)
- `memory/YYYY-MM-DD.md` — daily append-only logs
- Both live in the agent workspace (`~/.openclaw/workspace/` default)
- Agent reads today + yesterday on session start

**Layer 2: Vector Search (semantic recall)**
- `memory_search` tool — semantic search over indexed Markdown chunks
- `memory_get` tool — targeted read of specific file/line range
- Chunking: ~400 token target, 80-token overlap
- Storage: per-agent SQLite at `~/.openclaw/memory/<agentId>.sqlite`
- Provider cascade: local GGUF → OpenAI → Gemini → Voyage → Mistral
- Default local model: `embeddinggemma-300m-qat-Q8_0.gguf` (~0.6 GB)
- Uses sqlite-vec for in-database vector queries when available

**Layer 3: Hybrid BM25 + Vector Search**
```
Vector + Keyword → Weighted Merge → Temporal Decay → Sort → MMR → Top-K
```
- `vectorWeight: 0.7, textWeight: 0.3` (configurable)
- MMR re-ranking for diversity (lambda=0.7, off by default)
- Temporal decay: exponential, half-life 30 days (off by default)
  - Today: 100%, 7 days: 84%, 30 days: 50%, 90 days: 12.5%
  - Evergreen files (MEMORY.md, non-dated files) never decay
- BM25 catches exact tokens (IDs, env vars, code symbols) that embeddings miss

**QMD Backend (experimental alternative)**
- Local-first search sidecar: BM25 + vectors + reranking via Bun + node-llama-cpp
- Markdown stays source of truth; OpenClaw shells out to QMD for retrieval
- Runs fully local, auto-downloads GGUF models
- Can index session transcripts for conversation recall

### How Memory Tools Work (from source)
- `memory_search`: semantically searches chunks, returns snippet text (capped ~700 chars), file path, line range, score
- `memory_get`: reads specific workspace-relative memory file, optionally from a starting line for N lines
- Both are agent-facing tools the model calls; nothing magical

### Comparison to Our System
| Aspect | OpenClaw | Our System (Claude Code) |
|--------|----------|-------------------------|
| Long-term memory | `MEMORY.md` + daily logs | `MEMORY.md` (agent-memory) |
| Daily logs | `memory/YYYY-MM-DD.md` | None (gap) |
| Semantic search | Vector + BM25 hybrid | None built-in; selve for personal knowledge |
| Memory tools | `memory_search`, `memory_get` | Read tool on MEMORY.md |
| Pre-compaction flush | Silent agentic turn | `precompact-log.sh` (side-effect only, no agentic turn) |
| Temporal decay | Configurable half-life | None |

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/memory (archived)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/src/auto-reply/reply/memory-flush.ts]

---

## 2. Heartbeat System Implementation

### How the Timer Works (from source: `src/infra/heartbeat-runner.ts`)

The heartbeat is a **periodic agent turn** in the main session. Implementation:

1. `startHeartbeatRunner()` creates a runner with per-agent state:
   - Each agent gets `HeartbeatAgentState`: `agentId`, `heartbeat config`, `intervalMs`, `lastRunMs`, `nextDueMs`
   - A single `setTimeout` drives the tick (`.unref()` so it doesn't keep process alive)

2. On each tick, `requestHeartbeatNow({ reason: "interval" })` fires

3. `runHeartbeatOnce()` is the core function:
   - Checks: is heartbeat enabled? Within active hours? Queue busy?
   - **Preflight**: reads `HEARTBEAT.md` from workspace. If effectively empty (only blank lines/headers), **skips the run** to save API calls
   - Resolves session (main session by default, configurable)
   - Builds prompt: heartbeat prompt + `appendCronStyleCurrentTimeLine()` for time context
   - Calls `getReplyFromConfig()` — this runs a full embedded Pi agent turn
   - Processes response:
     - `HEARTBEAT_OK` → suppress delivery, prune transcript (truncate file back to pre-heartbeat size)
     - Alert content → deliver to target channel
     - Duplicate detection: same text within 24h → skip (anti-nag)

4. **Transcript pruning on OK**: When the model replies `HEARTBEAT_OK`, OpenClaw **truncates the transcript file** back to its pre-heartbeat size. This removes the user+assistant turns that were written during the heartbeat run, preventing context pollution from zero-information exchanges.

### Key Design Decisions
- **Default interval**: 30m (1h for Anthropic OAuth/setup-token users)
- **Active hours**: configurable time window (e.g., 08:00-22:00) with timezone support
- **Queue check**: if the main command queue is busy, heartbeat is skipped and retried later
- **Model override**: heartbeat can use a cheaper model than the main session
- **Target routing**: `none` (internal only), `last` (last contacted channel), or specific channel
- **Per-agent heartbeats**: if any agent in the list has a heartbeat block, only those agents run heartbeats

### What a Heartbeat Turn Looks Like
```
System: "Heartbeat" section in system prompt + memoryFlush system prompt
User: "Read HEARTBEAT.md if it exists (workspace context). Follow it strictly.
       Do not infer or repeat old tasks from prior chats.
       If nothing needs attention, reply HEARTBEAT_OK.
       Current time: Saturday, March 1, 2026, 8:30 PM (America/New_York)"
Agent: [runs tools, checks things, then either alerts or replies HEARTBEAT_OK]
```

### Cron vs Heartbeat
- **Heartbeat**: periodic awareness checks in main session (batches multiple checks)
- **Cron**: precise scheduling in isolated sessions (exact timing, different model)
- Heartbeat is like our orchestrator concept; cron is like traditional scheduled jobs

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/src/infra/heartbeat-runner.ts]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/heartbeat (archived)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/cron-vs-heartbeat (removed)]

---

## 3. Pre-Compaction Memory Flush

### Implementation (from source: `src/auto-reply/reply/memory-flush.ts`)

The flush is a **silent agentic turn** injected by the gateway before compaction wipes the context.

**Trigger condition** (`shouldRunMemoryFlush()`):
```
totalTokens >= contextWindow - reserveTokensFloor - softThresholdTokens
```
- `reserveTokensFloor`: 20,000 tokens (configurable)
- `softThresholdTokens`: 4,000 tokens (configurable)
- One flush per compaction cycle (tracked via `memoryFlushCompactionCount` in `sessions.json`)

**The silent turn**:
```
System prompt: "Pre-compaction memory flush turn. The session is near auto-compaction;
               capture durable memories to disk. You may reply, but usually NO_REPLY is correct."

User prompt:   "Pre-compaction memory flush. Store durable memories now
               (use memory/YYYY-MM-DD.md; create memory/ if needed).
               IMPORTANT: If the file already exists, APPEND new content only
               and do not overwrite existing entries.
               If nothing to store, reply with NO_REPLY."
```

**Suppression mechanism**:
- `NO_REPLY` token at start of response → delivery suppressed
- Since 2026.1.10: streaming is also suppressed when partial chunk begins with `NO_REPLY`
- `ensureNoReplyHint()` automatically adds NO_REPLY instructions if not already in prompt

**Wait-for-idle guard**: `src/agents/pi-embedded-runner/wait-for-idle-before-flush.ts` — the flush waits for the agent to be idle before injecting the silent turn (avoids colliding with active tool calls).

### Comparison to Our System
We have `precompact-log.sh` which logs compaction events but does NOT inject an agentic turn. OpenClaw's approach is architecturally superior — it gives the model agency to decide what to persist before losing context. Our system relies entirely on the model proactively saving state during normal turns, which is unreliable.

**Key gap in Claude Code**: Claude Code's PreCompact hook has "no decision control" — it can log but cannot inject content or run an agentic turn. To replicate OpenClaw's memory flush, we would need a different approach (perhaps a UserPromptSubmit hook that monitors token usage, or a prompt hook that injects memory-save reminders).

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/src/auto-reply/reply/memory-flush.ts]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/session-management-compaction (archived)]

---

## 4. Command Queue / Lane System

### Implementation (from source: `src/process/command-queue.ts`, `src/process/lanes.ts`)

**Lanes**: Four named lanes as a TypeScript const enum:
```typescript
export const enum CommandLane {
  Main = "main",      // inbound messages + heartbeats
  Cron = "cron",      // cron job runs
  Subagent = "subagent", // subagent tasks
  Nested = "nested",  // nested operations
}
```

**Queue mechanics**:
- Lane-aware FIFO queue with configurable concurrency per lane
- Default concurrency: 1 for unconfigured lanes; main defaults to 4, subagent to 8
- Per-session lanes guarantee only one agent run per session at a time
- A session key maps to its own sub-lane (`session:<key>`) then into the global lane

**Implementation details**:
- Pure TypeScript + Promises (no external deps, no background threads)
- `enqueueCommandInLane()` returns a Promise that resolves when the task completes
- Tasks that wait >2s get a warning logged
- `clearCommandLane()` rejects all pending entries with `CommandLaneClearedError`
- `markGatewayDraining()` rejects new enqueues with `GatewayDrainingError` during shutdown
- `resetAllLanes()` handles SIGUSR1 in-process restarts (bumps generation, clears stale task IDs)
- Generation tracking: stale completions from old in-flight tasks are ignored after restart

**Message coalescing modes** (per channel, configurable):
- `steer`: inject into current run (cancels pending tool calls at next tool boundary)
- `followup`: queue for next agent turn after current run
- `collect`: coalesce all queued messages into single followup turn (default)
- `steer-backlog`: steer now AND preserve for followup
- `interrupt` (legacy): abort active run, run newest message
- Debounce: default 1000ms, cap: 20 messages, overflow: `summarize`

### Comparison to Our System
We have nothing comparable. Claude Code processes one message at a time in a single session. No lane system, no queue coalescing, no concurrent session management. This matters less for us (single-user CLI) but would matter for any gateway/multi-channel setup.

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/src/process/command-queue.ts]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/queue (archived)]

---

## 5. Skills System

### How Skills Are Loaded

**Three locations, precedence high→low**:
1. `<workspace>/skills/` (per-agent workspace skills)
2. `~/.openclaw/skills/` (managed/local, shared across workspaces)
3. Bundled skills (shipped with npm package or OpenClaw.app)

**Skill format**: Directory with `SKILL.md` containing YAML frontmatter + Markdown instructions. Compatible with AgentSkills spec and Pi.

**Gating (load-time filters)** via `metadata.openclaw.requires`:
```yaml
metadata:
  {"openclaw": {
    "requires": {"bins": ["uv"], "env": ["GEMINI_API_KEY"], "config": ["browser.enabled"]},
    "primaryEnv": "GEMINI_API_KEY"
  }}
```
- `bins`: required binaries on PATH
- `anyBins`: at least one must exist
- `env`: env var must exist or be in config
- `config`: openclaw.json paths that must be truthy
- `os`: platform filter (darwin, linux, win32)

**Lazy loading**: Skills are **snapshotted at session start** and reused for subsequent turns. Changes take effect on next new session (or via hot-reload watcher, debounced 250ms).

**Token impact**: Eligible skills are injected as compact XML in the system prompt. Cost: 195 chars base + ~97 chars per skill + field lengths.

**Config injection**: `skills.entries.<name>.env` and `skills.entries.<name>.apiKey` inject secrets into the host process for that agent turn, then restore the original environment.

**ClawHub**: Public registry at clawhub.com for discovering/installing/syncing skills.

### Comparison to Our System (Claude Code Skills)
| Aspect | OpenClaw | Claude Code |
|--------|----------|-------------|
| Format | `SKILL.md` with YAML frontmatter | `SKILL.md` with YAML frontmatter (compatible) |
| Locations | workspace > managed > bundled | `.claude/skills/` per project, symlinked from shared |
| Gating | Binary/env/config/OS checks at load time | None (always loaded) |
| Hot reload | Watcher with debounce | None (session restart needed) |
| Registry | ClawHub (public) | None |
| Env injection | Per-skill env scoped to agent turn | None |
| Token control | XML injection, deterministic cost | Full content injection |

Key difference: OpenClaw skills are **filtered at load time** — if the binary/env isn't available, the skill never enters the prompt. Our skills are always loaded. This matters at scale (many skills).

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/skills (archived)]

---

## 6. Philosophy Files (SOUL.md, IDENTITY.md, AGENTS.md, etc.)

### Default Templates

**SOUL.md** — "Who You Are"
- Core truths: be genuinely helpful (not performatively), have opinions, be resourceful before asking, earn trust through competence, remember you're a guest
- Boundaries: private things stay private, ask before acting externally, never send half-baked replies
- Vibe: "the assistant you'd actually want to talk to"
- Continuity: "Each session, you wake up fresh. These files ARE your memory."
- Self-modifiable: "This file is yours to evolve. As you learn who you are, update it."

**SOUL.dev.md** — Dev mode persona (C-3PO)
- Dramatic debug companion with personality quirks
- Demonstrates that SOUL.md is meant to be swapped/evolved

**IDENTITY.md** — "Who Am I?"
- Name, Creature, Vibe, Emoji, Avatar
- Filled in during first conversation (bootstrap ritual)
- "This isn't just metadata. It's the start of figuring out who you are."

**BOOTSTRAP.md** — "Hello, World"
- One-time first-run ritual for new workspaces
- Agent asks user: what's my name? what kind of creature am I? what's my vibe?
- Updates IDENTITY.md, USER.md, and SOUL.md collaboratively
- Deletes itself when done: "You don't need a bootstrap script anymore — you're you now."

**AGENTS.md** (repo-level, NOT template) — Repository Guidelines
- The repo's own AGENTS.md is a massive 400+ line coding guidelines document
- Project structure, build commands, commit conventions, multi-agent safety rules
- This is equivalent to our CLAUDE.md per project

**HEARTBEAT.md** — Heartbeat Checklist
- Default template is intentionally empty (just comments)
- User adds tasks: "Quick scan: anything urgent in inboxes?"
- Empty file = heartbeat API calls skipped

**Workspace file map**:
```
~/.openclaw/workspace/
├── AGENTS.md          # Operating instructions (loaded every session)
├── SOUL.md            # Persona, tone, boundaries (loaded every session)
├── USER.md            # User profile (loaded every session)
├── IDENTITY.md        # Agent name/vibe/emoji
├── TOOLS.md           # Tool notes and conventions
├── HEARTBEAT.md       # Heartbeat checklist (optional)
├── BOOT.md            # Startup checklist on gateway restart (optional)
├── BOOTSTRAP.md       # One-time first-run ritual (deleted after)
├── MEMORY.md          # Curated long-term memory (optional, private only)
├── memory/
│   └── YYYY-MM-DD.md  # Daily logs
└── skills/            # Workspace-specific skills
```

### Architectural Philosophy
The philosophy is **agent-as-person**: the workspace files collectively form the agent's identity and memory. The agent is expected to evolve its own SOUL.md over time. This is fundamentally different from our approach where CLAUDE.md is human-owned and human-edited.

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/SOUL (archived)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/IDENTITY (archived)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/BOOTSTRAP (removed)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/agent-workspace (removed)]
[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/AGENTS.md]

---

## 7. Hook System Comparison

### OpenClaw Hooks
- **TypeScript handlers** in directories with `HOOK.md` + `handler.ts`
- **Discovery**: workspace hooks > managed hooks > bundled hooks
- **Events**: `command:new`, `command:reset`, `command:stop`, `agent:bootstrap`, `gateway:startup`, `message:received`, `message:sent`, `tool_result_persist`
- **Handler receives**: event context with session key, timestamp, messages array (push to deliver to user), workspace dir, config
- **Cannot block**: hooks fire-and-forget; they can push messages but cannot deny/block operations
- **4 bundled hooks**: session-memory (save context on `/new`), bootstrap-extra-files, command-logger, boot-md
- **Hook packs**: npm packages that export hooks, installable via `openclaw hooks install`

### Claude Code Hooks
- **Shell scripts** (command type) or **prompt/agent hooks** (LLM-judged)
- **17 event types** including PreToolUse, PostToolUse, Stop, SessionStart, etc.
- **Can block**: PreToolUse exit code 2 denies the tool call; Stop exit code 2 blocks completion
- **Decision control**: JSON output for allow/deny/ask decisions
- **No discovery**: configured explicitly in `settings.json`
- **No registry**: shared via file paths

### Key Differences

| Aspect | OpenClaw | Claude Code |
|--------|----------|-------------|
| Language | TypeScript | Shell scripts (command), LLM (prompt/agent) |
| Can block tool calls | No | Yes (PreToolUse exit 2) |
| Can block completion | No (future: maybe) | Yes (Stop exit 2) |
| Event granularity | 7 events (broad) | 17 events (granular) |
| Discovery | Automatic from directories | Manual in settings.json |
| State management | Event context + custom messages in session | Environment variables + file-based state |
| Hook types | handler.ts only | command, prompt, agent |
| Registry | Planned (hook packs via npm) | None |
| Per-tool routing | No (event-level only) | Yes (PreToolUse:Bash, PostToolUse:Write, etc.) |

**Claude Code is more powerful for enforcement** (blocking hooks), while **OpenClaw is more powerful for extension** (TypeScript handlers, custom messages, session state). OpenClaw hooks cannot prevent bad behavior; Claude Code hooks can.

OpenClaw's "future events" list notably includes `session:start`, `session:end`, and `agent:error` — all of which Claude Code already has.

[SOURCE: https://raw.githubusercontent.com/openclaw/openclaw/main/hooks (archived)]

---

## 8. Pi Agent Philosophy (from Armin Ronacher's blog)

### Core Design Principles

1. **Minimal core**: Pi has the shortest system prompt of any agent. Only 4 tools: Read, Write, Edit, Bash. Everything else is extensions.

2. **No MCP by design**: "If you want the agent to do something it doesn't do yet, you don't download an extension — you ask the agent to extend itself." Code writing code is the philosophy.

3. **Session trees**: Pi sessions are trees with branching. You can branch into a side-quest (e.g., fix a broken tool), then rewind with a summary. This avoids wasting main-session context.

4. **Extension state persistence**: Extensions can persist state into sessions (custom messages in JSONL). This enables hot-reloading — agent writes code, reloads, tests, loops.

5. **Model-provider portability**: Session format doesn't lean into provider-specific features. Messages can come from different providers in the same session.

6. **Tools outside the context**: Extensions can register tools, but the philosophy favors skills (prompt-level instructions) over tools (API-level registrations). Tools need to be in the system context at session start; skills can be loaded lazily.

### Agent Building Agents
Pi celebrates the idea of agents extending themselves:
- Armin's agent built its own to-do system, browser automation (CDP skill), commit workflow, code review
- Skills are "hand-crafted by my clanker and not downloaded from anywhere"
- Extensions are meant to be remixed: "point your agent to one and remix it to your heart's content"

[SOURCE: https://lucumr.pocoo.org/2026/1/31/pi/]

---

## Architectural Lessons for Our System

### 1. Pre-Compaction Memory Flush (HIGH VALUE)
OpenClaw's silent agentic turn before compaction is the single most valuable idea. Our PreCompact hook cannot inject content — it's side-effect only. Options:
- **Prompt hook on PostToolUse**: inject "save state" reminders when token count is high (requires token counting, which we don't have access to)
- **UserPromptSubmit hook**: monitor for compaction signals and inject memory-save directives
- **Proactive approach**: Already in our instructions ("proactively save progress to `.claude/checkpoint.md`"), but instructions alone are unreliable (our own constitution says "instructions alone = 0% reliable")

### 2. Daily Memory Logs (MEDIUM VALUE)
`memory/YYYY-MM-DD.md` as append-only daily logs alongside curated `MEMORY.md` is a good pattern. We currently have only MEMORY.md. Daily logs would capture session-specific context that doesn't warrant long-term memory but is useful for next-day continuity.

### 3. Temporal Decay for Memory Search (LOW VALUE for now)
Only relevant once we have vector search over memory. If we ever build this, the exponential decay with evergreen file exemptions is a well-designed approach.

### 4. Heartbeat Transcript Pruning (MEDIUM VALUE)
When a heartbeat returns "nothing to report," OpenClaw truncates the transcript back to pre-heartbeat size. This prevents zero-information exchanges from polluting context. We could apply similar thinking to our hook logs — don't log when nothing happened.

### 5. Skills Gating (MEDIUM VALUE)
OpenClaw's load-time gating (check if binary/env exists before injecting skill into prompt) is worth adopting. Our skills always load regardless of whether their tools are available, wasting prompt tokens.

### 6. Queue Coalescing (LOW VALUE for CLI)
Only relevant if we build a multi-channel gateway. The `collect` mode (coalesce multiple messages into one turn) is elegant.

### 7. NO_REPLY Token (MEDIUM VALUE)
A convention for silent agentic turns where the model does work but shouldn't produce user-visible output. Useful for background maintenance tasks. We don't have this concept.

---

## What's Uncertain

1. **QMD backend performance**: The experimental QMD backend (local BM25+vectors+reranking) is a compelling alternative to our separate selve/emb setup. No benchmarks found comparing it to cloud embeddings.

2. **Heartbeat cost**: Running full agent turns every 30m is expensive. The docs acknowledge this ("shorter intervals burn more tokens") but no cost data was found.

3. **Session tree implementation**: Pi's session branching is referenced in Armin's blog but I didn't read the Pi source code for the actual tree implementation. The architecture sounds similar to Claude Code's conversation branching but with explicit summarization on branch merge.

4. **Hook blocking future**: OpenClaw's hooks currently cannot block operations. Their "future events" list suggests they want `session:start/end` and `agent:error` but doesn't mention adding blocking capability. This may be intentional (gateway philosophy vs CLI philosophy).

---

## Sources Saved

All primary sources accessed via raw GitHub URLs and Exa crawling. Key files:
- `memory` (archived) — full memory architecture
- `heartbeat` (archived) — heartbeat configuration
- `queue` (archived) — command queue design
- `hooks` (archived) — hook system
- `skills` (archived) — skills system
- `session-management-compaction` (archived) — session/compaction deep dive
- `src/auto-reply/reply/memory-flush.ts` — memory flush implementation
- `src/infra/heartbeat-runner.ts` — heartbeat runner implementation (~700 LOC)
- `src/process/command-queue.ts` — command queue implementation
- `src/process/lanes.ts` — lane definitions
- Templates: SOUL.md, IDENTITY.md, BOOTSTRAP.md, HEARTBEAT.md, SOUL.dev.md
- Armin Ronacher's blog post on Pi philosophy

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: f8a51415719e

title: OpenClaw Architecture Deep Dive — Research Memo

end-knowledge-index -->
