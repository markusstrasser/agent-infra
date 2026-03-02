# CONTEXT: Cross-Model Review of Orchestrator Plan

# PROJECT CONSTITUTION
Quantify alignment gaps. For each principle, assess: coverage (0-100%), consistency, testable violations.

<constitution>
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
</constitution>

# PROJECT GOALS
Assess quantitative alignment. Which goals are measurably served? Which are neglected?

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


# REVIEW TARGET: Orchestrator Plan

# Plan: Orchestrator — Automating Recurring Human Steps

**Session:** 3a65775d-0af8-4f72-9b2c-6b4c36b1be51
**Date:** 2026-03-01
**Project:** meta (implements here, serves all projects)

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

**Not** using Agent SDK. Subprocess `claude -p` is simpler, proven, no dependency, and the SDK is new (hallucination risk in SDK docs — some of those code examples may be fabricated). We can migrate to SDK later if subprocess proves limiting.

**Not** using Agent Teams. Session-scoped, experimental, no cron integration.

**Not** building a DAG engine. Sequential task chaining with output files is sufficient. If we need DAGs later, we add them.

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
    step TEXT,               -- e.g. "explore", "review", "plan", "execute"
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
    last_run TEXT,
    enabled INTEGER DEFAULT 1
);
```

### 2. Core Loop (orchestrator.py)

```python
#!/usr/bin/env python3
"""Orchestrator: cron-driven task runner for claude -p."""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("~/.claude/orchestrator.db").expanduser()
LOG_PATH = Path("~/.claude/orchestrator-log.jsonl").expanduser()
PLANS_DIR = Path(".claude/plans")  # relative to project cwd

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db

def pick_task(db):
    """Pick highest-priority ready task."""
    return db.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND (depends_on IS NULL
               OR depends_on IN (SELECT id FROM tasks WHERE status = 'done'))
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """).fetchone()

def run_task(task):
    """Execute a single task via claude -p."""
    cmd = [
        "claude", "-p", task["prompt"],
        "--output-format", "json",
        "--max-turns", str(task["max_turns"] or 15),
        "--max-budget-usd", str(task["max_budget_usd"] or 5.0),
        "--no-session-persistence",
    ]
    if task["model"]:
        cmd.extend(["--model", task["model"]])
    if task["allowed_tools"]:
        cmd.extend(["--allowedTools", task["allowed_tools"]])

    cwd = task["cwd"] or os.path.expanduser(f"~/Projects/{task['project']}")

    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=cwd, timeout=1800,  # 30 min watchdog
    )
    return result

def log_event(event):
    with open(LOG_PATH, "a") as f:
        event["ts"] = datetime.utcnow().isoformat()
        f.write(json.dumps(event) + "\n")

def main():
    db = get_db()
    task = pick_task(db)
    if not task:
        return  # Nothing to do

    task_id = task["id"]
    db.execute("UPDATE tasks SET status='running', started_at=datetime('now') WHERE id=?", (task_id,))
    db.commit()

    log_event({"action": "start", "task_id": task_id, "pipeline": task["pipeline"], "step": task["step"]})

    try:
        result = run_task(task)
        output = json.loads(result.stdout) if result.stdout.strip() else {}

        # Extract cost/token info from JSON output
        cost = output.get("cost_usd", 0)
        tokens_in = output.get("usage", {}).get("input_tokens", 0)
        tokens_out = output.get("usage", {}).get("output_tokens", 0)
        summary = output.get("result", "")[:2000]

        # Save full output
        output_file = Path(f"~/.claude/orchestrator-outputs/{task_id}.json").expanduser()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(output, indent=2))

        db.execute("""
            UPDATE tasks SET status='done', finished_at=datetime('now'),
                output_file=?, result_summary=?, cost_usd=?,
                tokens_in=?, tokens_out=?
            WHERE id=?
        """, (str(output_file), summary, cost, tokens_in, tokens_out, task_id))

        log_event({"action": "done", "task_id": task_id, "cost_usd": cost,
                    "exit_code": result.returncode})

    except subprocess.TimeoutExpired:
        db.execute("UPDATE tasks SET status='failed', error='timeout_30min' WHERE id=?", (task_id,))
        log_event({"action": "timeout", "task_id": task_id})

    except Exception as e:
        db.execute("UPDATE tasks SET status='failed', error=? WHERE id=?", (str(e)[:500], task_id))
        log_event({"action": "error", "task_id": task_id, "error": str(e)[:200]})

    db.commit()

if __name__ == "__main__":
    main()
```

### 3. Pipeline Templates (the recurring workflows)

#### 3a. Explore → Review → Plan → Execute

This is the 4-step pipeline that currently requires 2-4 manual sessions.

```json
{
  "name": "research-and-implement",
  "steps": [
    {
      "step": "explore",
      "prompt": "Research {topic}. Use WebSearch, Exa, and paper-search MCP tools. Save findings to .claude/plans/{pipeline}-explore.md with source citations.",
      "max_turns": 20,
      "max_budget_usd": 3.0,
      "allowed_tools": "Read,Glob,Grep,WebSearch,WebFetch,mcp__exa__web_search_exa,mcp__research__search_papers"
    },
    {
      "step": "review",
      "prompt": "Read .claude/plans/{pipeline}-explore.md. Cross-check claims against the actual codebase (grep for mentioned files/functions). Use /model-review to get Gemini 3.1 Pro and GPT-5.2 critique. Write verified findings to .claude/plans/{pipeline}-review.md.",
      "max_turns": 25,
      "max_budget_usd": 8.0
    },
    {
      "step": "plan",
      "prompt": "Read .claude/plans/{pipeline}-review.md. Write an implementation plan to .claude/plans/{pipeline}-plan.md. For every claim about existing code, verify with grep/read. Include: file list, execution order, verification steps, rollback approach.",
      "max_turns": 15,
      "max_budget_usd": 3.0,
      "allowed_tools": "Read,Glob,Grep,Write"
    },
    {
      "step": "execute",
      "prompt": "Execute the plan at .claude/plans/{pipeline}-plan.md. Check git log for any changes since the plan was written. Implement, test, commit with [feature-name] prefix.",
      "max_turns": 15,
      "max_budget_usd": 5.0
    }
  ]
}
```

**Human checkpoint:** Between steps 3 (plan) and 4 (execute), the orchestrator can pause for human review. Config: `"pause_before": ["execute"]` in the pipeline definition. When paused, the task sits in `pending` until the human runs `orchestrate.py --approve <pipeline>`.

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
      "prompt": "Run /session-analyst on today's sessions across all projects. Append findings to improvement-log.md. If any finding recurs 2+ times, draft a CLAUDE.md rule change or hook proposal.",
      "max_turns": 20,
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
  "schedule": "0 8 * 1 *",
  "steps": [
    {
      "step": "search",
      "prompt": "Search arxiv for last 7 days: 'LLM agents', 'coding agents', 'tool use', 'agentic AI'. Search Exa for Anthropic blog posts, Simon Willison, Trail of Bits, Kapoor/Narayanan. Save papers to corpus. Write findings to .claude/plans/research-sweep.md.",
      "max_turns": 25,
      "max_budget_usd": 5.0,
      "allowed_tools": "Read,Write,Glob,Grep,WebSearch,WebFetch,mcp__exa__web_search_exa,mcp__research__search_papers,mcp__research__save_paper,mcp__paper-search__search_arxiv"
    },
    {
      "step": "triage",
      "prompt": "Read .claude/plans/research-sweep.md. For each finding: does it change our hooks, skills, routing, or architecture? If yes, write a proposal. Commit to meta with [research-sweep] prefix.",
      "max_turns": 10,
      "max_budget_usd": 2.0,
      "model": "sonnet"
    }
  ]
}
```

### 4. Hook Upgrades (Error Paste-Back Elimination)

Currently, when hooks block the agent, the user has to paste the error output back. Fix: upgrade all blocking hooks to use `additionalContext`.

**Files to change:**

| Hook | Current | Change |
|------|---------|--------|
| `stop-research-gate.sh` | `echo "BLOCKED: ..." >&2` | Add JSON `additionalContext` output alongside stderr |
| `pretool-data-guard.sh` | `echo "BLOCKED: ..." >&2` | Same |
| `postwrite-source-check.sh` | `echo "BLOCKED: ..." >&2` | Same |
| `pretool-search-burst.sh` | `echo "WARNING: ..." >&2` | Already partially done; ensure JSON output |

**Pattern:**
```bash
# Old:
echo "BLOCKED: reason" >&2
exit 2

# New:
echo '{"additionalContext": "BLOCKED: reason. Fix: do X instead."}' >&2
exit 2
```

Wait — PreToolUse hooks that block (exit 2) already have their output visible to the agent via the block message. The paste-back issue is specifically with **Stop hooks** where the block message may not be visible in the next prompt. Verify this is actually a problem before changing anything.

**Action:** Test Stop hook output visibility in a controlled session. If the agent sees the block reason automatically, no change needed. If not, add `additionalContext`.

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

### 6. Auto-Commit Post-Task

After an orchestrator execution task succeeds, check for uncommitted changes and commit them.

```python
# In orchestrator.py, after successful execute step:
def auto_commit(cwd, pipeline_name):
    """Commit if there are staged/unstaged changes from the task."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=cwd
    )
    if status.stdout.strip():
        subprocess.run(
            ["git", "add", "-A"], cwd=cwd  # orchestrator tasks = controlled scope
        )
        subprocess.run(
            ["git", "commit", "-m", f"[{pipeline_name}] Orchestrated task completion"],
            cwd=cwd
        )
```

**Only for orchestrator tasks.** Interactive sessions keep current behavior (commit on explicit request).

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
| `--no-session-persistence` | No | Ephemeral orchestrated tasks |
| `--allowedTools` | No | Scope tools per task type |
| `--fallback-model` | No | Add for resilience |
| `--worktree` | No | Could use for execute steps (isolation) |
| `--agents` | No | Could inline agent defs per task |
| Agent Teams | No conflict — orthogonal | Teams = within-session fan-out. Orchestrator = cross-session scheduling. |
| `/batch` | No conflict | `/batch` = interactive parallel refactor. Orchestrator = scheduled pipeline. |
| Hooks | No conflict | Hooks fire inside orchestrated `claude -p` sessions normally |
| Subagent memory | Complementary | Orchestrated tasks spawn subagents that accumulate memory |
| `--json-schema` | Useful | Structured output for verification steps |

**No conflicts found.** The orchestrator operates at a layer above Claude Code — it's a scheduler that invokes Claude Code. Everything inside the invocation uses native features normally.

## Implementation Order

### Phase 1: Core (~2 hours)
- [ ] `scripts/orchestrator.py` — core loop (pick, run, log)
- [ ] `scripts/schema.sql` — task queue DDL
- [ ] `scripts/orchestrator.py submit/run/status/log` — CLI interface
- [ ] Test: submit one task, verify it runs and logs

### Phase 2: Pipelines (~1 hour)
- [ ] `pipelines/` directory with JSON templates
- [ ] `depends_on` chaining (task N+1 waits for task N)
- [ ] `pause_before` config for human approval gates
- [ ] File-based output passing (step N writes to `.claude/plans/`, step N+1 reads)
- [ ] Test: run explore→plan→execute chain end-to-end

### Phase 3: Scheduling (~30 min)
- [ ] launchd plist
- [ ] `orchestrator.py schedule` — list/enable/disable scheduled pipelines
- [ ] Test: verify launchd fires every 15 minutes, picks up pending tasks

### Phase 4: Retro + Hooks (~1 hour)
- [ ] `/retro` skill
- [ ] Test Stop hook `additionalContext` visibility (may be unnecessary)
- [ ] Upgrade hooks if needed
- [ ] Auto-commit post-task function
- [ ] Ground-truth verification step template

### Phase 5: Pipeline Library (~1 hour)
- [ ] `research-and-implement` pipeline template
- [ ] `entity-refresh` pipeline template
- [ ] `session-retro` pipeline template
- [ ] `research-sweep` pipeline template
- [ ] Wire session-analyst into nightly retro

## Success Criteria (30 days)

1. **Plan-paste sessions drop by >50%.** Measured via supervision audit: "Implement the following plan:" messages should decline.
2. **Commit-only sessions drop to zero.** Orchestrated tasks auto-commit.
3. **Retro snippet disappears from clipboard.** Replaced by `/retro` or nightly pipeline.
4. **Error paste-back incidents = 0.** Hooks inject context directly.
5. **Daily cost stays under $25.** Orchestrated tasks have budget caps.
6. **No silent failures.** Every failed task has an error in the DB + JSONL log.

## Risks

1. **Laptop sleep kills tasks.** Mitigation: `subprocess.run(timeout=1800)` + task status = 'failed' on timeout. Launchd restarts on wake.
2. **Cost runaway.** Mitigation: `--max-budget-usd` per task, daily cap check in orchestrator.
3. **Stale plans.** Mitigation: verification step checks git log for changes since plan creation.
4. **Wrong project commits.** Mitigation: `cwd` per task is explicit. No cross-project commits.
5. **Agent SDK obsoletes this.** Fine — the 150-line script is disposable. If SDK adds scheduling, migrate.


# KEY DATA POINTS

- 80+ sessions analyzed across 4 projects
- 44% of sessions start with plan-paste
- Supervision audit: 21% → 5.9% wasted in 2 days
- 7+ commit-only sessions observed
- Average session cost: $1-$42 (median ~$5)
- Claude Code v2.1.63 with claude -p, --max-turns, --max-budget-usd, --output-format json, --json-schema, --worktree, --agents, --no-session-persistence
- Agent SDK exists (Python/TS) but new — plan chooses subprocess for simplicity
- macOS, single operator, launchd for scheduling
- Laptop (goes to sleep — tasks can be interrupted)
