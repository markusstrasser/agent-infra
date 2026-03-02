# PROJECT CONSTITUTION
Review against these principles, not your own priors.


> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

### Generative Principle

> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. In code, you can always run things — if they don't run successfully, they produce errors, and errors get corrected. With good verification, common sense, and cross-checking, autonomy leads to more than caution does. Grow > de-grow. Build the guardrails because they're cheap, not because they're the goal.

Error correction per session is the secondary constraint: autonomy only increases if errors are actually being caught. If supervision drops but errors go undetected, the system is drifting, not improving.

**The arms race:** The better the agent gets, the faster the human must rethink what they want next. Agent capability outpaces goal-setting. The human iteratively discovers what they want based on what they have — goals emerge from capability, not the other way around. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep. Until then, the agent proposes and the human steers.

### Principles

**1. Architecture over instructions.** Instructions alone = 0% reliable (EoG). If it matters, enforce with hooks/tests/scaffolding. Text is a prototype; architecture is the product. Exception: simple format rules and semantic predicates that can't be expressed as deterministic checks.

**2. Enforce by category.**

| Category | Examples | Enforcement |
|----------|----------|-------------|
| Cascading waste | Spin loops, bash parse errors, search flooding | Hooks (block) |
| Irreversible state | Protected data writes, destructive git ops | Hooks (block) |
| Epistemic discipline | Source tagging, hypothesis generation, pushback | Stop hook (advisory) |
| Style/format | Commit messages, naming | Instructions |

**3. Measure before enforcing.** Log every hook trigger to measure false positives. Without data, you can't promote or demote hooks rationally.

**4. Self-modification by reversibility + blast radius.** "Obvious improvement" is unmeasurable. Use concrete proxies:
- **Autonomous:** affects only meta's files, easily reversible, one clear approach, no other project changes
- **Propose and wait:** touches shared infrastructure, multiple viable approaches, affects other projects, deletes/restructures architecture
- **Always human-approved:** this Constitution section, GOALS.md

**5. Research is first-class.** Divergent (explore) → convergent (build) → eat your own dogfood → analyze → research again when stuck. Not every session. Action produces information. Opportunistic, not calendar-driven.

**6. Skills governance.** Meta owns skill quality: authoring, testing, propagation. Skills stay in `~/Projects/skills/` (separate). Meta governs through session-analyst (sees usage across projects) and improvement-log.

**7. Fail open, carve out exceptions.** Hooks fail open by default. Explicit fail-closed list: protected data writes, multiline bash, repeated failure loops (>5). List grows only with measured ROI data.

**8. Recurring patterns become architecture.** If used/encountered 10+ times → hook, skill, or scaffolding. Not a snippet, not a manual habit. (The Raycast heuristic.)

**9. Cross-model review for non-trivial decisions.** Same-model review is a martingale. Cross-model provides real adversarial pressure. Required for multi-project or shared infrastructure changes. **Dispatch on proposals, not open questions** — critique is sharper than brainstorming. When model review disagrees with user's expressed preference, surface the disagreement and let the user decide.

**10. The git log is the learning.** Every correction is a commit. The error-correction ledger is the moat. Commits touching governance files (CLAUDE.md, MEMORY.md, improvement-log, hooks) require evidence trailers.

### Autonomy Boundaries

**Hard limits (never without human):** modify Constitution or GOALS.md; deploy shared hooks/skills affecting 3+ projects; delete architectural components.

**Autonomous:** update meta's CLAUDE.md/MEMORY.md/improvement-log/checklist; add meta-only hooks; run session-analyst; conduct research sweeps; create new skills (propagation = propose).

### Self-Improvement Governance

A finding becomes a rule or fix only if: (1) recurs 2+ sessions, (2) not covered by existing rule, (3) is a checkable predicate OR architectural change. Reject everything else.

Primary feedback: session-analyst comparing actual runs vs optimal baseline. If a change doesn't improve things in 30 days, revert or reclassify as experimental.

### Session Architecture
- Fresh context per orchestrated task (no --resume)
- 15 turns max per orchestrated task
- Subagent delegation for fan-out (>10 discrete operations)

### Known Limitations
- **Sycophancy:** instruction-mitigated only. Session-analyst detects post-hoc.
- **Semantic failures:** unhookable. Cross-model review is the only mitigation.
- **Instructions work >0% for simple predicates.** Don't over-hook.

### Pre-Registered Tests

How to verify this constitution is working (check via session-analyst after 2 weeks):

1. **No build-then-undo on shared infrastructure changes.** The reversibility + blast radius boundary should prevent autonomous changes that get reverted. Test: zero reverts of meta-initiated shared changes in 14 days.
2. **Hooks fire on high-frequency failures.** Deployed hooks (bash-loop-guard, spinning-detector, failure-loop) should reduce repeated tool failures. Test: ≥50% reduction in ≥5-bash-failure-streaks vs pre-deployment baseline.
3. **Research produces architecture, not documents.** Research sessions should result in hooks, skills, or code — not just memos. Test: ≥50% of research findings in improvement-log have "implemented" status within 30 days.
4. **Model review surfaces disagreements.** When cross-model review disagrees with a stated preference, the synthesis explicitly flags it. Test: zero instances of silently overriding user preference in review artifacts.


# PROJECT GOALS

# Meta — Goals

> Human-owned. Agent may propose changes but must not modify without explicit approval.

## Mission

Maximize autonomous agent capability across all projects while maintaining epistemic integrity. The system should learn things once and handle them forever — the human intervenes only for genuinely new information, creative direction, or goal-setting.

## Generative Principle

**Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all projects.**

The deeper dynamic: the better the agent gets, the faster the human must rethink what they actually want next. This is an arms race — agent capability outpaces goal-setting until prediction quality is high enough that the agent can extrapolate what the human would want without asking. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep.

## Primary Success Metric

**Ratio of autonomous-to-supervised work across sub-projects.** Measured qualitatively: when reviewing a day's chat logs, there should be no:
- Reverted work (build-then-undo)
- 5-hour runs that should have been 1-hour (missing scaffolding, bad DX)
- Error branch spirals (bad hooks, missing guards)
- Agent theater (performative work that produces no value)
- Repeated corrections for things already taught once

The closer sessions get to "optimal run" (what would happen if the agent had perfect tooling and perfect instructions), the better meta is doing its job.

## Secondary Metrics

- **Wasted supervision rate** — % of human turns that are corrections, boilerplate, or rubber stamps. Currently ~21%. No numeric target, but qualitative trend should be downward.
- **Agent reliability** — % of tasks completed correctly without correction.
- **Time-to-capability** — how fast a new project gets proper agent infrastructure.

## Self-Modification Boundaries

**Full autonomy within invariants**, with a gradient:
- **Clear improvement, one obvious path** → just do it, commit, move on
- **Multiple valid solutions, could change a lot** → propose and wait for human review
- **CLAUDE.md Constitution section / GOALS.md** → always human-approved

The invariants: the Constitution section (in CLAUDE.md) and GOALS.md are human-owned. Everything else (rest of CLAUDE.md, hooks, skills, maintenance checklists, rules, MEMORY.md) can be modified autonomously when the improvement is unambiguous.

## Strategy

1. **Session forensics** — session-analyst finds behavioral anti-patterns, improvement-log tracks them to architectural fixes
2. **Hook engineering** — deterministic guards that prevent known failure modes (instructions alone = 0% reliable)
3. **Observability** — cockpit components keep the human informed without requiring them to ask
4. **Research** — stay current on agent behavior research, absorb what's applicable, ignore what's not
5. **Cross-project propagation** — skills, hooks, rules, and patterns flow from meta to all projects
6. **Self-improvement** — meta improves its own tooling using the same methods it applies to sub-projects

## Orchestrator

**Unblocked.** The orchestrator is meta-level infrastructure, independent of any specific project's validation status. Build it for tasks that are clearly automatable now:
- Entity refresh cycles
- Data maintenance
- Research sweeps
- Self-improvement passes (`/project-upgrade`, `/goals` elicitation)

The vision: any project can receive `/project-upgrade` or `/goals` and get meta's full toolkit applied autonomously, stopping only when a quality judge determines no further improvement is possible given the project's goals.

## Research Cadence

**First-class function, not every-session.** Research is divergent thinking — exploring what's new, what's possible, what others have solved. Implementation is convergent — building, testing, eating your own dogfood.

The cycle: research (divergent) until diminishing returns → build (convergent) → use it → analyze whether it actually works → research again when stuck or when new information appears.

- **Not calendar-driven.** No fixed weekly sweep that degrades into checkbox behavior.
- **Opportunistic.** New model ships → immediate sweep. Stuck on a problem → search for prior art. Steep improvement curve → more research. Diminishing returns → more action.
- **Action produces information.** At some point, building and using is more informative than reading papers.

## Projects Served

All projects: intel, selve, genomics, skills, papers-mcp, and any future repos. The uneven attention to date (mostly intel) is an artifact of where work has concentrated, not a priority decision.

Meta provides: shared skills, hooks, MCP servers, maintenance checklists, session analysis, observability, and the research pipeline. Any project should be able to install meta's toolkit and benefit.

## Skills Ownership

**Meta owns skill quality.** Meta runs session analysis, sees when skills are applied across projects, and can judge whether they work. Claude Code knowledge is co-located here. The information flow is natural: session-analyst findings → skill improvements → propagation.

Skills (`~/Projects/skills/`) may merge into meta as a directory. For now, kept separate. But quality governance (authoring standards, testing, versioning, cross-project propagation) lives in meta regardless of directory structure.

## Quality Standard

Recurring patterns (used/encountered 10+ times) must become architecture — not instructions, not snippets, not manual habits. The Raycast-snippet heuristic: if you paste it 10 times, it should be a hook, a skill, or scaffolding.

Qualitative reports from session-analyst are the primary feedback mechanism. No arbitrary numeric targets — the goal is "no stupid shit in the logs," judged by comparing actual runs against what an optimal run would look like.

## Open Questions (dispatched to model-review)

- **Enforcement granularity** — which principles deserve hooks vs. which stay instructional? Hooks can be annoying. Need empirical data from meta sessions. Progressive approach for now.
- **Autonomy gradient threshold** — where exactly does "clear improvement" end and "multiple valid solutions" begin? Probably can't be defined precisely; needs examples over time.
- **Skills merge timing** — meta owns quality but skills/ is still separate. When/whether to merge directories.

## Deferred Scope

- **IB API / trading automation** — blocked by paper trading validation in intel, not meta's concern
- **Fraud/corruption separation** — stays in intel until compute burden forces a split
- **Numeric benchmarking** — qualitative assessment first, formalize metrics when patterns stabilize

## Exit Condition

Meta becomes unnecessary when:
1. Claude (5, 6, N) natively handles meta-improvement — eliciting user goals, applying project upgrades, working correctly across subdomains, benchmarking itself
2. Claude Code ships native equivalents of hooks, observability, session analysis
3. The creative/divergent capability (connecting old projects, finding novel solutions across domains) is handled natively

This may never fully happen — meta encodes domain-specific and personal-idiosyncratic knowledge that generic tooling won't replicate. But the goal is to make meta's job progressively smaller, not to preserve it.

## Resource Constraints

- Single human operator with limited attention
- Cost-conscious (session receipts track spend)
- Compute: local Mac + cloud APIs (Anthropic, Google, OpenAI, Exa)
- Storage: SSK1TB external drive for large datasets

---

*Created: 2026-02-28. Updated: 2026-02-28 (generative principle, self-modification boundaries, research philosophy, skills ownership). Elicited via goals + constitution questionnaire.*


# ORCHESTRATOR PLAN (the artifact under review)

# Plan: Orchestrator — Automating Recurring Human Steps

**Session:** 3a65775d-0af8-4f72-9b2c-6b4c36b1be51
**Date:** 2026-03-01
**Project:** meta (implements here, serves all projects)
**Review:** Gemini 3.1 Pro + GPT-5.2. Artifacts: `.model-review/2026-03-01-orchestrator-plan/`
**Key revisions from review:** Drop auto_commit (constitutional violation), add worktree isolation for execute steps, fix runner bugs (returncode, JSON parsing, cascading failure, atomic claiming), cap all templates at 15 turns, add baseline instrumentation before deploy.

## Problem Statement

Analysis of 80+ sessions across 4 projects identified 8 recurring manual steps the human performs. 44% of sessions start with pasting a 6-20K char plan. The explore→review→plan→execute pipeline spans 2-4 sessions with the human as scheduler. Commit-only sessions, retro snippets, error paste-backs, and model routing directives are repeated daily.

Supervision audit: 5.9% wasted (down from 21%). The remaining waste is structural — it can't be eliminated by rules or hooks. It requires an orchestrator.

## Architecture: What We Build

```
┌─────────────────────────────────────────────┐
│  orchestrator.py (~150 lines)               │
│                                             │
│  cron (launchd) → poll task_queue.db        │
│  pick highest-priority ready task           │
│  claude -p "..." --max-turns 15             │
│      --output-format json                   │
│      --max-budget-usd 5.00                  │
│      --allowedTools "Read,Edit,Write,..."   │
│  parse result → update DB → pick next       │
│  log to orchestrator-log.jsonl              │
│  daily summary → daily-summary.md           │
└─────────────────────────────────────────────┘
```

**Not** using Agent SDK. Subprocess `claude -p` is simpler, proven, no dependency, and the SDK is new. We can migrate to SDK later if subprocess proves limiting.

**Not** using Agent Teams. Session-scoped, experimental, no cron integration.

**Not** building a DAG engine. Sequential task chaining with output files is sufficient. If we need DAGs later, we add them.

## Pre-Flight Tests — COMPLETED 2026-03-01

| Test | Session ID | Transcript? | Result |
|------|-----------|-------------|--------|
| `--worktree` | 4833b4a1 | **No** | Works but suppresses transcript creation |
| Slash commands | 4c6b25ca | **Yes** | Skills fire but hit permission denials (Skill + Read tools denied) |
| `--no-session-persistence` | 508c5c83 | **No** | Suppresses transcripts as feared |

**Decisions:**
1. **Drop `--no-session-persistence`.** Kills transcripts → breaks session-analyst feedback loop. Let sessions persist.
2. **Drop `--worktree` for execute steps (for now).** Also kills transcripts. Execute on trunk with scoped `--allowedTools` to limit blast radius. Revisit if transcript behavior changes in future Claude Code versions.
3. **Skills in `-p` need `--allowedTools` including `Skill,Read,Glob,Grep,Bash,Write,Edit`.** Or use explicit `llmx` calls for cross-model review (plan already does this).
4. **JSON output structure:** Cost at `total_cost_usd`, tokens under `modelUsage.<model>.inputTokens/outputTokens`. Runner updated accordingly.

## What Gets Automated (mapped to findings)

| # | Manual Step | Sessions | Automation |
|---|------------|----------|------------|
| 1 | Plan-paste-execute | 44% | Task chain: prior task writes `.claude/plans/`, next task reads it |
| 2 | Retro snippet | 2-3/day | Post-task step: run retro after every execution task |
| 3 | Commit-only sessions | 7+ | Post-task step: auto-commit after verified execution |
| 4 | Error paste-back | 2-3 sessions | Hook upgrade: all hooks → `additionalContext` JSON |
| 5 | Multi-session pipelines | daily | Pipeline type: explore→review→plan→execute as 4 chained tasks |
| 6 | Model routing | manual/session | Routing table in task definitions |
| 7 | Ground-truth verification | after model review | Verification task between review and execution |
| 8 | Recurring corrections | ongoing | Session-analyst → auto-propose CLAUDE.md patches |

## Detailed Design

### 1. Task Queue (SQLite)

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    pipeline TEXT,           -- e.g. "intel-data-wiring"
    step TEXT,               -- e.g. "explore", "review", "verify", "plan", "execute"
    project TEXT NOT NULL,   -- e.g. "intel", "selve", "genomics"
    prompt TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending|running|done|failed|blocked
    depends_on INTEGER REFERENCES tasks(id),
    priority INTEGER DEFAULT 5,     -- 1=highest, 10=lowest
    max_turns INTEGER DEFAULT 15,
    max_budget_usd REAL DEFAULT 5.0,
    model TEXT,                      -- NULL=default, "sonnet", "haiku"
    allowed_tools TEXT,              -- comma-separated, NULL=all
    cwd TEXT,                        -- working directory for this task
    requires_approval INTEGER DEFAULT 0,  -- 1 = human must approve before running
    blocked_reason TEXT,             -- why this task is blocked (dependency failed, needs approval)
    output_file TEXT,                -- path to JSON result
    result_summary TEXT,             -- extracted from structured output
    cost_usd REAL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    finished_at TEXT,
    error TEXT
);

CREATE TABLE pipelines (
    name TEXT PRIMARY KEY,
    template TEXT NOT NULL,  -- JSON array of step definitions
    project TEXT NOT NULL,
    schedule TEXT,           -- cron expression or NULL for manual
    pause_before TEXT,       -- JSON array of step names requiring approval
    last_run TEXT,
    enabled INTEGER DEFAULT 1
);
```

### 2. Core Loop (orchestrator.py)

```python
#!/usr/bin/env python3
"""Orchestrator: cron-driven task runner for claude -p."""

import fcntl
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("~/.claude/orchestrator.db").expanduser()
LOG_PATH = Path("~/.claude/orchestrator-log.jsonl").expanduser()
LOCK_PATH = Path("/tmp/orchestrator.lock")
OUTPUT_DIR = Path("~/.claude/orchestrator-outputs").expanduser()
DAILY_COST_CAP = 25.0  # USD

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db

def acquire_lock():
    """Prevent concurrent orchestrator runs (launchd overlap)."""
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        return None  # Another instance running

def claim_task(db):
    """Atomically pick + claim highest-priority ready task."""
    db.execute("BEGIN IMMEDIATE")
    task = db.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND (depends_on IS NULL
               OR depends_on IN (SELECT id FROM tasks WHERE status = 'done'))
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """).fetchone()
    if task:
        db.execute("UPDATE tasks SET status='running', started_at=datetime('now') WHERE id=?",
                    (task["id"],))
    db.commit()
    return task

def cascade_failure(db, task_id):
    """Mark all downstream tasks as blocked when a dependency fails."""
    db.execute("""
        UPDATE tasks SET status='blocked', error='dependency_failed'
        WHERE depends_on = ? AND status = 'pending'
    """, (task_id,))
    # Recurse: tasks depending on newly-blocked tasks
    blocked = db.execute("SELECT id FROM tasks WHERE depends_on = ? AND status = 'blocked'",
                         (task_id,)).fetchall()
    for row in blocked:
        cascade_failure(db, row["id"])

def check_daily_cost(db):
    """Return today's total cost. Abort if over cap."""
    row = db.execute("""
        SELECT COALESCE(SUM(cost_usd), 0) as total
        FROM tasks WHERE date(finished_at) = date('now', 'localtime')
    """).fetchone()
    return row["total"]

def run_task(task):
    """Execute a single task via claude -p."""
    cmd = [
        "claude", "-p", task["prompt"],
        "--output-format", "json",
        "--max-turns", str(task["max_turns"] or 15),
        "--max-budget-usd", str(task["max_budget_usd"] or 5.0),
        "--fallback-model", "sonnet",
        # NOTE: --no-session-persistence and --worktree both suppress transcripts.
        # Transcripts are needed for session-analyst. Omit both flags.
    ]
    if task["model"]:
        cmd.extend(["--model", task["model"]])
    if task["allowed_tools"]:
        cmd.extend(["--allowedTools", task["allowed_tools"]])

    cwd = task["cwd"] or os.path.expanduser(f"~/Projects/{task['project']}")

    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=cwd, timeout=2700,  # 45 min safety net (primary limits: max-turns + max-budget)
    )
    return result

def log_event(event):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        event["ts"] = datetime.utcnow().isoformat()
        f.write(json.dumps(event) + "\n")

def main():
    # Prevent concurrent runs
    lock_fd = acquire_lock()
    if not lock_fd:
        return  # Another instance running

    db = get_db()

    # Check daily cost cap
    daily_cost = check_daily_cost(db)
    if daily_cost >= DAILY_COST_CAP:
        log_event({"action": "cost_cap", "daily_cost": daily_cost})
        return

    task = claim_task(db)
    if not task:
        return  # Nothing to do

    task_id = task["id"]
    log_event({"action": "start", "task_id": task_id, "pipeline": task["pipeline"],
               "step": task["step"], "project": task["project"]})

    try:
        result = run_task(task)

        # Check returncode FIRST — don't parse stdout if process failed
        if result.returncode != 0:
            db.execute("""
                UPDATE tasks SET status='failed', finished_at=datetime('now'),
                    error=? WHERE id=?
            """, (f"exit_code_{result.returncode}: {result.stderr[:500]}", task_id))
            cascade_failure(db, task_id)
            log_event({"action": "failed", "task_id": task_id,
                        "exit_code": result.returncode, "stderr": result.stderr[:200]})
            db.commit()
            return

        # Parse JSON output (with fallback)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / f"{task_id}.json"

        try:
            output = json.loads(result.stdout) if result.stdout.strip() else None
            if output is None:
                raise ValueError("Empty stdout")
        except (json.JSONDecodeError, ValueError) as e:
            # Save raw stdout for debugging, mark failed
            output_file.write_text(result.stdout[:50000] if result.stdout else "EMPTY")
            db.execute("""
                UPDATE tasks SET status='failed', finished_at=datetime('now'),
                    output_file=?, error=? WHERE id=?
            """, (str(output_file), f"json_parse: {e}", task_id))
            cascade_failure(db, task_id)
            log_event({"action": "parse_error", "task_id": task_id, "error": str(e)})
            db.commit()
            return

        # Extract cost/token info from actual JSON structure (verified 2026-03-01)
        # Cost is at top level: total_cost_usd
        # Tokens are under modelUsage.<model>.inputTokens/outputTokens
        cost = output.get("total_cost_usd", 0)
        model_usage = output.get("modelUsage", {})
        tokens_in = sum(v.get("inputTokens", 0) + v.get("cacheReadInputTokens", 0)
                        for v in model_usage.values())
        tokens_out = sum(v.get("outputTokens", 0) for v in model_usage.values())
        summary = output.get("result", "")[:2000]
        is_error = output.get("is_error", False)
        permission_denials = output.get("permission_denials", [])

        # Treat permission denials as partial failure
        if permission_denials:
            summary = f"PERMISSION_DENIALS: {len(permission_denials)} tools denied. " + summary

        output_file.write_text(json.dumps(output, indent=2))

        db.execute("""
            UPDATE tasks SET status='done', finished_at=datetime('now'),
                output_file=?, result_summary=?, cost_usd=?,
                tokens_in=?, tokens_out=?
            WHERE id=?
        """, (str(output_file), summary, cost, tokens_in, tokens_out, task_id))

        log_event({"action": "done", "task_id": task_id, "cost_usd": cost})

    except subprocess.TimeoutExpired:
        db.execute("UPDATE tasks SET status='failed', finished_at=datetime('now'), error='timeout_45min' WHERE id=?",
                   (task_id,))
        cascade_failure(db, task_id)
        log_event({"action": "timeout", "task_id": task_id})

    except Exception as e:
        db.execute("UPDATE tasks SET status='failed', finished_at=datetime('now'), error=? WHERE id=?",
                   (str(e)[:500], task_id))
        cascade_failure(db, task_id)
        log_event({"action": "error", "task_id": task_id, "error": str(e)[:200]})

    db.commit()

if __name__ == "__main__":
    main()
```

### 3. Pipeline Templates (the recurring workflows)

#### 3a. Explore → Review → Verify → Plan → Execute

This is the pipeline that currently requires 2-4 manual sessions. All steps capped at 15 turns per constitutional constraint.

```json
{
  "name": "research-and-implement",
  "pause_before": ["execute"],
  "steps": [
    {
      "step": "explore",
      "prompt": "Research {topic}. Use WebSearch, Exa, and paper-search MCP tools. Save findings to .claude/plans/{pipeline}-explore.md with source citations for every factual claim.",
      "max_turns": 15,
      "max_budget_usd": 3.0,
      "allowed_tools": "Read,Glob,Grep,WebSearch,WebFetch,mcp__exa__web_search_exa,mcp__research__search_papers"
    },
    {
      "step": "review",
      "prompt": "Read .claude/plans/{pipeline}-explore.md. For each recommendation, verify it against the actual codebase (grep/read). Run cross-model review: pipe context to llmx -m gemini-3.1-pro-preview and llmx -m gpt-5.2 for adversarial critique. Write verified findings to .claude/plans/{pipeline}-review.md.",
      "max_turns": 15,
      "max_budget_usd": 8.0
    },
    {
      "step": "verify",
      "prompt": "Read .claude/plans/{pipeline}-review.md. For every claim about existing code (file paths, function names, features), verify against the actual codebase using Grep and Read. Write correction table to .claude/plans/{pipeline}-verified.md: | Claim | Actual | Status (confirmed/corrected/missing) |",
      "max_turns": 15,
      "max_budget_usd": 1.0,
      "allowed_tools": "Read,Glob,Grep,Write"
    },
    {
      "step": "plan",
      "prompt": "Read .claude/plans/{pipeline}-verified.md. Write an implementation plan to .claude/plans/{pipeline}-plan.md incorporating all corrections. Include: file list, execution order, verification steps.",
      "max_turns": 15,
      "max_budget_usd": 3.0,
      "allowed_tools": "Read,Glob,Grep,Write"
    },
    {
      "step": "execute",
      "prompt": "Execute the plan at .claude/plans/{pipeline}-plan.md. Check git log for any changes since the plan was written. Implement, test, commit with [{pipeline}] prefix.",
      "max_turns": 15,
      "max_budget_usd": 5.0
    }
  ]
}
```

**Human checkpoint:** Between plan and execute, the task sits in `blocked` with `requires_approval=1` until the human runs `orchestrator.py approve <pipeline>`. The human reviews `.claude/plans/{pipeline}-plan.md` and decides.

**Note on cross-model review:** The `review` step uses explicit `llmx` CLI calls instead of `/model-review` slash command, since slash commands may not work in `-p` mode (needs empirical verification per pre-flight test #2). If they do work, templates can be simplified.

#### 3b. Entity Refresh (intel)

```json
{
  "name": "entity-refresh",
  "project": "intel",
  "schedule": "0 6 * * *",
  "steps": [
    {
      "step": "refresh",
      "prompt": "Read analysis/entities/ and identify entities not updated in >7 days. For each, use WebSearch and DuckDB to find latest data. Update entity files with source tags. Commit with [entity-refresh] prefix.",
      "max_turns": 15,
      "max_budget_usd": 3.0,
      "model": "sonnet",
      "agent": "entity-refresher"
    }
  ]
}
```

#### 3c. Session Retro (all projects)

```json
{
  "name": "session-retro",
  "schedule": "0 22 * * *",
  "steps": [
    {
      "step": "analyze",
      "prompt": "Analyze today's sessions across all projects for behavioral anti-patterns: sycophancy, over-engineering, build-then-undo, token waste, search flooding. Use extract_transcript.py to preprocess, then dispatch to Gemini for analysis. Append structured findings to improvement-log.md. If any finding recurs 2+ times, draft a CLAUDE.md rule change or hook proposal.",
      "max_turns": 15,
      "max_budget_usd": 3.0,
      "model": "sonnet",
      "cwd": "~/Projects/meta"
    }
  ]
}
```

#### 3d. Research Sweep (weekly)

```json
{
  "name": "research-sweep",
  "schedule": "0 8 * * 1",
  "steps": [
    {
      "step": "search",
      "prompt": "Search arxiv for last 7 days: 'LLM agents', 'coding agents', 'tool use', 'agentic AI'. Search Exa for Anthropic blog posts, Simon Willison, Trail of Bits, Kapoor/Narayanan. Save papers to corpus. Write findings to .claude/plans/research-sweep.md with source citations.",
      "max_turns": 15,
      "max_budget_usd": 5.0,
      "allowed_tools": "Read,Write,Glob,Grep,WebSearch,WebFetch,mcp__exa__web_search_exa,mcp__research__search_papers,mcp__research__save_paper,mcp__paper-search__search_arxiv"
    },
    {
      "step": "triage",
      "prompt": "Read .claude/plans/research-sweep.md. For each finding: does it change our hooks, skills, routing, or architecture? If yes, write a proposal to .claude/plans/research-sweep-proposals.md. Commit to meta with [research-sweep] prefix.",
      "max_turns": 15,
      "max_budget_usd": 2.0,
      "model": "sonnet"
    }
  ]
}
```

### 4. Hook Upgrades (Error Paste-Back Elimination)

Currently, stop-research-gate prints block reasons to **stderr** and exits 2. The agent sees "a hook blocked you from stopping" but never sees **why** — the stderr message goes to the user's terminal, not the agent's context. That's why the user has to paste it back.

**Fix:** Output JSON to **stdout** with `additionalContext` field. Keep exit 2 for the block signal.

**Files to change:**

| Hook | Current | Change |
|------|---------|--------|
| `stop-research-gate.sh` | `print(..., file=sys.stderr); sys.exit(2)` | `print(json.dumps({"additionalContext": "..."})); sys.exit(2)` |
| `postwrite-source-check.sh` | Same pattern | Same fix |

**Pattern (corrected — stdout, not stderr):**
```bash
# Old:
echo "BLOCKED: Research files missing source tags" >&2
exit 2

# New:
echo '{"additionalContext": "BLOCKED: Research files modified without source tags: file1.md, file2.md. Add provenance tags before stopping."}'
exit 2
```

**Note:** PreToolUse hooks with exit 2 already have their block reason visible to the agent. This fix is specifically for Stop hooks where the block reason doesn't reach the agent's context.

Our existing advisory hooks (spinning-detector, commit-check) already use `additionalContext` via stdout correctly — this just extends the pattern to blocking Stop hooks.

### 5. Retro Skill

Replace the clipboard snippet with a one-word command.

**File:** `~/Projects/skills/retro/SKILL.md`

```markdown
---
name: retro
description: End-of-session retrospective. Extracts lessons learned, failure modes, and tooling proposals.
user-invocable: true
argument-hint: '[project]'
---

Review what happened in this session:

1. What went wrong? Name specific failure modes (build-then-undo, token waste, sycophancy, search flooding).
2. Where did you struggle with the environment (paths, dependencies, APIs, permissions)?
3. What information would have saved time if you'd known it upfront?
4. What recurring pattern should become a hook, rule, or skill?

Output format:
- 3-5 bullet points, each with: **failure mode**, evidence, proposed fix
- If any finding matches an existing improvement-log entry, note "RECURRING: #N"
- Be concise. No platitudes. Name the files, the commands, the exact mistake.
```

### 6. ~~Auto-Commit Post-Task~~ → Agent Commits Per CLAUDE.md Rules

**DROPPED per model review.** Auto-commit from Python violates the irreversible state principle (blindly `git add -A` commits everything) and creates a race condition with the agent's own commit behavior.

**Instead:** The execute step's prompt instructs the agent to commit per CLAUDE.md rules (semantic messages, [prefix], governance trailers). The orchestrator's Python code never touches git.

**Note:** `--worktree` was the ideal solution (isolated branch, human reviews PR) but pre-flight testing showed it suppresses transcript creation — breaking the session-analyst feedback loop. Execute steps run on trunk with scoped `--allowedTools` to limit blast radius. The commit instruction in the prompt is the agent's responsibility, not the orchestrator's.

**Revisit:** When Claude Code fixes worktree transcript persistence, switch execute steps to `--worktree`.

### 7. Ground-Truth Verification Step

Injected between model-review and execution in pipelines that use external model feedback.

```json
{
  "step": "verify",
  "prompt": "Read .claude/plans/{pipeline}-review.md. For every claim about existing code (file paths, function names, class names, variable names, feature presence), verify against the actual codebase using Grep and Read. Write a correction table to .claude/plans/{pipeline}-verified.md: | Claim | Actual | Status (confirmed/corrected/missing) |",
  "max_turns": 10,
  "max_budget_usd": 1.0,
  "allowed_tools": "Read,Glob,Grep,Write"
}
```

This replaces the manual "8 corrections to Gemini's analysis" pattern.

### 8. CLI Interface

```bash
# Submit a pipeline
python3 orchestrator.py submit research-and-implement \
    --project intel --topic "alternative data for semiconductor supply chain"

# Submit a one-off task
python3 orchestrator.py run --project intel \
    --prompt "Add views for the 5 new FAA datasets" \
    --max-turns 15

# Check status
python3 orchestrator.py status

# Approve a paused pipeline step
python3 orchestrator.py approve intel-data-wiring

# View today's log
python3 orchestrator.py log --today

# Generate daily summary
python3 orchestrator.py summary
```

### 9. Scheduling (launchd on macOS)

```xml
<!-- ~/Library/LaunchAgents/com.meta.orchestrator.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.meta.orchestrator</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/alien/Projects/meta/scripts/orchestrator.py</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>  <!-- every 15 minutes -->
    <key>StandardOutPath</key>
    <string>/Users/alien/.claude/orchestrator-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/alien/.claude/orchestrator-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/Users/alien/.local/bin</string>
    </dict>
</dict>
</plist>
```

## What We Explicitly Don't Build

1. **DAG engine** — Sequential chaining with `depends_on` is sufficient. Airflow/Temporal are overkill.
2. **Agent SDK integration** — subprocess `claude -p` first. SDK if we need structured streaming.
3. **Web UI** — CLI + daily markdown summary. Dashboard.py already exists for receipts.
4. **Multi-machine** — Single laptop. No distributed anything.
5. **Custom model routing** — Use `--model` flag per task. No smart router.

## Compatibility Check: Claude Code Native Features

| Native Feature | Conflicts? | How We Use It |
|----------------|-----------|---------------|
| `claude -p` + `--max-turns` | No — this IS our execution engine | Core of orchestrator |
| `--output-format json` | No | Parse results |
| `--max-budget-usd` | No | Cost cap per task |
| `--no-session-persistence` | Transcript gap | Suppresses transcripts (tested). Don't use. |
| `--allowedTools` | No | Scope tools per task type |
| `--fallback-model` | No | Add for resilience |
| `--worktree` | Transcript gap | Suppresses transcripts (tested). Defer until fixed. |
| `--agents` | No | Could inline agent defs per task |
| Agent Teams | No conflict — orthogonal | Teams = within-session fan-out. Orchestrator = cross-session scheduling. |
| `/batch` | No conflict | `/batch` = interactive parallel refactor. Orchestrator = scheduled pipeline. |
| Hooks | No conflict | Hooks fire inside orchestrated `claude -p` sessions normally |
| Subagent memory | Complementary | Orchestrated tasks spawn subagents that accumulate memory |
| `--json-schema` | Useful | Structured output for verification steps |

**No conflicts found.** The orchestrator operates at a layer above Claude Code — it's a scheduler that invokes Claude Code. Everything inside the invocation uses native features normally.

## Implementation Order

### Phase 0: Pre-Flight Tests (~15 min, MUST be run outside Claude Code session)
- [ ] Test `--worktree` in `-p` mode: `claude -p "Create a test file" --worktree test-orch --max-turns 3 --output-format json`
- [ ] Test slash commands in `-p` mode: `claude -p "List your available slash commands" --max-turns 3 --output-format json`
- [ ] Test transcript persistence: run with `--no-session-persistence`, check `~/.claude/projects/` for new .jsonl
- [ ] Record results → decide: use --worktree? use slash commands or llmx? keep --no-session-persistence?

### Phase 1: Core + Baseline Instrumentation (~3 hours)
- [ ] `scripts/schema.sql` — task queue DDL (with requires_approval, blocked_reason columns)
- [ ] `scripts/orchestrator.py` — core loop with: atomic claiming (BEGIN IMMEDIATE + flock), returncode checking, JSON parse fallback, cascading failure, daily cost cap
- [ ] `scripts/orchestrator.py submit/run/status/approve/log` — CLI interface
- [ ] `scripts/baseline_metrics.py` — daily metrics.json: plan-paste count, commit-only sessions, hook triggers, daily cost (run for 14 days before Phase 3)
- [ ] Test: submit one task, verify it runs and logs correctly
- [ ] Test: submit a task that fails, verify cascade + error logging

### Phase 2: Pipelines + Template Engine (~2 hours)
- [ ] `pipelines/` directory with JSON templates
- [ ] Template variable substitution ({pipeline}, {topic}) in runner
- [ ] `depends_on` chaining (task N+1 waits for task N)
- [ ] `pause_before` → sets `requires_approval=1` on matching steps
- [ ] `approve` CLI command flips blocked → pending
- [ ] File-based output passing (step N writes to `.claude/plans/`, step N+1 reads)
- [ ] Test: run explore→verify→plan chain, verify pause before execute

### Phase 3: Scheduling + Deploy (~30 min)
- [ ] launchd plist (15-min interval)
- [ ] `orchestrator.py schedule` — list/enable/disable scheduled pipelines
- [ ] Test: verify launchd fires, respects flock (no concurrent runs), picks up pending tasks

### Phase 4: Retro + Hooks (~1 hour)
- [ ] `/retro` skill (clipboard snippet replacement)
- [ ] Upgrade stop-research-gate.sh: JSON additionalContext to stdout (keep exit 2)
- [ ] Upgrade postwrite-source-check.sh: same pattern
- [ ] Ground-truth verification step template

### Phase 5: Pipeline Library (~1 hour)
- [ ] `research-and-implement` pipeline template (5 steps with verify)
- [ ] `entity-refresh` pipeline template
- [ ] `session-retro` pipeline template
- [ ] `research-sweep` pipeline template
- [ ] Wire session-analyst into nightly retro
- [ ] `monthly-pruning` pipeline template (consumption audit + keep/compress/kill)
- [ ] `last_useful` column + consumption tracking in CLI

## Success Criteria (30 days, with measurement definitions)

**Baseline:** Capture 14 days of pre-deploy metrics using daily metrics.json before deploying orchestrator.

1. **Plan-paste sessions decline measurably.** Detection: user message matches `(?i)\bimplement the following plan\b` OR single message ≥6000 chars with ≥5 markdown headings. Measure: rate in days 15-30 vs baseline. Target: statistically significant decline (not a fixed %). Conservative estimate: 13-20% reduction.
2. **Commit-only sessions decline.** Detection: session where ≥80% of tool calls are git commands and net diff ≤10 LOC. Target: ≤20% of baseline for orchestrated work.
3. **Retro performed via `/retro` or pipeline for ≥80% of sessions.** Measure: `retro_invocations / sessions` from orchestrator log + transcript analysis.
4. **Error paste-back incidents = 0 for orchestrated runs.** Detection: user message contains `(?i)\bBLOCKED:\b` that repeats hook stderr content. Target: 0 for orchestrated, ≤20% of baseline for interactive.
5. **Daily cost stays under $25.** Enforced by orchestrator daily cap. Metric: `P(daily_cost ≤ 25) ≥ 0.95` over 30 days.
6. **No silent failures.** Detection: any task with status=done AND (returncode ≠ 0 OR output invalid OR missing terminal log event). Target: 0 over 30 days.
7. **Zero orchestrator-generated reverts.** (Constitutional prereg test #1 analogue.) Target: 0 reverts of orchestrator commits in 14 days.
8. **Autonomy metric improvement.** Human turns tagged "correction/boilerplate" by session-analyst decline by ≥20% vs baseline.
9. **No unbounded accumulation.** After 60 days: governance file line counts (CLAUDE.md, MEMORY.md) grow ≤20% net. Churn rate on governance files ≤5 modifications/14 days. Monthly pruning report executed at least once.

## Hardening (merged from OpenClaw lessons model review, 2026-03-01)

Source: `.model-review/2026-03-01-openclaw-lessons-plan/synthesis.md` items G5, G6, G12, G13, P11, P12.

### H1. JSON Output Schema + 2-Try Error Correction (G12)
When a task returns invalid JSON or empty stdout, retry once with a simplified prompt before marking failed. Current code marks failed immediately on parse error.

- [ ] Add retry logic in `run_task`: on JSON parse failure, re-run with prompt "The previous run produced invalid output. Re-run the task and ensure valid JSON output." + original prompt
- [ ] Cap at 2 tries total (not infinite retry)
- [ ] Consider `--json-schema` flag for verification steps that need structured output

### H2. Race Condition Mitigation — Separate Memory Namespace (G5)
Orchestrator tasks and foreground interactive sessions both write to MEMORY.md → race condition.

- [ ] Orchestrator writes to `~/.claude/orchestrator-memory/` namespace, not shared MEMORY.md
- [ ] Daily summary step merges orchestrator findings into a human-reviewable `orchestrator-daily.md`
- [ ] Foreground session never auto-reads orchestrator memory (avoids contamination)

### H3. Self-Observability — Structured JSONL (G6, P12)
Current log_event captures start/done/failed but lacks structured metrics for analysis.

- [ ] Add fields to log events: `turns_used`, `context_tokens_at_end`, `permission_denials_count`, `tools_used` (list)
- [ ] Add acceptance test metrics per task type: `edit_time_seconds`, `files_modified`, `lines_changed`, `commit_count`
- [ ] Weekly script to compute: ship-ready rate (done/(done+failed)), mean cost per task type, mean turns per task type

### H4. Doctor as First Maintenance Task (G13)
Run health diagnostics before any autonomous work to catch config drift early.

- [ ] Add `doctor` as step 0 in all scheduled pipelines (entity-refresh, session-retro, research-sweep)
- [ ] Doctor checks: hook syntax, settings.json validity, MCP connectivity, git state, symlink integrity
- [ ] If doctor fails with severity=error, block all subsequent pipeline steps
- [ ] Doctor implementation: `scripts/doctor.py` (see openclaw-lessons plan Phase 5 for spec)

### H5. Kill-Switch (P11)
- [ ] Env var `ORCHESTRATOR_DISABLED=1` skips all task execution in main()
- [ ] Staged rollout: meta-only pipelines for 2 weeks before cross-project

## Self-Regulation: Preventing Cruft Accumulation

The orchestrator produces artifacts (rules, hooks, entity profiles, research memos, findings). Without selection pressure, these accumulate into cruft — not wrong enough to flag, not useful enough to justify their existence.

### Mechanism 1: Consumption Tracking

Every orchestrator output gets a `last_useful` timestamp in the DB. Updated when:
- Human views output via CLI (`orchestrator.py show <id>`) or Telegram
- An entity profile is referenced in a session (grep session transcripts)
- A rule/hook fires (hook telemetry)
- A research finding gets cited in improvement-log

```sql
ALTER TABLE tasks ADD COLUMN last_useful TEXT;  -- updated on consumption
```

Artifacts with no `last_useful` update in 30 days are pruning candidates.

### Mechanism 2: Churn-Rate Monitoring

Track modification frequency on governance files. High churn = thrashing, not improving.

```bash
# Weekly check — added to maintenance pipeline
git log --since="14 days" --name-only --pretty=format: -- CLAUDE.md MEMORY.md improvement-log.md | sort | uniq -c | sort -rn
```

Threshold: if a governance file is modified >5 times in 14 days, flag for review. Either the rule isn't right yet (needs more thought before committing) or the underlying problem isn't well-understood.

### Mechanism 3: Monthly Pruning Prompt

The orchestrator generates a monthly digest:
- Everything added in the last 30 days (rules, hooks, entity profiles, research memos)
- For each: last_useful timestamp, creation source, what it replaced (if anything)
- Items with no consumption → proposed for kill
- Items referenced 3+ times → candidates for compression (instruction → tool → infrastructure)

Three outcomes per item: **keep** (still needed as-is), **compress** (promote to tool/hook/principle), **kill** (delete).

```json
{
  "name": "monthly-pruning",
  "schedule": "0 9 1 * *",
  "steps": [
    {
      "step": "audit",
      "prompt": "Generate a pruning report. For every orchestrator artifact created in the last 30 days, check: (1) last_useful timestamp, (2) times referenced in sessions, (3) whether it duplicates or overlaps existing rules/hooks. Output: keep/compress/kill recommendation per item with evidence. Write to .claude/plans/pruning-report.md.",
      "max_turns": 15,
      "max_budget_usd": 2.0,
      "requires_approval": 1
    }
  ]
}
```

Human reviews the report. Compress actions become tasks (e.g., "turn these 3 rules into a hook"). Kill actions are deletions. Keep actions touch `last_useful`.

### Design Rationale

The default for accumulated things should be **expiration, not persistence**. In biological systems, ~98% is turnover, ~2% is conserved (core genes). For this system:
- **Accumulate at the leaves:** entity profiles, findings, datasets — reality has detail, keep it
- **Compress at the trunk:** principles, tools, APIs — fewer pieces that combine more ways
- The orchestrator's pruning job isn't "delete old stuff" — it's "has this been repeated enough to compress into a tool, or is it still a useful leaf?"

## Risks

1. **Laptop sleep kills tasks.** Mitigation: 45-min timeout + task marked failed. Launchd restarts on wake. Cascade blocks downstream tasks.
2. **Cost runaway.** Mitigation: `--max-budget-usd` per task + daily $25 cap check before picking tasks.
3. **Stale plans.** Mitigation: verification step checks git log. Execute prompt includes "check git log for changes since plan was written."
4. **Wrong project commits.** Mitigation: `cwd` per task is explicit. Execute steps use `--worktree` (isolated branch). No Python git operations.
5. **Agent SDK obsoletes this.** Fine — the script is disposable. If SDK adds scheduling, migrate.
6. **Concurrent orchestrator runs.** Mitigation: `fcntl.flock` on `/tmp/orchestrator.lock` + atomic `BEGIN IMMEDIATE` claiming.
7. **False positives (task marked done on failure).** Mitigation: returncode checked before parsing output. Empty/invalid JSON = failed.
8. **Session-analyst can't see orchestrated runs.** Mitigation: pre-flight test #3 verifies transcript persistence. Drop `--no-session-persistence` if needed.
9. **Cross-model review broken in -p mode.** Mitigation: use explicit `llmx` calls in templates instead of `/model-review` slash command. Pre-flight test #2 verifies.


# PREVIOUS MODEL REVIEW (already incorporated into plan above)

# Cross-Model Review Synthesis: Orchestrator Plan

**Mode:** Review (convergent)
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (CLAUDE.md Constitution section, GOALS.md)
**Extraction:** 38 items extracted, 19 included, 3 deferred, 0 rejected, 16 merged into 8 parents

## Verified Findings (adopt into plan)

| ID | Finding | Source | Verified How |
|----|---------|--------|-------------|
| G2/G10/P19 | **Drop auto_commit entirely.** Python wrapper should not touch git. Agent commits inside worktree per CLAUDE.md rules. | Both models | Constitutional check: irreversible state principle. Race condition with agent's own commits. |
| G7/G13 | **Use `--worktree` for execute steps.** Automated execution on trunk risks polluting main. Worktree creates a branch; human or CI reviews. | Both models | Native feature exists (`--worktree` flag). Gemini's #1 priority. |
| P7/P8/G8 | **Check returncode before marking done.** Current code marks done regardless of exit code. Empty stdout = success (wrong). | Both models | Code review: `json.loads(result.stdout)` with fallback `{}` — no returncode check anywhere. |
| G4/P4 | **Cascading failure + blocked state.** Failed task → downstream tasks stuck forever. Schema has 'blocked' but code never sets it. | Both models | SQL review: `pick_task` requires `status='done'` on dependency. No cascade logic. |
| P9/P18 | **Atomic task claiming.** Launchd 15min < timeout 30min = certain overlap. Need `BEGIN IMMEDIATE` + file lock. | GPT | Arithmetic: 15 < 30. No lock in code. |
| P1 | **15-turn cap violated.** Templates use 20-25 turns. Constitution says 15. | GPT | Direct text comparison. Easy fix. |
| G1/G15 | **Hook JSON goes to stdout, not stderr.** stop-research-gate prints to stderr + exit 2. Agent never sees the reason — just "blocked." | Gemini | Verified: spinning-detector already uses stdout JSON correctly. stop-research-gate uses stderr. |
| G6/G14 | **Verify `--no-session-persistence` doesn't kill transcripts.** If it does, session-analyst can't analyze orchestrated runs — breaks self-improvement loop. | Gemini | Can't test from inside session. Must verify empirically before deploying. |
| P2/P16 | **Verify `/model-review` works in `-p` mode.** If slash commands don't fire in batch mode, the cross-model review step is broken. | GPT | Can't test from inside session. Must verify empirically. |
| P5/P6 | **Template system unimplemented.** Pipelines table, variable substitution ({pipeline}, {topic}), pause_before — all described but no code. | GPT | Code review: runner has no template expansion, no pipeline CRUD. |
| P11/P13/P14 | **Success criteria need baselines + measurement.** "Plan-paste drop >50%" has no baseline. Realistic estimate: 13-20% reduction. Need regex definitions, baseline windows. | GPT | Quantitative analysis. 44% × 60% schedulable × 50% approval-needed ≈ 13-20%. |
| P12 | **Daily cost cap not enforced.** No rollup query, no stop-scheduling threshold. | GPT | Code review: cost_usd stored per task but never aggregated. |
| P21 | **Baseline instrumentation before deploy.** "Measure before enforcing" principle requires pre/post data. Add daily metrics.json. | GPT | Constitutional principle #3 check. |
| P10 | **Log/output directory creation missing.** mkdir -p needed. | GPT | Code review: LOG_PATH opened without ensuring parent dir exists. |
| G5 | **Soften the 30-min guillotine.** Use --max-turns + --max-budget-usd as primary limits. Keep subprocess timeout at 45min as last-resort safety net only. | Gemini | Valid: graceful limits > abrupt kill. |
| P3 | **Resolve hook fix contradiction.** Plan proposes specific changes while admitting root cause unverified. Rewrite: verify first, then propose. | GPT | Internal inconsistency in plan text. |
| G11 | **Retro skill: build as specified.** Both models agree. Clean replacement for clipboard snippet. | Both | No objection. |
| G12 | **Verification step: keep as specified.** Both models agree. Embodies cross-model review principle. | Both | No objection. |

## Deferred (needs empirical testing)

| ID | Finding | Test Required |
|----|---------|---------------|
| G16 | `--worktree` may hang in headless `-p` mode awaiting confirmation | Run `claude -p "..." --worktree test` from terminal outside session |
| P22 | `/model-review` slash commands may work in `-p` mode | Run `claude -p "Use /model-review on X" --max-turns 5` outside session |
| G6 | `--no-session-persistence` may still write transcripts | Run with flag, check `~/.claude/projects/` for new .jsonl |

**These three tests should be the FIRST thing done before implementing.** They determine whether key features of the plan are viable.

## Where I (Claude) Was Wrong in the Original Plan

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|
| "echo JSON to stderr; exit 2" for hooks | Hooks communicate structured data via stdout. stderr goes to terminal, not agent. | Gemini (G1) |
| Auto-commit function safe for orchestrator | Constitutional violation — irreversible state. Race condition with agent commits. | Both (G2, P19) |
| 15-25 turns in templates | Constitution caps at 15. Direct violation. | GPT (P1) |
| Code handles failures correctly | Marks done regardless of returncode. Empty output = success. | Both (P7, G8) |
| Plan-paste sessions drop >50% | Realistic: 13-20% unless full template system + habit change. | GPT (P13) |
| Hook error paste-back fix is clear | Internal contradiction: proposed changes while admitting root cause unverified. | GPT (P3) |

## Gemini Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| "Emit JSON to stdout then exit 0 (let Claude Code parse block instruction)" | Partially wrong. For blocking PreToolUse hooks, exit 2 IS the block signal. `additionalContext` on stdout is separate from the block mechanism. Exit 2 + stdout JSON with `additionalContext` is the correct pattern. |
| Worktree may break in headless mode | Possible but unverified. Not a reason to skip — just test it first. |

## GPT Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| "15-turn cap violated by templates" — constitution says 15 | CORRECT. But "Session Architecture" section says 15, while the orchestrator section in GOALS.md is open-ended. The 15-turn limit was for orchestrated tasks specifically. Still, safer to respect the documented cap and increase only with evidence. |
| "Concurrency 10-30% for long tasks" | Plausible but specific percentage is fabricated. The real question: does launchd guarantee no overlap? (No — `StartInterval` doesn't prevent it.) |
| Constitutional coverage scores (40-80%) | These percentages are invented. Useful as relative ranking but don't trust absolute numbers. |

## Revised Plan Changes

Based on this review, the plan needs these amendments before implementation:

### Critical (must fix)
1. **Drop auto_commit function.** Execute steps use `--worktree`. Agent commits inside worktree per its CLAUDE.md rules. No Python git operations.
2. **Add returncode check.** `if result.returncode != 0: status = 'failed'`. Don't parse stdout if returncode is bad.
3. **Add cascading failure.** When task fails: `UPDATE tasks SET status='blocked' WHERE depends_on = ?`
4. **Add atomic claiming.** `BEGIN IMMEDIATE` transaction + filesystem lock (`/tmp/orchestrator.lock`).
5. **Fix templates to 15 turns max.** Respect constitutional cap.
6. **Wrap JSON parse in try/except.** Save raw stdout on parse failure. Mark failed, not done.
7. **mkdir -p for all output dirs.** Trivial but necessary.

### Important (fix before deploy)
8. **Run 3 empirical tests first.** Worktree in -p, slash commands in -p, transcript persistence with --no-session-persistence.
9. **Fix hook output pattern.** stop-research-gate: output JSON to stdout with `additionalContext`, keep exit 2 for blocking. Don't touch stderr approach until after verifying the problem.
10. **Implement pipeline template expansion.** Without it, the orchestrator is just "batch claude-p" — no chaining.
11. **Add daily cost rollup + threshold check.** `SELECT SUM(cost_usd) FROM tasks WHERE date(finished_at) = date('now')`.
12. **Temper success criteria.** "Measurable decline from baseline" not ">50%". Add regex definitions per GPT's suggestions.
13. **Add baseline instrumentation** (daily metrics.json) BEFORE deploying orchestrator.

### Nice-to-have (can defer)
14. Replace /model-review in pipeline prompts with explicit llmx calls (in case slash commands don't work in -p).
15. Add --fallback-model to runner for resilience.
16. Implement `blocked_reason`, `requires_approval` columns for richer approval UX.
# NEW TRANSCRIPT ANALYSIS (70 sessions, Mar 1-2, all projects)

## Context
After the orchestrator plan was written and model-reviewed, we analyzed 70 sessions (193 transcripts) across genomics, intel, meta, and selve projects to discover patterns the orchestrator should address. Three subagents independently analyzed each project's transcripts.

## Quantitative Summary
- 385 user messages across 70 sessions
- 25 plan-paste instances (44% of meta sessions start with clipboard paste)
- 49 research-kick instances (most frequent user action)
- 26 interrupted requests (tasks running too long)
- 23 task notifications (subagent results)
- 13 approval rubber-stamps ("ok", "yes", "go ahead")
- 12 compaction continuations
- 11 hook paste-backs (human copying hook stderr to agent)

## Finding 1: Orientation Tax (49-78% of genomics sessions)
Every genomics session re-runs ls data/wgs/analysis/, ls /Volumes/SSK1TB/, volume mount checks, pipeline state enumeration. Session c6e8f986 spent 78% of its 989-line session on orientation before writing a single file. Session 0a1abe5b spent 49% (lines 0-275) doing ls/cat discovery before the first Edit.

Root cause: No persistent pipeline state snapshot. Every session re-discovers what's in data/wgs/analysis/.

Proposed fix: Nightly genomics_status.py --local > pipeline_state.json. Inject into every orchestrated task. Also: run setup-volumes.sh as preamble in every claude -p call.

## Finding 2: Skills Drift Check (3 sessions in 24 hours)
Three separate meta sessions audited whether projects had correct skill symlinks. Session 88f8a442 literally said "again ... we did this already a few times." 42 ls -la .claude/skills/ calls across sessions.

Proposed fix: New orchestrator task type: skills-drift-check. Compare each project's skills against canonical list. Write report. Run nightly. Pure script, no claude -p needed.

## Finding 3: Earnings Calendar Searched 12x, Never Stored (intel)
MRVL earnings searched 3x across sessions. HIMS earnings in 3 sessions. No download_earnings_calendar.py exists. Free data (Nasdaq endpoint). 12 Exa searches × wasted context + search-burst hook triggers.

Proposed fix: Write download_earnings_calendar.py, add to weekly_update.sh. New task: EARNINGS_CALENDAR_REFRESH (Sunday night).

## Finding 4: Subagent Output Race Condition (genomics)
In c6e8f986, 4 agent retries because /private/tmp/.../tasks/*.output got cleaned before parent read it. Expensive — subagent re-runs entire reasoning.

Proposed fix: Orchestrated tasks use claude -p (stdout, not tmp files). Researcher subagents write memos to docs/research/ before completing.

## Finding 5: llmx Timeout Recovery Loops (10-30 min per model review)
Session 6a489280 killed 3 llmx processes, retried with progressively smaller payloads (960K → 700K → 5 sessions). Non-streaming mode buffers entire response.

Proposed fix: (a) Transcript compression layer before supervision-audit dispatch. (b) Always --stream in orchestrated llmx calls. (c) Pre-built context via .context/ Makefile.

## Finding 6: Discovery Scan → Thesis Check Pipeline Not Wired (intel)
discovery_scan.py runs weekly and outputs candidates. Nobody runs /thesis-check on those automatically. Human asks "find more stocks" → agent rebuilds screen from DuckDB → triggers thesis checks manually.

Proposed fix: After discovery_scan.py --add-to-thesis 10, orchestrator generates THESIS_CHECK tasks. Add generate_discovery_tasks().

## Finding 7: DuckDB Column Guessing (11 errors)
"Run DESCRIBE before querying" is in CLAUDE.md. 11 column-not-found errors anyway. Constitution says "instructions alone = 0% reliable."

Proposed fix: For orchestrated tasks, inject schema snapshot into task context. Not an orchestrator fix — separate PreToolUse hook needed.

## Finding 8: Paper Ledger State Not in Session Context (intel)
Agent rediscovers paper_ledger.py every session. Morning brief should include portfolio state.

Proposed fix: SessionStart hook or orchestrated morning task reads paper_ledger.py positions and injects into session context.

## Finding 9: Cross-Project Config Propagation is Manual
Session ca133e87 spent 53 bash calls deploying auto-overview infra from intel to other projects. Repeats monthly.

Proposed fix: project-sync.sh checks each project against canonical infra list. Weekly cron. Execution needs approval.

## Finding 10: The Intel Orchestrator Is Built But Not Scheduled
intel/tools/orchestrator.py already has generate_staleness_tasks(), generate_signal_tasks(), generate_healthcheck_tasks(). None of it runs. The human spent ~400 tool calls across 17 sessions doing work the intel orchestrator was designed to dispatch.

## Finding 11: "Monday Open Brief" Pattern
Sessions 331211bf and 0f2669e1: human asks "find the best assets to act on." Agent spends 40-60 tool calls rebuilding what daily_synthesis.py already generates. The daily brief exists but isn't surfaced at session start.

## Updated Task Type Inventory (proposed additions to orchestrator plan)

| Task Type | Source | Human Input | Schedule |
|-----------|--------|-------------|----------|
| execute_plan | Plan paste sessions | Plan approval only | On demand |
| entity_refresh | Staleness check | None | Daily 6PM |
| thesis_check | Signal scanner alerts | None | Daily after scan |
| discovery_thesis | NEW: discovery_scan output | None | Weekly after scan |
| morning_brief | NEW: daily_synthesis + earnings + positions | None | Daily 8AM trading days |
| earnings_refresh | NEW: Nasdaq calendar | None | Weekly Sunday |
| pipeline_state | NEW: genomics_status.py | None | Nightly |
| research_gap_sweep | NEW: pipeline state vs research log | None | Weekly |
| skills_drift | NEW: canonical list diff | None | Daily |
| supervision_audit | Session-analyst | None | Nightly |
| epistemic_metrics | pushback/lint/SAFE-lite | None | Nightly |
| model_review | Explore/plan output | Synthesis review | On demand |
| project_sync | Infra drift report | Approval required | Weekly |
| monthly_pruning | Already in plan | Review report | Monthly |
