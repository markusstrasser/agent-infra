# Autonomous Agent Architecture for Long-Running Intelligence Work

**Date:** 2026-02-27
**Context:** Design for a single Claude Code agent that can work productively for an entire day across the `intel` (adversarial intelligence) and `genomics` (WGS pipeline/health) projects, with inspectable evolution, no mode collapse, and continuous self-improvement.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [Architecture Overview](#2-architecture-overview)
3. [The Seven Loops](#3-the-seven-loops)
4. [Orchestrator Design](#4-orchestrator-design)
5. [Anti-Mode-Collapse Mechanisms](#5-anti-mode-collapse-mechanisms)
6. [Progress Logging & Inspectability](#6-progress-logging--inspectability)
7. [Self-Improvement Loop](#7-self-improvement-loop)
8. [Claude Code Technical Surface](#8-claude-code-technical-surface)
9. [Known Failure Modes & Mitigations](#9-known-failure-modes--mitigations)
10. [Implementation Plan](#10-implementation-plan)
11. [Sources](#11-sources)

---

## 1. The Problem

Current workflow: human starts Claude Code session, manually selects what to work on, drives investigation, spawns ad-hoc subagents, updates memory, closes session. Repeat N times per day across multiple projects.

**What's lost:**
- No systematic rotation across work types (analysis gets all attention, tooling starves)
- No forcing function for entity staleness — human has to remember to check
- Multi-model review is manual (copy analysis → llm_check → read output → update memory)
- Context dies between sessions — MEMORY.md preserves facts but not momentum
- No log of "what was attempted, what worked, what was abandoned" — only final commits

**What we want:**
- Agent runs for 8+ hours with bounded cost ($20-50/day budget)
- Rotates across work types without human steering
- Maintains inspectable log reviewable in 5 minutes
- Improves its own tooling, knowledge base, and detection capability
- Handles both `intel` (investments, fraud) and `genomics` (WGS pipeline, health optimization)
- Human reviews output once/day, approves/rejects, provides new orientation

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  ORCHESTRATOR                     │
│  (Python script using claude-agent-sdk)           │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Task     │  │ Budget   │  │ Diversity     │   │
│  │ Queue    │  │ Tracker  │  │ Monitor       │   │
│  │ (DAG)    │  │ ($/ turn)│  │ (type hist)   │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Session  │  │ Stuck    │  │ Progress      │   │
│  │ Manager  │  │ Detector │  │ Logger        │   │
│  │ (chain)  │  │ (circuit)│  │ (JSONL+md)    │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
│              Dispatches via:                       │
│         claude -p "..." --max-turns N             │
│              or claude-agent-sdk                   │
└─────────────────┬───────────────────┬─────────────┘
                  │                   │
    ┌─────────────▼──────┐  ┌────────▼──────────┐
    │   intel project    │  │   self project     │
    │   (investments,    │  │   (genomics,       │
    │    fraud, entities)│  │    health, n=1)    │
    └────────────────────┘  └───────────────────┘
```

**Key design choice:** The orchestrator is a **Python script** (not a Claude Code session itself), because:
1. Claude sessions have context limits; the orchestrator needs to run all day
2. Budget/diversity/stuck detection need deterministic logic, not LLM reasoning
3. Session chaining via `--resume` lets each task get fresh context
4. External process can monitor Claude for freezes/hangs (known failure mode)

---

## 3. The Seven Loops

These are the recurring workflows identified from 40+ intel project sessions. Each has clear inputs, outputs, and a mechanism by which the repo gets better.

### Loop 1: DATA ACQUISITION (automated, daily cron)
- **Trigger:** Scheduled (daily_update.sh)
- **What:** Download prices, signals, filings → rebuild views → healthcheck → signal scanner → paper ledger
- **Output:** Fresh data, alerts CSV, portfolio mark
- **Improvement mechanism:** New data sources added over time; each enriches all downstream queries
- **Automation status:** FULLY AUTOMATED (cron)

### Loop 2: ENTITY INTELLIGENCE (event-triggered)
- **Trigger:** Staleness detector fires, 8-K monitor flags refresh, signal scanner alert
- **What:** Pull new SEC filings/trades/8-Ks → update entity file → source-grade → commit
- **Output:** Updated entity dossier with coverage dates advanced
- **Improvement mechanism:** Entity files accumulate knowledge; git log = audit trail
- **Automation status:** MANUAL — highest-value automation target

### Loop 3: INVESTIGATION (human-oriented)
- **Trigger:** Phase 1 screening surfaces anomaly, or human orients
- **What:** Hypothesis-driven data exploration → ACH for leads >$10M → findings to entity file
- **Output:** Case analysis, mechanism classification, updated priors
- **Improvement mechanism:** Case library grows, detection hierarchy refines
- **Automation status:** SEMI-MANUAL — Phase 1 screening automatable, Phase 2 needs human

### Loop 4: MULTI-MODEL REVIEW (quality gate)
- **Trigger:** Any analysis produced (entity update, thesis check, investigation)
- **What:** Send to Gemini (pattern) + GPT-5.2 (math) with structured questions → synthesize → verify
- **Output:** Validated/corrected findings, MEMORY.md updates
- **Improvement mechanism:** Error-correction ledger compounds; each catch becomes permanent guardrail
- **Automation status:** MANUAL — second-highest automation target

### Loop 5: INVESTMENT DECISION (thesis → capital)
- **Trigger:** Signal scanner high-LLR alert, or scheduled position review
- **What:** Pre-mortem → thesis-check → probability calibration → paper ledger
- **Output:** Trade execution, prediction logged, score updated
- **Improvement mechanism:** Prediction tracker accumulates scored outcomes, base rates sharpen
- **Automation status:** SEMI-MANUAL — signal→thesis-check automatable, decision needs human

### Loop 6: METHODOLOGY IMPROVEMENT (meta-learning)
- **Trigger:** Error discovered, or scheduled academic audit
- **What:** Document error → update scoring/tools → academic literature check → encode in rules
- **Output:** Updated MEMORY.md, scoring.py, rules/ files, analytical_reasoning.md
- **Improvement mechanism:** Each mistake becomes permanent guardrail
- **Automation status:** MANUAL — but "wrap-up" skill pattern could partially automate

### Loop 7: INFRASTRUCTURE HARDENING (plumbing)
- **Trigger:** New dataset needed, tool gap identified, healthcheck failure
- **What:** Write script → add views → update healthcheck → add rule → update docs
- **Output:** New tool, expanded view catalog, tighter guardrails
- **Improvement mechanism:** All future sessions become faster
- **Automation status:** MANUAL

### Cross-Project Application

The same 7 loops apply to the `genomics` project (`~/Projects/genomics/`):
- **Loop 1:** Download new ClinVar releases, PharmGKB updates, 23andMe reprocessing
- **Loop 2:** Gene/variant entity files with coverage dates (last ClinVar check, last literature review)
- **Loop 3:** "Why do I have this phenotype?" as investigation; ACH for competing genetic explanations
- **Loop 4:** Multi-model review of supplement protocols, drug interaction claims
- **Loop 5:** N=1 experiment design → execution → measurement → Bayesian update
- **Loop 6:** Pharmacogenomic lessons (e.g., "CYP2D6 poor metabolizer changes dosing for X")
- **Loop 7:** New assay parser, new data source integration

---

## 4. Orchestrator Design

### 4.1 Task Queue (DAG-based)

Tasks have types, priorities, dependencies, and time estimates:

```python
@dataclass
class Task:
    id: str
    type: TaskType  # ENTITY_REFRESH | THESIS_CHECK | MULTI_MODEL_REVIEW |
                    # INVESTIGATION | METHODOLOGY | INFRASTRUCTURE | DATA_ACQUISITION
    project: str    # "intel" | "self"
    priority: float # 0-1, sigmoid-sampled for stochastic selection
    max_turns: int  # Claude turn budget
    max_cost: float # Dollar budget
    prompt: str     # What to send to Claude
    depends_on: list[str]  # Task IDs that must complete first
    context: dict   # Files to read, session to resume, etc.
    created_at: datetime
    completed_at: datetime | None
    result: str | None  # Summary of what happened
    status: str     # PENDING | RUNNING | COMPLETED | FAILED | SKIPPED
```

### 4.2 Task Generation (Daily Briefing)

At start of day, the orchestrator generates the task queue:

```python
def generate_daily_tasks(project: str) -> list[Task]:
    tasks = []

    # 1. Staleness-driven entity refreshes
    stale = run_staleness_check(project)
    for entity, stale_classes in stale.items():
        tasks.append(Task(
            type=ENTITY_REFRESH,
            priority=staleness_urgency(entity, stale_classes),
            prompt=f"Update entity file for {entity}. Stale: {stale_classes}. "
                   f"Pull latest data, update coverage dates, commit.",
            max_turns=30,
            max_cost=2.0,
        ))

    # 2. Signal-driven thesis checks
    alerts = read_latest_signals(project)
    for alert in alerts.high_llr():
        tasks.append(Task(
            type=THESIS_CHECK,
            priority=alert.posterior,
            prompt=f"/thesis-check {alert.ticker}",
            max_turns=50,
            max_cost=3.0,
            depends_on=[],  # Can run independently
        ))

    # 3. Pending multi-model reviews
    unreviewed = find_unreviewed_analyses(project)
    for doc in unreviewed:
        tasks.append(Task(
            type=MULTI_MODEL_REVIEW,
            priority=0.7,  # Always medium-high
            prompt=f"Run multi-model review on {doc}. "
                   f"Gemini pattern + GPT-5.2 math. Structured questions. "
                   f"Update MEMORY.md with validated findings.",
            max_turns=20,
            max_cost=5.0,
        ))

    # 4. Scheduled reviews (quarterly thesis checks, monthly portfolio review)
    tasks += scheduled_reviews(project)

    # 5. Infrastructure tasks from healthcheck failures
    health = run_healthcheck(project)
    for failure in health.failures:
        tasks.append(Task(
            type=INFRASTRUCTURE,
            priority=0.5,
            prompt=f"Fix healthcheck failure: {failure}",
            max_turns=20,
            max_cost=1.0,
        ))

    # 6. Self-improvement task (always present, lowest priority)
    tasks.append(Task(
        type=METHODOLOGY,
        priority=0.3,
        prompt="Review recent session logs. Identify any recurring errors or "
               "patterns. Update MEMORY.md, rules/, or scoring.py if warranted. "
               "Check academic literature for new methods relevant to our work.",
        max_turns=30,
        max_cost=3.0,
    ))

    return tasks
```

### 4.3 Task Selection (Sigmoid-Sampled, Diversity-Aware)

**Not** a simple priority sort. Three mechanisms prevent mode collapse:

```python
def select_next_task(queue: list[Task], history: list[Task]) -> Task:
    eligible = [t for t in queue if t.status == PENDING and deps_met(t)]
    if not eligible:
        return None

    # 1. Sigmoid-transform priorities (stochastic, not deterministic)
    weights = [sigmoid(t.priority * 5 - 2.5) for t in eligible]

    # 2. Diversity penalty: downweight overrepresented task types
    type_counts = Counter(t.type for t in history[-10:])
    for i, task in enumerate(eligible):
        if type_counts[task.type] > 3:  # >30% of recent work
            weights[i] *= 0.3  # Heavy penalty
        elif type_counts[task.type] > 2:
            weights[i] *= 0.6

    # 3. Time-since-last penalty: boost types not seen recently
    for i, task in enumerate(eligible):
        last_of_type = max(
            (h.completed_at for h in history if h.type == task.type),
            default=datetime.min
        )
        hours_since = (datetime.now() - last_of_type).total_seconds() / 3600
        weights[i] *= min(1 + hours_since * 0.1, 2.0)  # Up to 2x boost

    # 4. Weighted random selection
    return random.choices(eligible, weights=weights, k=1)[0]
```

### 4.4 Session Execution

Each task gets a fresh Claude session with bounded resources:

```python
async def execute_task(task: Task) -> TaskResult:
    task.status = RUNNING
    log_task_start(task)

    try:
        result_text = ""
        session_id = None

        async for message in query(
            prompt=task.prompt,
            options=ClaudeAgentOptions(
                allowed_tools=tools_for_type(task.type),
                permission_mode="acceptEdits",
                max_turns=task.max_turns,
                cwd=project_dir(task.project),
                system_prompt=load_system_prompt(task.project),
                # Load project CLAUDE.md, skills, rules
                setting_sources=["project"],
            ),
        ):
            if hasattr(message, "subtype") and message.subtype == "init":
                session_id = message.session_id
            if hasattr(message, "result"):
                result_text = message.result

        task.status = COMPLETED
        task.result = result_text
        task.session_id = session_id

    except Exception as e:
        task.status = FAILED
        task.result = str(e)

    log_task_end(task)
    return task
```

### 4.5 Budget Tracking

```python
@dataclass
class DayBudget:
    max_usd: float = 30.0
    max_turns_total: int = 500
    spent_usd: float = 0.0
    turns_used: int = 0

    def can_afford(self, task: Task) -> bool:
        return (self.spent_usd + task.max_cost <= self.max_usd and
                self.turns_used + task.max_turns <= self.max_turns_total)
```

---

## 5. Anti-Mode-Collapse Mechanisms

Mode collapse in this context means: the agent does the same type of work repeatedly, ignoring other valuable work. Or it gets stuck repeating the same approach to a problem.

### 5.1 Diversity Monitor (Type Histogram)

Track work type distribution over a rolling window. If any type exceeds 40% of recent work, penalize selection probability. If any type drops below 10%, boost it.

Source: Adapted from CORPGEN's hierarchical planning (Microsoft Research, Feb 2026, [arXiv:2602.14229](https://arxiv.org/abs/2602.14229)). CORPGEN found that under 46-task load, hierarchical planning with diversity constraints achieved 15.2% completion vs 4.3% baseline.

### 5.2 Time-Boxing

Each task type gets a maximum time budget per session:
- ENTITY_REFRESH: 30 min (--max-turns 30)
- THESIS_CHECK: 45 min (--max-turns 50)
- MULTI_MODEL_REVIEW: 20 min (--max-turns 20)
- INVESTIGATION: 60 min (--max-turns 60)
- METHODOLOGY: 30 min (--max-turns 30)
- INFRASTRUCTURE: 20 min (--max-turns 20)

When a task hits its turn limit, it's marked INCOMPLETE with a summary of progress, and a continuation task is queued (but not necessarily next).

Source: Ralph Wiggum pattern — `--max-iterations` caps force exit and reassessment. ([beuke.org](https://beuke.org/ralph-wiggum-loop/))

### 5.3 Sigmoid Probability Sampling

Instead of always picking the highest-priority task, transform priorities through a sigmoid and sample randomly. This injects exploration without abandoning priorities entirely.

Source: Gemini game theory analysis from our own `analysis/llm_checks/` — fixed thresholds create Nash equilibria; sigmoid probability sampling prevents gaming.

### 5.4 Mandatory Rotation Rule

After 3 consecutive tasks of the same type, the next task MUST be a different type, regardless of priority. This is a hard constraint, not a soft penalty.

### 5.5 "Surprise Me" Tasks

10% of task slots reserved for exploration: pick a random entity, random dataset join, random academic paper search. These seed new investigations that wouldn't emerge from priority queues alone.

Source: DGPO (Diversity-Guided Policy Optimization, AAAI 2024). Use diversity objective alongside task reward to discover multiple solution strategies.

---

## 6. Progress Logging & Inspectability

### 6.1 Three-Layer Log Architecture

Adapted from AgentTrace ([arXiv:2602.10133](https://arxiv.org/html/2602.10133v1)) and Ian Paterson's memory architecture.

**Layer 1: JSONL Event Stream** (machine-readable)
```jsonl
{"ts": "2026-02-27T09:00:00Z", "event": "task_start", "task_id": "t001", "type": "ENTITY_REFRESH", "entity": "HIMS", "project": "intel"}
{"ts": "2026-02-27T09:02:15Z", "event": "tool_call", "task_id": "t001", "tool": "DuckDB", "query": "SELECT ... FROM sec_form4 WHERE ticker='HIMS'"}
{"ts": "2026-02-27T09:15:00Z", "event": "task_end", "task_id": "t001", "status": "COMPLETED", "cost_usd": 0.85, "turns": 12, "summary": "Updated HIMS: 3 insider sells in Feb, coverage extended to 2026-02-27"}
{"ts": "2026-02-27T09:15:30Z", "event": "task_start", "task_id": "t002", "type": "MULTI_MODEL_REVIEW", "target": "analysis/investments/thesis_checks/hims_2026-02-20.md"}
```

**Layer 2: Daily Markdown Summary** (human-reviewable in 5 minutes)
```markdown
# Agent Log: 2026-02-27

## Summary
- 14 tasks completed, 2 failed, 3 skipped (budget)
- $18.40 spent (of $30 budget)
- 312 turns used (of 500 budget)

## Type Distribution
| Type | Count | % | Target |
|------|-------|---|--------|
| ENTITY_REFRESH | 5 | 36% | 20-40% |
| THESIS_CHECK | 3 | 21% | 15-25% |
| MULTI_MODEL_REVIEW | 2 | 14% | 10-20% |
| INVESTIGATION | 1 | 7% | 5-15% |
| METHODOLOGY | 2 | 14% | 10-20% |
| INFRASTRUCTURE | 1 | 7% | 5-15% |

## Key Findings
1. **HIMS insider selling accelerated** — 3 sells in Feb, $2.4M total [DATA]
2. **scoring.py EB shrinkage still not implemented** — flagged 3 sessions ago
3. **New FAERS view broken** — missing column `reporter_country`, healthcheck failing

## Commits Made
- `abc1234` update: HIMS — Feb insider sells, coverage through 2026-02-27
- `def5678` fix(views): add reporter_country to faers_demo view

## Failed Tasks
- t007 INVESTIGATION FCX copper: hit max turns, queued continuation
- t011 MULTI_MODEL_REVIEW: Gemini API timeout (rate limit)

## Human Review Needed
- [ ] HIMS insider selling: reduce position? (3 sells, no buys)
- [ ] FCX investigation incomplete — should we continue?
- [ ] scoring.py EB shrinkage: implement or defer?
```

**Layer 3: Git History** (permanent record)
Every entity update, tool fix, and analysis gets committed with descriptive messages. `git log --oneline` is the timeline. This already exists in intel project workflow.

### 6.2 Daily Briefing Email/File

At end of day, generate a 1-page summary:
- What was accomplished (commits, entity updates, reviews)
- What was attempted but failed (with reasons)
- What needs human decision (position changes, investigation directions)
- What's queued for tomorrow
- Budget spent vs planned
- Diversity score (entropy of type distribution)

Source: Agents Arcade observability guide — "silent degradation is the real threat" — track cost surface, latency amplifiers, asymmetric failures.

---

## 7. Self-Improvement Loop

### 7.1 The "Wrap-Up" Pattern

At end of each task (not just end of day), the orchestrator appends a mini-review:

```python
WRAP_UP_PROMPT = """
Before finishing, briefly note:
1. Did this task reveal any error in our tools, scoring, or knowledge base?
2. Is there a recurring pattern that should become a rule in .claude/rules/?
3. Is there a lesson that should update MEMORY.md?
4. Did any assumption turn out wrong?

If yes to any: make the update now. If no: say "No meta-updates needed."
"""
```

Source: Reddit "wrap-up" skill pattern — "every mistake becomes a rule." ([r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1r89084/selfimprovement_loop_my_favorite_claude_code_skill/))

### 7.2 Methodology Improvement as Explicit Task Type

Not just a side-effect — methodology improvement is a first-class task in the queue:
- Review recent session logs for recurring errors
- Check academic literature (Semantic Scholar MCP) for new methods
- Validate existing scoring formulas against new data
- Populate empty case library mechanisms (14/28 have zero cases)
- Update base rates in priors.md with new enforcement data

### 7.3 Tool Self-Improvement

When the agent encounters a limitation (e.g., "no view for this dataset", "this query is slow"), it can create infrastructure tasks:

```python
# Detected during entity refresh:
# "FAERS view missing reporter_country column"
# → Auto-create infrastructure task:
Task(
    type=INFRASTRUCTURE,
    priority=0.6,  # Medium — blocks future work
    prompt="Fix faers_demo view: add reporter_country column. "
           "Run setup_duckdb.py and verify healthcheck passes.",
    max_turns=15,
)
```

Source: MetaAgent (BAAI, [arXiv:2508.00271](https://arxiv.org/html/2508.00271v1)) — agents that autonomously build in-house tools from task experience. Also CORPGEN experiential learning (8.7% → 15.2% completion with pattern reuse).

### 7.4 Knowledge Base Growth Tracking

Metrics to track whether the system is actually getting smarter:
- Entity file count and total coverage breadth
- Case library completeness (73/168 mechanism slots filled)
- Prediction tracker N (currently 60, need 155 for statistical power)
- Base rate precision (CI width shrinking?)
- Healthcheck pass rate over time
- Source evaluation track records accumulating

---

## 8. Claude Code Technical Surface

### 8.1 Headless Execution

```bash
# Single task, bounded, with JSON output
claude -p "Update HIMS entity file" \
  --max-turns 30 \
  --output-format json \
  --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__duckdb__execute_query" \
  --permission-mode acceptEdits

# Resume a previous session
claude -p "Continue the FCX investigation" \
  --resume "$SESSION_ID" \
  --max-turns 30
```

Key flags:
| Flag | Purpose |
|------|---------|
| `-p` | Non-interactive mode (required for automation) |
| `--max-turns N` | Hard cap on agentic loop iterations |
| `--max-budget-usd N` | Cost ceiling (print mode only) |
| `--output-format json` | Structured output with session_id, cost |
| `--allowedTools` | Whitelist tools (no permission prompts) |
| `--permission-mode` | `acceptEdits` (auto-approve edits, ask for shell) or `bypassPermissions` (auto-approve everything) |
| `--resume ID` | Continue previous session (preserves context) |
| `--fork-session` | Branch from resume point without modifying original |
| `--append-system-prompt` | Add instructions while keeping defaults |
| `--no-session-persistence` | Don't save (ephemeral tasks) |
| `--json-schema '{...}'` | Force structured output matching schema |

Source: [Official headless docs](https://code.claude.com/docs/en/headless), [CLI reference](https://code.claude.com/docs/en/cli-reference)

### 8.2 Agent SDK (Programmatic)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Update HIMS entity file with latest insider transactions",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep",
                       "mcp__duckdb__execute_query"],
        permission_mode="acceptEdits",
        max_turns=30,
        cwd="/Users/alien/Projects/intel",
        setting_sources=["project"],  # Load CLAUDE.md, skills, rules
        mcp_servers={
            "duckdb": {"command": "uvx", "args": ["duckdb-mcp-server",
                       "--db-path", "/Users/alien/Projects/intel/intel.duckdb",
                       "--readonly"]}
        },
    ),
):
    if hasattr(message, "subtype") and message.subtype == "init":
        session_id = message.session_id
    if hasattr(message, "result"):
        print(message.result)
```

Source: [Agent SDK Python docs](https://platform.claude.com/docs/en/agent-sdk/python), [Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview)

### 8.3 Hooks for Autonomy

Two hooks are critical for autonomous operation:

**Stop Hook** — Checks if the task is actually complete before allowing Claude to stop:
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/check_task_complete.py"
      }]
    }]
  }
}
```

The script receives `{"stop_hook_active": bool, "last_assistant_message": "..."}` on stdin. Return `{"decision": "block", "reason": "Entity file not committed yet"}` to force continuation. **CRITICAL:** Check `stop_hook_active` and exit 0 if true to prevent infinite loops.

**SessionStart (compact matcher)** — Re-injects critical context after auto-compaction:
```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "compact",
      "hooks": [{
        "type": "command",
        "command": "cat .claude/post-compact-context.txt"
      }]
    }]
  }
}
```

Source: [Hooks guide](https://code.claude.com/docs/en/hooks-guide), [Hooks reference](https://code.claude.com/docs/en/hooks)

### 8.4 Custom Agent Definitions

```markdown
# .claude/agents/entity-refresher.md
---
name: entity-refresher
description: "Updates a single entity file with latest SEC, insider, 8-K data"
tools: Read, Edit, Write, Glob, Grep, Bash, mcp__duckdb__execute_query
model: opus
maxTurns: 30
skills:
  - entity-management
  - source-grading
---

You are an entity intelligence analyst. Your job is to update a single entity
file in analysis/entities/ with the latest available data.

## Process
1. Read the entity file and its YAML frontmatter (coverage dates)
2. For each stale coverage class, pull the latest data
3. Update the entity file with new findings, source-grading every claim
4. Update coverage dates in YAML frontmatter
5. Commit with descriptive message about what changed in understanding
```

Source: [Sub-agents docs](https://code.claude.com/docs/en/sub-agents)

### 8.5 Agent Teams (Experimental)

For parallel work across independent entities:
```bash
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

Shared task list at `~/.claude/tasks/`. DAG dependencies. Inter-agent messaging. But: no session resumption with teammates, experimental stability.

Source: [Agent teams docs](https://code.claude.com/docs/en/agent-teams)

---

## 9. Known Failure Modes & Mitigations

| Failure | Frequency | Impact | Mitigation |
|---------|-----------|--------|------------|
| **Opus 4.6 explore loops** | Common | 5-22 min wasted, >50 useless tool calls | `--max-turns` hard cap; external timer kills process after 2x expected duration |
| **Infinite compaction loop** | Occasional | Burns tokens indefinitely | External watchdog; if no output for 5 min, kill and restart |
| **Complete freeze (100% CPU)** | Rare | Requires kill -9, session lost | Process monitor with heartbeat check |
| **Context collapse after compaction** | Common | Forgets constraints, hallucinates | `SessionStart` compact hook re-injects critical context; keep tasks short enough to avoid compaction |
| **Premature "conversation too long"** | Occasional | Session unusable at 48% capacity | Start new session; don't try to /compact |
| **Stop hook infinite loop** | Guaranteed if misconfigured | Agent never stops | Always check `stop_hook_active`; max 2 stop-hook retries then force exit |
| **DuckDB parallel query crash** | Guaranteed on this hardware | Machine OOM | Sequential task execution only; never dispatch parallel agents loading parquet |
| **Sandbox escape (CVE-2026-25725)** | Patched | Config injection | Keep claude-code updated |

**The External Watchdog Pattern:**
```python
import subprocess, time, os, signal

def run_with_watchdog(cmd: list[str], timeout_seconds: int = 1800):
    """Run claude -p with a hard timeout and output monitoring."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    last_output_time = time.time()

    while proc.poll() is None:
        time.sleep(10)
        # Check for output (heartbeat)
        if proc.stdout.readable():
            last_output_time = time.time()

        # Hard timeout
        if time.time() - last_output_time > timeout_seconds:
            os.kill(proc.pid, signal.SIGTERM)
            time.sleep(5)
            if proc.poll() is None:
                os.kill(proc.pid, signal.SIGKILL)
            return TaskResult(status=FAILED, reason="Watchdog timeout")

    return TaskResult(status=COMPLETED, output=proc.stdout.read())
```

Sources:
- [GitHub #24585: Opus explore loops](https://github.com/anthropics/claude-code/issues/24585)
- [GitHub #6004: Infinite compaction](https://github.com/anthropics/claude-code/issues/6004)
- [GitHub #18532: Complete freeze](https://github.com/anthropics/claude-code/issues/18532)
- [GitHub #26858: Context window freeze](https://github.com/anthropics/claude-code/issues/26858)

---

## 10. Implementation Plan

### Phase 1: Minimal Orchestrator (1-2 days)

1. Python script: `meta/orchestrator.py`
2. Task queue from staleness check + signal scanner output
3. Sequential execution via `claude -p` with `--max-turns` and `--output-format json`
4. JSONL event log + daily markdown summary
5. Budget tracking ($ and turns)
6. Simple priority sort (no diversity yet)

### Phase 2: Anti-Mode-Collapse (1 day)

1. Diversity monitor (type histogram)
2. Sigmoid probability sampling for task selection
3. Mandatory rotation after 3 consecutive same-type
4. Time-boxing per task type

### Phase 3: Self-Improvement (1 day)

1. Wrap-up prompt appended to each task
2. METHODOLOGY as first-class task type
3. Tool self-improvement detection (create INFRASTRUCTURE tasks when gaps found)
4. Knowledge growth metrics dashboard

### Phase 4: Multi-Project Support (1 day)

1. Project-aware task generation (intel + self)
2. Per-project CLAUDE.md and memory loading
3. Cross-project learning (shared methodology improvements)
4. Project rotation (don't spend 8 hours on one project)

### Phase 5: Agent SDK Migration (2-3 days)

1. Replace `claude -p` subprocess calls with `claude-agent-sdk` async streams
2. Proper session management (capture and resume)
3. Hook integration for autonomous permission decisions
4. Parallel entity refreshes (if hardware permits — careful with DuckDB)

### Phase 6: Dashboard (optional)

1. Web UI showing daily log, task queue, budget, diversity metrics
2. One-click approval/rejection of pending decisions
3. Task injection (human adds to queue)
4. Historical trend charts (knowledge growth, prediction accuracy, cost)

---

## 11. Sources

### Claude Code Technical
- [Claude Code Headless/Programmatic](https://code.claude.com/docs/en/headless) — Official `-p` mode docs
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) — All flags
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide) — Hook events and patterns
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) — Full schemas
- [Claude Code Sub-agents](https://code.claude.com/docs/en/sub-agents) — Agent definitions
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) — Multi-agent coordination
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) — Programmatic API
- [Claude Agent SDK Python](https://platform.claude.com/docs/en/agent-sdk/python) — Python reference
- [Claude Agent SDK TypeScript](https://platform.claude.com/docs/en/agent-sdk/typescript) — TS reference
- [claude-agent-sdk-python GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [claude-agent-sdk-typescript GitHub](https://github.com/anthropics/claude-agent-sdk-typescript)

### Autonomous Agent Architecture
- [CORPGEN: Multi-Horizon Task Environments](https://arxiv.org/abs/2602.14229) — Microsoft Research, Feb 2026. Hierarchical planning across temporal scales. 3.5x improvement.
- [Decentralized Adaptive Task Allocation](https://www.nature.com/articles/s41598-025-21709-9) — Nature Scientific Reports, Nov 2025. Bandit-based task assignment.
- [OpenAI Codex Long-Horizon Tasks](https://developers.openai.com/cookbook/examples/codex/long_horizon_tasks/) — 25-hour, 13M token sessions. Plan/Edit/Run/Observe/Repair loop.
- [OpenAI Self-Evolving Agents](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining/) — LLM-as-judge + automated prompt refinement.
- [MetaAgent: Self-Evolving via Tool Meta-Learning](https://arxiv.org/html/2508.00271v1) — BAAI. Autonomous tool creation and knowledge base building.
- [Promptbreeder](https://openreview.net/attachment?id=9ZxnPZGmPU&name=pdf) — Google DeepMind, ICLR 2024. Self-referential self-improvement of prompts.
- [MetaReflection](https://arxiv.org/abs/2405.13009) — Microsoft Research. Learning meta-instructions from failure traces.

### Observability & Logging
- [AgentTrace](https://arxiv.org/html/2602.10133v1) — Three-surface structured logging (operational/cognitive/contextual).
- [Ian Paterson's 4-Layer Memory Architecture](https://ianlpaterson.com/blog/claude-code-memory-architecture/) — Practical MEMORY.md + daily logs + topic files.
- [Agents Arcade: Observability for AI Agents](https://agentsarcade.com/blog/observability-for-ai-agents-logs-traces-metrics) — Metrics, traces, silent degradation.
- [Gradient Flow: Observability for Agentic AI](https://gradientflow.com/observability-for-agentic-ai/) — LLM-as-judge evaluation traces.

### Community Autonomous Patterns
- [Building Automated Claude Code Workers with Cron](https://www.blle.co/blog/automated-claude-code-workers) — Task queue + cron + worker.
- [Ralph Wiggum Loop](https://beuke.org/ralph-wiggum-loop/) — Self-evaluating restart loop with git commits.
- [Claude Code Self-Improvement Skill](https://www.reddit.com/r/ClaudeCode/comments/1r89084/selfimprovement_loop_my_favorite_claude_code_skill/) — "Every mistake becomes a rule."
- [Running Claude Code 24/7](https://www.howdoiuseai.com/blog/2026-02-13-running-claude-code-24-7-gives-you-an-autonomous-c)
- [claude-code-scheduler](https://github.com/jshchnz/claude-code-scheduler) — OS-level task scheduling.
- [claude-flow](https://github.com/ruvnet/claude-flow) — Multi-agent orchestration platform.

### Failure Modes
- [GitHub #24585: Opus 4.6 explore loops](https://github.com/anthropics/claude-code/issues/24585)
- [GitHub #6004: Infinite compaction loop](https://github.com/anthropics/claude-code/issues/6004)
- [GitHub #18532: Complete freeze](https://github.com/anthropics/claude-code/issues/18532)
- [GitHub #26858: Context window freeze](https://github.com/anthropics/claude-code/issues/26858)
- [GitHub #23751: Premature context full](https://github.com/anthropics/claude-code/issues/23751)
- [CVE-2026-25725: Sandbox escape](https://advisories.gitlab.com/pkg/npm/@anthropic-ai/claude-code/CVE-2026-25725/)
- [Claude Code Architecture (reverse engineered)](https://vrungta.substack.com/p/claude-code-architecture-reverse)

### Adjacent Frameworks
- [SWE-EVO Benchmark](https://arxiv.org/pdf/2512.18470) — Long-horizon coding benchmark. GPT-5 + OpenHands: 65% SWE-bench but only 21% SWE-EVO.
- [CURATE: Curriculum Learning for RL Agents](https://icml.cc/virtual/2025/51486) — ICML 2025. Dynamic task difficulty scaling.
- [DGPO: Diversity-Guided Policy Optimization](https://ojs.aaai.org/index.php/AAAI/article/view/29019) — AAAI 2024. Diversity objective prevents mode collapse.
- [Durable Execution Pattern](https://inference.sh/blog/agent-runtime/durable-execution) — Checkpoint 5 state categories; lose at most 1 step on failure.
- [Error Handling Guide for AI Agents](https://www.arunbaby.com/ai-agents/0033-error-handling-recovery/) — Circuit breakers, selective amnesia, fallback escalation.
- [Steve Yegge's Gas Town](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) — Mayor/Polecats/Refinery multi-agent architecture. "Beads" for session memory.

### Our Own Prior Work
- `memory/claude_code_best_practices.md` — Feb 2026 research on CLAUDE.md, rules, skills, hooks, context management
- `docs/CONSTITUTION.md` — North star, improvement loop, self-prompting priorities
- `memory/MEMORY.md` — Session memory with 30+ methodological lessons
- `memory/analytical_reasoning.md` — 11 principles for adversarial analysis
- `memory/mechanisms.md` — 28 fraud/investment patterns
- `memory/priors.md` — Base rates and LLR tables

---

*This document is the design spec for the autonomous orchestrator. It should be reviewed and updated as implementation reveals new constraints.*

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: 8c7164edc9e8

cross_refs: analysis/investments/thesis_checks/hims_2026-02-20.md, docs/CONSTITUTION.md

end-knowledge-index -->
