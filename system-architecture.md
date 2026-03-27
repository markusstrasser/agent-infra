# System Architecture

How the agent infrastructure works, end to end. One doc, no indirection.

---

## 1. What This Is

A personal agent infrastructure spanning 5 core projects (meta, intel, selve, genomics, skills) plus ~60 auxiliary repos. Claude Code is the primary agent runtime. The system adds layers on top: hooks for guardrails, skills for capabilities, MCP servers for tool access, an orchestrator for automation, and measurement scripts for self-improvement.

The goal: agents get more autonomous over time, measured by declining supervision.

---

## 2. Layer Model

Six layers, loaded bottom-up into every Claude Code session. Each layer is a different file-system location with different scope and governance.

```
┌─────────────────────────────────────────────────────────┐
│  6. MCP Servers          (external tool access)         │
├─────────────────────────────────────────────────────────┤
│  5. Orchestrator         (cron automation)              │
├─────────────────────────────────────────────────────────┤
│  4. Project Config       (per-repo rules + hooks)       │
├─────────────────────────────────────────────────────────┤
│  3. Skills               (shared capabilities)          │
├─────────────────────────────────────────────────────────┤
│  2. Shared Hooks         (cross-project guardrails)     │
├─────────────────────────────────────────────────────────┤
│  1. Global Config        (universal rules + settings)   │
└─────────────────────────────────────────────────────────┘
```

### Layer 1: Global Config (`~/.claude/`)

Loaded in every project, every session. The foundation.

| File/Dir | What it does |
|----------|-------------|
| `CLAUDE.md` | Universal rules: git workflow, Python/uv conventions, pushback protocol, reasoning routing, subagent policy, context management, execution policy. ~400 lines. |
| `settings.json` | Global hooks (all 12 events), status line, enabled plugins, env vars. The hook wiring diagram. |
| `rules/` | Auto-loaded rule files. Currently: `research-tool-gotchas.md`, `research-api-routing.md`. |
| `hooks/` | Hook scripts owned by global config (8 scripts): `session-init.sh`, `spinning-detector.sh`, `stop-debrief.sh`, `stop-notify.sh`, `tab-color.sh`, `tool-tracker.sh`, `pretool-modal-cost-guard.sh`, `pretool-shared-infra-guard.sh`. |
| `statusline.sh` | Terminal status bar: model, branch, cost, context usage. |
| `active-agents.json` | Cross-session awareness — which Claude instances are running where. Written by `session-init.sh`. |
| `mcp.json` | User-scope MCP servers (loaded in all projects). |
| `projects/` | Per-project memory directories. Each has `MEMORY.md` (index) + topic files. Auto-loaded by Claude Code's memory system. |

### Layer 2: Shared Hooks (`~/Projects/skills/hooks/`)

~50 shell scripts. Referenced by path in `~/.claude/settings.json` (global) and per-project `settings.json` files. Shared across all projects — change once, affects everywhere.

**Categories:**
- **PreToolUse blockers**: `bash-loop-guard`, `llmx-guard`, `cost-guard`, `ast-precommit`, `commit-check`, `search-burst`, `consensus-search`, `subagent-gate`, `source-remind`, `regression-dag-gate`, `goal-drift`, `companion-remind`
- **PostToolUse checks**: `bash-failure-loop`, `review-check`, `verify-before-expand`, `research-reformat`, `source-check`, `frontier-timeliness`, `l3-telemetry`, `propagate-check`
- **Lifecycle**: `precompact-log`, `postcompact-verify`, `sessionend-log`, `sessionend-overview-trigger`, `sessionend-index-sessions`, `subagent-start-log`, `subagent-epistemic-gate`, `userprompt-context-warn`, `posttool-failure-log`
- **Stop hooks**: `plan-status`, `verify-plan`, `uncommitted-warn`

**Convention**: Scripts exit 0 (pass), exit 2 (block with message), or write to stderr (advisory). All fail open unless on the explicit fail-closed list.

### Layer 3: Skills (`~/Projects/skills/`)

35 skills, each a `SKILL.md` file with optional `references/` directory. Invoked via `/skill-name` in conversation. Symlinked into per-project `.claude/skills/` dirs.

**Current inventory** (grouped):
- **Reasoning**: `causal-check`, `causal-dag`, `causal-robustness`, `competing-hypotheses`, `brainstorm`
- **Research**: `researcher`, `epistemics`, `knowledge-diff`, `investigate`, `data-acquisition`
- **Review**: `model-review`, `session-analyst`, `design-review`, `supervision-audit`, `de-slop`, `source-grading`, `code-review`
- **Writing**: `coedit`, `entity-management`
- **Infrastructure**: `claude-api`, `modal`, `llmx-guide`, `debug-mcp-servers`, `model-guide`, `google-workspace`, `browse`, `qa`
- **Meta**: `retro`, `suggest-skill`, `skill-authoring`, `agent-pliability`, `constitution`, `project-upgrade`, `dispatch-research`
- **Archived**: `architect` (in `archive/`)

Skills are loaded on-demand when invoked. Their descriptions appear in the system prompt skill list, consuming ~2K tokens total.

### Layer 4: Project Config (per-repo `.claude/`)

Each project has its own `.claude/` directory:

```
.claude/
├── CLAUDE.md          # Project-specific rules (checked into git)
├── settings.json      # Project-specific hooks (checked in)
├── settings.local.json # Local overrides (gitignored)
├── rules/             # Auto-loaded rule files (checked in)
├── skills/            # Symlinks to ~/Projects/skills/ entries
├── overviews/         # Auto-generated codebase summaries (source-overview.md, tooling-overview.md)
├── plans/             # Ephemeral work plans (gitignored)
├── checkpoint.md      # Compaction handoff doc
├── current-session-id # Written by session-init hook
├── overview.conf      # Overview generation config
└── overview-marker    # Staleness tracking for overviews
```

**Core projects and their focus:**

| Project | Purpose | Unique config |
|---------|---------|---------------|
| `meta` | Agent infrastructure, self-improvement | Constitution, orchestrator, measurement scripts, 64 research memos |
| `intel` | Investment research | DuckDB MCP, intelligence MCP, entity management, prediction tracking |
| `selve` | Personal knowledge | Selve MCP, runbooks, personal data rules |
| `genomics` | Genomics pipeline | Cache dir, prompts, runbooks, bioinformatics tools |
| `skills` | Shared skill library | Skill validation hooks |

### Layer 5: Orchestrator (`scripts/orchestrator.py`)

Cron-driven task runner. Submits and executes tasks via `claude -p` (LLM) or `subprocess` (deterministic scripts).

```
launchd (every 15 min)
  → orchestrator.py tick
    → picks highest-priority pending task from SQLite queue
    → executes via claude -p (with --allowedTools, project context)
    → logs result, updates status
    → checks scheduled_runs for auto-submitted pipelines
```

**Pipeline templates** (`pipelines/*.json`): Define multi-step workflows with variable substitution, approval gates, and scheduling.

**Scheduling agents** (launchd):
- `com.meta.orchestrator.plist` — tick every 15 min
- `com.meta.session-retro-daily.plist` — session-retro at 22:00
- `com.meta.hook-roi-daily.plist` — hook ROI report at 22:30
- `com.meta.propose-work-daily.plist` — morning brief at 05:00

**Constraints**: $25/day cost cap, `fcntl.flock` prevents concurrent ticks, 600s stall timeout, max 3 concurrent tasks per pipeline.

### Layer 6: MCP Servers

External tool access. Configured per-project in `.mcp.json` (project-scope) and `~/.claude/mcp.json` (user-scope).

**User-scope** (available everywhere via `~/.claude/mcp.json` or system config):
- `exa` — Neural web search, entity enrichment, deep research
- `research` (research-mcp) — S2 paper discovery, full-text fetch, evidence preparation, citation traversal
- `brave-search` — Independent web search index
- `perplexity` — Grounded LLM search/reasoning
- `firecrawl` — Web scraping and extraction
- `context7` — Library documentation lookup
- `meta-knowledge` — Section-based search over meta's .md files
- `repo-tools` — Tiered code navigation (summary, outline, callgraph, imports, deps, changes)
- `claude-in-chrome` — Browser automation
- `paper-search` — arXiv/PubMed/bioRxiv search

**Project-scope** (per-repo `.mcp.json`):
- `intel`: DuckDB, intelligence MCP, selve MCP, FMP (financial data)
- `selve`: Selve MCP
- `genomics`: (none active)

---

## 3. Information Flow

### Session Startup

```
1. Claude Code launches
2. Loads ~/.claude/CLAUDE.md                    (global rules)
3. Loads ~/.claude/rules/*.md                   (global rule files)
4. Loads {project}/CLAUDE.md                    (project rules)
5. Loads {project}/.claude/rules/*.md           (project rule files)
6. Loads ~/.claude/projects/{path}/memory/MEMORY.md  (auto-memory)
7. Starts MCP servers from .mcp.json + ~/.claude/mcp.json
8. Fires SessionStart hook → session-init.sh:
   - Saves session ID to .claude/current-session-id
   - Snapshots git status baseline
   - Registers in active-agents.json
   - Hashes loaded skills for provenance
   - Scans for incomplete plans → injects as additionalContext
   - Injects codebase overview INDEX blocks as additionalContext
9. Loads skill descriptions into system prompt (~2K tokens)
10. Loads deferred tool list (MCP tools available via ToolSearch)
```

**Total context budget at session start** (approximate):
- Global CLAUDE.md: ~8K tokens
- Global rules: ~2K tokens
- Project CLAUDE.md: ~8-15K tokens (meta is largest)
- Project rules: ~3-5K tokens
- MEMORY.md + topic files referenced: ~3K tokens
- Skill descriptions: ~2K tokens
- Deferred tool list: ~2K tokens
- Overview additionalContext: ~2K tokens
- **Total before first user message: ~30-40K tokens**

### During Session

```
User message
  → UserPromptSubmit hook (context-warn, tab-color)
  → Model generates response
  → For each tool call:
      → PreToolUse hooks (matchers filter by tool name)
        - May BLOCK (exit 2) or ADVISE (stderr)
      → Tool executes
      → PostToolUse hooks
        - May warn, log, or inject guidance
  → When model stops:
      → Stop hooks (plan-status, verify-plan, uncommitted-warn, debrief, notify)
```

### Session End / Compaction

```
Context approaching limit:
  → PreCompact hook (logs nuance signals)
  → Compaction summarizes conversation
  → PostCompact hook (verifies invariants survived)
  → checkpoint.md written for handoff

Session ends:
  → SessionEnd hooks:
    - sessionend-log.sh (receipt to session-receipts.jsonl)
    - sessionend-overview-trigger.sh (marks overviews for refresh)
    - sessionend-index-sessions.sh (indexes into sessions.db)
```

---

## 4. Cross-Project Architecture

```
~/Projects/
├── justfile              # Workspace task runner (all-health, push-all, todos)
├── meta/                 # Agent infra, orchestrator, measurement, research
├── intel/                # Investment research
├── selve/                # Personal knowledge
├── genomics/             # Genomics pipeline
├── skills/               # Shared skill library
│   ├── */SKILL.md        # 35 skills
│   └── hooks/            # ~50 shared hook scripts
├── research-mcp/           # Research paper MCP server
├── llmx/                 # Multi-model CLI transport (editable-installed)
└── best/                 # OSS reference repos (auto-synced daily)
```

**Shared resources flow downward from meta and skills:**
- `meta` owns: constitution, hooks governance, orchestrator, measurement, research
- `skills/` owns: capabilities (skills) and guardrails (hooks)
- `research-mcp` owns: research tool infrastructure
- `llmx` owns: multi-model dispatch

**Data stores:**
- `~/.claude/orchestrator.db` — Task queue
- `~/.claude/runlogs.db` — Cross-vendor session transcripts
- `~/.claude/session-receipts.jsonl` — Session cost/duration log
- `~/.claude/hook-triggers.jsonl` — Hook fire/block telemetry
- `~/.claude/subagent-log.jsonl` — Subagent spawn/result log
- `~/.claude/tool-log.jsonl` — Tool call sequence tracking

---

## 5. Self-Improvement Loop

The core feedback cycle that makes the system get better:

```
Sessions happen (human + agent work)
  ↓
session-retro pipeline (daily 22:00)
  → session-shape.py         # Zero-cost structural anomaly detector (pre-filter)
  → session-analyst skill    # Deep behavioral analysis (dispatches to Gemini)
  → improvement-log.md       # Structured findings appended
  ↓
finding-triage.py
  → SQLite staging DB        # Fingerprinting + dedup
  → 2+ recurrences?          # Auto-promote to actionable
  ↓
Implementation
  → Hook, rule, skill, or code change
  → Commit with evidence trailer
  ↓
fix-verify.py
  → Runs detection queries against recent sessions
  → Confirms fix is holding
```

**Measurement scripts** (epistemic instrumentation):
- `supervision-kpi.py` — Supervision Load Index (north star metric)
- `calibration-canary.py` — Answer-confidence calibration
- `pushback-index.py` — Sycophancy detection
- `trace-faithfulness.py` — Agent claims vs actual tool calls
- `safe-lite-eval.py` — Factual precision via Exa verification
- `epistemic-lint.py` — Unsourced claim detection
- `fold-detector.py` — Behavioral sycophancy (position fold rate)

---

## 6. The Memory Problem

### Why Claude Code "likes" MEMORY.md

The user observes that Claude Code over-relies on MEMORY.md — referencing it when it should read the actual codebase. This is **not** context rot in the traditional sense. It's **attention capture** caused by three reinforcing mechanisms:

**1. Positional privilege.** MEMORY.md content is injected into the system prompt, near the top of context. Research shows ~75% accuracy for start-positioned information vs ~55% for middle (Liu et al., Lost-in-the-Middle). MEMORY.md gets the best attention real estate in every session. It's always "in mind" while code files require active retrieval via tool calls.

**2. Instructional reinforcement.** The auto-memory system prompt explicitly tells the model to:
- Read memories when they seem relevant
- Save new memories when learning about the user/project
- Access memory when the user asks to recall something

This creates a behavioral loop: the model is *told* to use memory, *rewarded* by it being easy to access (no tool call needed), and *penalized* for ignoring it (might miss relevant context). The instructions make memory-checking a default behavior rather than a last resort.

**3. Zero-cost access vs tool-call cost.** Reading MEMORY.md content requires zero tool calls — it's already in context. Reading actual code requires Read/Grep tool calls, each of which:
- Costs latency
- Costs tokens (tool call overhead)
- Might return more information than needed
- Requires the model to decide *what* to read

The rational lazy strategy is: check what's already in context first, and only go to the codebase if needed. This is correct behavior in principle but creates staleness risk — MEMORY.md reflects when it was written, not the current state.

### What this means practically

- MEMORY.md assertions about file paths, function names, or code state may be stale
- The model may "remember" something exists without verifying it still does
- Instructions in MEMORY.md may contradict what the codebase actually does
- The model treats MEMORY.md as ground truth rather than as a cache that needs validation

### What would fix it

The user's existing `feedback_memory_skepticism.md` note and CLAUDE.md rule ("memory records what was true when it was written... trust what you observe now") are the right direction. The fundamental tension is:

1. **Can't remove MEMORY.md** — it carries genuinely useful cross-session context
2. **Can't stop it from being privileged** — it's in the system prompt by design
3. **Can mitigate** via:
   - Keeping MEMORY.md minimal (index of pointers, not content)
   - Moving factual claims to `.claude/rules/` files (which are also auto-loaded but positioned differently)
   - Adding a verification norm: "if MEMORY.md names a specific file/function/flag, grep for it before acting on it" (already in global CLAUDE.md)
   - Periodic memory pruning: delete entries that are now derivable from code

The honest answer: MEMORY.md will always have some attention advantage due to position. The system already has the right mitigations in principle. The gap is enforcement — there's no hook that detects "agent cited memory without verifying current state." That would require semantic judgment (unhookable), making cross-model review the only real check.

---

## 7. Where to Find Things

| Question | Look here |
|----------|-----------|
| Why does a hook fire? | `~/.claude/settings.json` → hook path → read the script |
| What rules load for project X? | `{project}/CLAUDE.md` + `{project}/.claude/rules/` + `~/.claude/CLAUDE.md` + `~/.claude/rules/` |
| What MCP tools are available? | `{project}/.mcp.json` + `~/.claude/mcp.json` + deferred tool list in session |
| What skills exist? | `~/Projects/skills/*/SKILL.md` |
| What the orchestrator is doing? | `orchestrator.py status`, `orchestrator.py log --today` |
| Session history? | `runlog.py recent`, `runlog.py query <named-query>` |
| Hook telemetry? | `hook-roi.py`, `hook-telemetry-report.py` |
| What was decided and why? | `meta/decisions/*.md` |
| Research on topic X? | `meta/research/` (index in `.claude/rules/research-index.md`) |
| Cross-project health? | `just all-health` from `~/Projects/` |
