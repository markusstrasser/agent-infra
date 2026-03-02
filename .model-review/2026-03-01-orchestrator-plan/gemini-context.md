# CONTEXT: Cross-Model Review of Orchestrator Plan

# PROJECT CONSTITUTION
Review against these principles, not your own priors.

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


# EXISTING DESIGN DOCS

## maintenance-checklist.md (Orchestrator section)

## Ideas / Future Work

### Orchestrator MVP
A Python script (not an LLM session) that runs the agent autonomously. Each task gets a fresh context — no context rot.

**What it does:**
```
Every 15 minutes (cron):
  1. Query SQLite task queue (what's stale? what signals fired?)
  2. Pick highest-priority task
  3. Run: claude -p "Update HIMS entity" --max-turns 15 --output-format json
  4. Kill if stuck (subprocess timeout 30min)
  5. Log result, pick next task
```

**MVP spec (from review-synthesis.md):** ~100 lines Python. Cron + SQLite + subprocess. No DAG, no diversity monitor, no Agent SDK (premature optimizations).

**Status: UNBLOCKED.** The orchestrator is meta-level infrastructure, independent of any specific project's validation status. Build for tasks that are clearly automatable: research sweeps, self-improvement passes, entity refresh, data maintenance. (Decision: goals elicitation 2026-02-28)

**Key design decisions (already validated by multi-model review):**
- Fresh `claude -p` per task, NOT `--resume` (quadratic cost)
- 15 turns max per task (context degrades beyond this)
- Self-improvement is a dedicated fresh-context task every 5 tasks, not a wrap-up prompt
- subprocess.run(timeout=1800) as watchdog
- JSONL event log for debugging
- Daily markdown summary for human review

See `autonomous-agent-architecture.md` and `review-synthesis.md` for full design.

### IB API Integration (Future Phase)
Interactive Brokers API for agent-managed trading. $10K sandbox account. Outbox pattern: agent proposes → queue → execute. Pending paper trading validation proving consistent edge.

### Fraud/Corruption Separation (Decide Later)
Currently in intel as analysis/fraud/, analysis/sf/. May become separate repo if compute burden grows. Entity graph is shared regardless. Not urgent — the join is the moat.

## Key URLs to Monitor
- Claude Code releases: `anthropic.com/claude-code` (no public changelog URL — check `claude --version`)
- Codex CLI: `github.com/openai/codex` (or wherever they publish)
- Gemini CLI: `github.com/google/gemini-cli` (or wherever they publish)
- Agent benchmarks: SWE-bench, BFCL, Terminal-Bench
- Security: Trail of Bits blog, OWASP LLM Top 10



## Claude Code Native Features Assessment

# Claude Code Native Features vs Meta Infrastructure

> Assessment date: 2026-03-01. Based on actual documentation (code.claude.com), not changelog extrapolation.

## Summary

Claude Code is building primitives (hooks, subagents, memory) but meta's governance layer (what to enforce, when to promote, how to self-improve) has no native equivalent. Real consolidation opportunity is ~10-15%, mostly in memory mechanics and testing bundled skills against backlog items.

## 1. Agent Teams — NOT an orchestrator replacement

**Status:** Experimental, behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

Multiple Claude Code instances in one terminal sharing a task list and mailbox. One fixed lead + teammates. Each teammate = separate context window + full API cost.

**Known limitations (from docs):**
- No `/resume` with in-process teammates
- Task status can lag
- One team per session, no nested teams, lead fixed
- Split panes unsupported in VS Code, Windows Terminal, Ghostty

**Why not an orchestrator replacement:** Our orchestrator is cross-session, cross-project, cron-driven, SQLite task queue, fresh context per task. Agent teams are session-scoped — terminal closes, team gone.

**Possible use:** Within-session fan-out. `/batch` bundled skill more interesting — decomposes into 5-30 units, each in worktree, each opens PR.

## 2. Subagents — Mature, highest leverage

**Production-ready.** New since last audit:
- **Persistent memory** via `memory: user|project|local`. Per-subagent MEMORY.md across sessions.
- **Hooks in frontmatter** scoped to lifecycle. `Stop` auto-converts to `SubagentStop`.
- **Skills preloading** — full content injected at startup.
- **Worktree isolation** — `isolation: "worktree"`.
- **Transcripts** survive main compaction.
- **Resume** retains full history.

**Key gap:** Skills cannot have persistent memory. Only subagents get `memory` field. Refactor to subagent for cross-session learning.

## 3. Skills Platform — Mature, minor gaps

**New fields:**
- `model` — pin skill to specific model
- `hooks` — embed lifecycle hooks in frontmatter
- `argument-hint` — autocomplete hints

**Token budget:** 2% of context window (~16K chars) for all skill descriptions. Check `/context` for truncation.

**Bundled skills:**
- `/batch <instruction>` — parallel agents in worktrees, each opens PR
- `/simplify` — 3 parallel review agents (reuse, quality, efficiency)
- `/debug [description]` — session troubleshooting

## 4. Hook System — Significant new capabilities

**4 hook types now:**

| Type | What | Use for |
|------|------|---------|
| `command` | Shell script, JSON stdin | Deterministic checks (existing) |
| `http` | POST to URL | Remote validation services |
| `prompt` | Single-turn Haiku eval | Semantic checks too complex for bash |
| `agent` | Multi-turn with Read/Grep/Glob, 50 turns | Complex verification (the stop-hook-verifier from cockpit.md backlog) |

**`additionalContext`** on PreToolUse/PostToolUse — injects warning directly into Claude's context (better than stderr).

**`once: true`** — fires once per session then removed. Skills-only.

**Shell-only events (9/17):** SessionStart, SessionEnd, PreCompact, ConfigChange, Notification, SubagentStart, TeammateIdle, WorktreeCreate, WorktreeRemove.

## 5. Native Memory

Same storage path we use. Claude manages topic files, 200-line limit, auto-splitting. Machine-local, no git.

**Verdict:** Native handles mechanics. Our governance (recurs 2+, checkable predicate, evidence requirements) stays in CLAUDE.md. Complementary, not competing.

## 6. Native Observability

| Component | Custom | Native | Replace? |
|-----------|--------|--------|----------|
| Statusline | `statusline.sh` | Native JSON API | Already native. Script is customization. |
| Receipts | SessionEnd → JSONL | OTel (needs collector) | Keep JSONL. OTel overkill for single-user. |
| Dashboard | `dashboard.py` | `/stats`, `/insights` | Keep. `/stats` basic, `/insights` interesting but different. |
| Spinning detector | PostToolUse hook | None | Keep. |
| Idle notification | Stop hook | None | Keep. |

**OTel metrics available** (if we ever set up a collector): session count, lines changed, PR/commit count, cost by model, token usage, edit accept/reject, active time. Comprehensive but needs infrastructure.

## 7. Plugins

Bundle skills + agents + hooks + MCP + LSP. Distribution mechanism, not capability. Adds namespace overhead. Skip unless distributing to others.

## Concrete Actions

### High value, low effort
1. Test `/batch` for orchestrator-style parallel work
2. Test `/simplify` after feature implementation
3. Add `model` field to pinned skills
4. Try `additionalContext` in spinning-detector

### High value, moderate effort
5. Refactor researcher to custom subagent for persistent memory
6. Add prompt hooks for semantic checks (commit message quality)
7. Add hooks to skill frontmatter for per-skill validation

### Monitor / evaluate later
8. Agent teams — wait for stable
9. OTel — only if wanting Grafana
10. Plugins — only if distributing
11. `/insights` — test overlap with session-analyst

## What Meta Keeps (no native replacement)

- Cross-session orchestrator (cron-driven)
- Session-analyst pipeline
- Hook governance (promotion criteria, ROI telemetry)
- Cockpit receipts + dashboard
- Spinning detector, idle notification, custom stop hooks
- Cross-project propagation
- improvement-log → architectural fix pipeline

## GOALS.md Exit Condition Status

"Meta becomes unnecessary when Claude Code ships native equivalents" — not close. Primitives are building but governance layer is where meta's value lives.

---

*Sources: code.claude.com/docs/en/{skills, hooks, hooks-guide, sub-agents, agent-teams, memory, statusline, telemetry}. All fetched 2026-03-01.*


## Improvement Log (evidence of manual patterns)

# Improvement Log

Findings from session analysis. Each tracks: observed → proposed → implemented → measured.
Source: `/session-analyst` skill analyzing transcripts from `~/.claude/projects/`.

## Findings
<!-- session analyst appends below -->

### [2026-02-28] TOKEN WASTE: Iterative regex parsing via repeated Bash one-liners
- **Session:** intel 16552a95
- **Evidence:** 9 reads of `setup_duckdb.py`, 6 separate `python3 -c "import re..."` Bash commands to iteratively test regex parsing of view names from Python source. Each attempt failed, requiring a new iteration with slightly modified regex.
- **Failure mode:** Token waste — iterative debugging via tool calls instead of writing a script
- **Proposed fix:** CLAUDE.md change: "When extracting structured data from Python source, use `ast` module or write a standalone script. Never iterate regex via inline Bash one-liners."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] OVER-ENGINEERING: Regex parsing of Python source instead of AST
- **Session:** intel 16552a95
- **Evidence:** Agent used complex regexes with line-lookaheads and paren-counting to extract view names and directory paths from `setup_duckdb.py` f-strings. Repeatedly failed on edge cases. The `ast` module or simply importing the file's data structures would have been simpler and correct.
- **Failure mode:** Over-engineering — fragile approach when robust alternative exists
- **Proposed fix:** CLAUDE.md change: "Prefer `ast` module or direct import over regex when parsing Python source code."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] TOKEN WASTE: Repeated find commands instead of saving to temp file
- **Session:** intel deb3fac6
- **Evidence:** 9 `find /Volumes/SSK1TB/corpus/` commands with minor variations (`wc -l`, `sed`, `stat`, `printf`) instead of saving the file list to `/tmp/` once and processing it. Each re-traverses 6,031 files.
- **Failure mode:** Token waste — filesystem re-traversal
- **Proposed fix:** rule: "Save `find`/`ls` output to `/tmp/` file when you need multiple passes over the same listing."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] SYCOPHANCY: No pushback on "ALWAYS BE DOWNLOADING" bulk hoarding directive
- **Session:** intel f32653c6
- **Evidence:** User said "DO NOT STOP, ALWAYS BE DOWNLOADING." Agent immediately complied, spawning 105+ task dispatches and 123 inline Python download scripts across 13 context continuations. No discussion of: data quality, schema alignment, storage cost, API rate limits, or whether the downloaded datasets had integration plans. Session burned through context 13 times and hit usage limits 145 times.
- **Failure mode:** Sycophancy — compliance with directive that warranted pushback
- **Proposed fix:** rule: "Pushback required when download requests lack integration plan. Ask: What view will this create? What entity does it join to? If no answer, deprioritize."
- **Severity:** high
- **Status:** [x] implemented — intel CLAUDE.md "Download Discipline" section (2026-02-28). Instructions-only; acknowledged weakness per EoG.

### [2026-02-28] TOKEN WASTE: 123 inline Python scripts via Bash instead of writing .py files
- **Session:** intel f32653c6
- **Evidence:** 123 `Bash: uvx --with requests python3 -c "import requests, os..."` one-liners for individual downloads instead of writing download functions to a `.py` file. 496 total Bash calls in the session. Each inline script wastes tokens on boilerplate and is not reusable.
- **Failure mode:** Token waste — inline scripts where file-based scripts would save tokens and be maintainable
- **Proposed fix:** CLAUDE.md change: "Multi-line Python (>10 lines) must go in a .py file, not inline Bash. Exception: one-shot queries."
- **Severity:** high
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] TOKEN WASTE: Polling failed tasks after hitting usage limits
- **Session:** intel f32653c6
- **Evidence:** 145 "out of extra usage" messages. Agent continued attempting to read task outputs and retry failed downloads instead of halting and informing the user. Burned tokens on identical failure loops.
- **Failure mode:** NEW: Usage-limit spin loop — agent keeps polling when API limits are hit
- **Proposed fix:** hook: Detect repeated usage-limit errors and halt with user notification instead of retrying.
- **Severity:** high
- **Status:** [x] partially implemented — PostToolUse:Bash hook (`posttool-bash-failure-loop.sh`) detects 5+ consecutive Bash failures. Deployed to intel (2026-02-28). Does NOT catch API-level usage limits (system messages, not tool outputs).

### [2026-02-28] BUILD-THEN-UNDO: Download scripts rewritten for broken URLs
- **Session:** intel f32653c6
- **Evidence:** `download_new_alpha_datasets.py` written, run, URLs found broken (FERC, USITC, PatentsView, FL Sunbiz, NRC), script edited, re-run, more broken URLs found, edited again. Pattern repeated across multiple download scripts.
- **Failure mode:** Build-then-undo — URL validation should precede bulk download script writing
- **Proposed fix:** architectural: HEAD-request validation step before writing download scripts. Already partially addressed in `data_sources.md` lessons.
- **Severity:** medium
- **Status:** [x] implemented — intel CLAUDE.md "Download Discipline" rule: validate URLs with HEAD before bulk scripts (2026-02-28)

### [2026-02-28] SYCOPHANCY: Built heuristic auto-classification rules without epistemic challenge
- **Session:** selve a2679f18
- **Evidence:** After user asked "what can we do now that's better?", agent proposed and immediately implemented 3 heuristic rules to auto-demote variants as LIKELY_BENIGN (HLA region, alt contigs, tolerant + AM benign). Only after user pushback did agent articulate why these were epistemically unsound: "HLA gene -> LIKELY_BENIGN is a population-level prior, not evidence about the specific variant. HLA genes *do* cause disease." Agent had the knowledge to pushback before building but didn't.
- **Failure mode:** Sycophancy — compliance without epistemic challenge on safety-critical classification
- **Proposed fix:** [rule] "Distinguish mechanistic vs. heuristic changes before implementing. Mechanistic (parser fix, known-good data source) can proceed. Heuristic (new classification rule based on correlation/prior) requires stating the false-negative risk and requesting confirmation."
- **Severity:** high
- **Status:** [ ] rejected — one-off domain judgment, not a recurring pattern. General sycophancy pushback rule already covers this.

### [2026-02-28] BUILD-THEN-UNDO: Implemented and reverted heuristic auto-classification rules
- **Session:** selve a2679f18
- **Evidence:** Agent added `_is_alt_contig()`, `_is_tolerant_missense_benign()`, `_PRIMARY_CHROMS`, and modified `auto_classify()` to add 3 new LIKELY_BENIGN rules. After user pushback, all code was reverted and dead helpers cleaned up. The priority tiering function survived, but the filtering rules were wasted. Estimated ~4K output tokens on code that was deleted.
- **Failure mode:** Build-then-undo — direct consequence of missing pushback (above)
- **Proposed fix:** Same as above — epistemic challenge before building prevents the undo
- **Severity:** medium
- **Status:** [ ] rejected — linked to above

### [2026-02-28] TOKEN WASTE: 4 consecutive Read calls on same 700-line file
- **Session:** selve a2679f18
- **Evidence:** Lines 132-146 of transcript show 4 back-to-back `Read(generate_review_packets.py)` calls before a single Edit. The file was already in context from the first Read. Later in the session, similar patterns appear: Read -> Edit -> Read -> Edit on the same file when content was already available.
- **Failure mode:** Token waste — redundant file reads
- **Proposed fix:** [architectural] Before issuing Read, check if the file content is already in recent context. Use Grep for targeted lookups instead of full file reads when only checking a specific function or line.
- **Severity:** medium
- **Status:** [ ] deferred — a PreToolUse:Read hook would be too noisy (many legitimate re-reads). Claude Code already instructs agents to prefer Grep. Not worth the false-positive cost.

### [2026-02-28] RULE VIOLATION: Committed code without explicit user request
- **Session:** selve a2679f18
- **Evidence:** Agent committed at multiple points ("git add ... && git commit") without the user explicitly asking for commits. The user provided a plan and said "Implement the following plan" — the agent interpreted this as license to commit at each phase boundary. While the branch workflow in CLAUDE.md says "Git commit changes (semantic, granular)" when done, the global rule says "NEVER commit changes unless the user explicitly asks." The agent auto-committed 5+ times during implementation.
- **Failure mode:** Rule violation — auto-committing without explicit request
- **Proposed fix:** [rule clarification] The branch workflow instruction ("commit changes") and the global "never commit unless asked" are in tension. Resolve: branch workflow implicitly authorizes commits when user requests branch-based implementation.
- **Severity:** low (commits were well-structured and appropriate for branch workflow)
- **Status:** [x] implemented — clarified in global CLAUDE.md: branch workflow implicitly authorizes commits (2026-02-28)

### [2026-02-28] Supervision Audit
- **Period:** 1 day, 68 sessions, 348 user messages
- **Wasted:** 21.0% (target: <15%)
- **Top patterns:**
  1. **context-exhaustion (45):** User pasting "This session is being continued from a previous conversation that ran out of context" boilerplate. 33 in intel, 10 in selve, 3 in meta. The existing checkpoint.md + PreCompact hook generates the checkpoint, and CLAUDE.md tells the agent to read it, but the user still manually pastes continuation summaries. Root cause: no mechanism auto-injects checkpoint context at session start.
  2. **commit-boilerplate (12):** User pasting "IFF everything works: git commit..." block across 10 sessions. All rules already exist in global CLAUDE.md. Trust problem, not tooling problem — but a `/commit` command alias or explicit "when user says 'commit', follow CLAUDE.md commit rules" could reduce friction.
  3. **context-resume (4):** "Continue from where you left off" — overlaps with context-exhaustion.
  4. **rubber-stamp (6):** "ok", "do it", "go" — natural approvals, not clearly automatable without removing intentional oversight.
  5. **corrections (6 unique):** idempotency-check (2), completeness-verify (1), depth-nudge (1), env-uv-not-conda (1), capability-nudge (1) — below recurrence threshold, noise not signal.
- **Per-project:** intel 28.9%, selve 26.9%, meta 12.8%
- **Gemini synthesis:** Proposed SessionStart hook + commit skill. SessionStart hook is architecturally sound but SessionStart events can't inject prompt content (command-only). Commit skill is overkill given existing CLAUDE.md rules.
- **Fixes implemented:**
  1. [ARCHITECTURAL] UserPromptSubmit hook (`userprompt-context-warn.sh`) detects continuation boilerplate, warns user if checkpoint.md exists. Non-blocking. Deployed globally.
  2. [RULE] Strengthened CLAUDE.md Context Continuations instruction: agent infers task from git state, doesn't ask user for context.
  3. [RULE] Added "when user says 'commit', follow these rules" line to CLAUDE.md Git Commits section.
- **Status:** [x] implemented (2026-02-28)

### [2026-03-01] Supervision Audit
- **Period:** 1 day, 88 sessions, 355 user messages
- **Wasted:** 5.9% (target: <15%) -- down from 21.0% on 2026-02-28
- **Classifier fixes deployed this audit:**
  1. **context-continuation false positive.** Previous audit's 25 RE_ORIENT "context-exhaustion" messages were auto-continuation summaries injected by Claude Code, not human typing. Fixed: added SYSTEM classification for "session is being continued from a previous conversation". This alone dropped wasted% from 12.6% to 6.5%.
  2. **idempotency-check false positive.** "already exists as dormant code" in user-pasted context triggered `already (have|download|exist)` regex. Tightened to `we already (have|download)`. Dropped 2 more false positives.
- **Top remaining patterns (corrected):**
  1. **commit-boilerplate (7):** Same clipboard paste as 2026-02-28. Rule exists in CLAUDE.md. User habit, not agent failure. 6 sessions, identical text. No new fix needed -- the 2026-02-28 CLAUDE.md rule addition is the right fix; user adoption is the bottleneck.
  2. **rubber-stamp (7):** "ok", "do it", "go ahead" -- intentional approval checkpoints. Not automatable without removing oversight the user wants.
  3. **context-resume (3):** "Continue from where you left off" -- checkpoint.md mechanism exists but user still types this. The 2026-02-28 UserPromptSubmit hook should be catching this. Possible: hook not deployed to all projects.
  4. **corrections (4 unique):** completeness-verify (1), depth-nudge (1), env-uv-not-conda (1), capability-nudge (1). All singletons, noise not signal.
- **Trend:** Wasted supervision 21.0% -> 5.9% in 2 days. ~60% of the drop is classifier accuracy (false positives removed), ~40% is genuine improvement from 2026-02-28 fixes (commit rule, context continuation rule, UserPromptSubmit hook).
- **Gemini synthesis (cross-checked):**
  - Proposed commit-boilerplate DEFAULT fix -- rejected, rule already exists (CLAUDE.md git_rules section).
  - Proposed context-exhaustion ARCHITECTURAL fix -- moot, these were false positives in the classifier.
  - Proposed build-failure SKILL and tool-error HOOK -- both from one selve/genomics session (a2679f18), not recurring. Below threshold.
- **Fixes deployed:**
  1. [CLASSIFIER] `extract_supervision.py`: Added SYSTEM classification for auto-continuation messages
  2. [CLASSIFIER] `extract_supervision.py`: Tightened idempotency-check regex to avoid context-paste false positives
- **No new automation fixes warranted.** At 5.9% wasted, the remaining patterns are either (a) user habits that rules already address, (b) intentional approval checkpoints, or (c) singletons below recurrence threshold. Further investment in automation has diminishing returns until new patterns emerge.
- **Status:** [x] reviewed


## Session Receipts (recent, for context on volume)

{"ts":"2026-03-01T08:43:02","session":"04f94b15-7dd6-4e25-97af-05953d28546a","project":"meta","model":"Opus 4.6","branch":"main","reason":"clear","duration_min":30.9,"cost_usd":7.2659740500000005,"context_pct":60,"lines_added":470,"lines_removed":0,"transcript_lines":899}
{"ts":"2026-03-01T08:52:34","session":"0cdad11b-2e70-4428-89c1-385212efa053","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":54.2,"cost_usd":8.938919149999997,"context_pct":36,"lines_added":796,"lines_removed":22,"transcript_lines":288,"commits":["6680085 [meta-mcp] Add meta knowledge MCP server"]}
{"ts":"2026-03-01T08:52:36","session":"ce64b616-2909-4bed-ba1d-f1f21f63a64c","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":419.6,"cost_usd":21.094819100000006,"context_pct":73,"lines_added":3941,"lines_removed":58,"transcript_lines":1948,"commits":["6680085 [meta-mcp] Add meta knowledge MCP server"]}
{"ts":"2026-03-01T08:52:42","session":"9144c768-3ec4-498b-81b3-c9a45da82b5d","project":"genomics","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":565.0,"cost_usd":13.869425699999999,"context_pct":32,"lines_added":221,"lines_removed":226,"transcript_lines":2222,"commits":["211457c [project-upgrade] feat: add preflight import validator for modal scripts"]}
{"ts":"2026-03-01T08:52:44","session":"fd820f62-c5fe-460c-8a56-ed5fde42afde","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":399.9,"cost_usd":7.3189989,"context_pct":59,"lines_added":1323,"lines_removed":98,"transcript_lines":686,"commits":["6680085 [meta-mcp] Add meta knowledge MCP server"]}
{"ts":"2026-03-01T09:22:35","session":"24e3746a-26b2-4c42-bfa6-989af7c220f4","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":0.3,"cost_usd":0.48021575,"context_pct":43,"lines_added":0,"lines_removed":0,"transcript_lines":1663}
{"ts":"2026-03-01T09:22:56","session":"4dcf4bb6-d763-4681-a0c4-b74d6d8f4683","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":30.0,"cost_usd":1.9947073,"context_pct":46,"lines_added":9,"lines_removed":3,"transcript_lines":455}
{"ts":"2026-03-01T09:44:01","session":"c6041d33-7ae9-41e2-994e-fdf89f0cca65","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":11.1,"cost_usd":3.6022155,"context_pct":59,"lines_added":709,"lines_removed":56,"transcript_lines":662,"commits":["44dd838 [data-infra] Add auto_view.py \u2014 auto-detect dataset formats + generate view SQL"]}
{"ts":"2026-03-01T10:00:54","session":"a5a5a931-ba20-4121-8de4-29ade2a84910","project":"Projects","model":"Opus 4.6","branch":"\u2014","reason":"other","duration_min":12.9,"cost_usd":1.3908784999999995,"context_pct":30,"lines_added":0,"lines_removed":0,"transcript_lines":320}
{"ts":"2026-03-01T10:03:13","session":"4dcf4bb6-d763-4681-a0c4-b74d6d8f4683","project":"intel","model":"Opus 4.6","branch":"main","reason":"clear","duration_min":67.8,"cost_usd":7.4019783,"context_pct":75,"lines_added":423,"lines_removed":189,"transcript_lines":1072,"commits":["44dd838 [data-infra] Add auto_view.py \u2014 auto-detect dataset formats + generate view SQL"]}
{"ts":"2026-03-01T10:27:46","session":"9d0e5391-2c57-4d91-ae9d-668daa18463b","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":1.7,"cost_usd":0.629358,"context_pct":26,"lines_added":1,"lines_removed":1,"transcript_lines":39}
{"ts":"2026-03-01T10:27:54","session":"83492631-2c60-4e2d-a532-e2e8ed3b810e","project":"selve","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":30.7,"cost_usd":1.2342627500000003,"context_pct":31,"lines_added":0,"lines_removed":0,"transcript_lines":55}
{"ts":"2026-03-01T10:42:19","session":"0769f753-b44a-4b64-88a6-2e0ee6617649","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":101.4,"cost_usd":13.662948549999996,"context_pct":65,"lines_added":1010,"lines_removed":196,"transcript_lines":1200,"commits":["bdce54c [data-wiring] Regenerate schema cache \u2014 385 views (was ~295)","bbac286 [data-wiring] Add dataset_inventory.py \u2014 diagnostic for wired vs unwired datasets","69c3ed2 [data-wiring] Add Open Payments + FAC terminal confirmations to falsify_npi","5b97185 [data-wiring] Add 4 scanners + fix congressional to include Senate","456a280 [data-wiring] Add 15 views + fix FINRA/congressional/FAERS integrations"]}
{"ts":"2026-03-01T12:03:34","session":"b1294cc8-421c-4238-a040-2d5f7ba1ed50","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":33.1,"cost_usd":0.0,"context_pct":0,"lines_added":0,"lines_removed":0,"transcript_lines":1}
{"ts":"2026-03-01T12:15:39","session":"694bec9c-d20c-49f5-ae14-cae5ac50f2f3","project":"meta","model":"Opus 4.6","branch":"main","reason":"clear","duration_min":0.1,"cost_usd":0.0,"context_pct":0,"lines_added":0,"lines_removed":0,"transcript_lines":5}
{"ts":"2026-03-01T12:16:11","session":"24519d11-0bb9-4d14-aa9d-09eea5c9c52a","project":"people","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":0.8,"cost_usd":0.27540375,"context_pct":20,"lines_added":0,"lines_removed":0,"transcript_lines":36}
{"ts":"2026-03-01T12:16:17","session":"079dda42-aefe-4ea5-b8cc-996df56e4dac","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":71.4,"cost_usd":1.9850807499999996,"context_pct":33,"lines_added":200,"lines_removed":14,"transcript_lines":281}
{"ts":"2026-03-01T12:16:23","session":"2fd6f3ee-57fd-4f18-bc2c-c029c947eee2","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":3.9,"cost_usd":1.0604015,"context_pct":31,"lines_added":0,"lines_removed":0,"transcript_lines":76}
{"ts":"2026-03-01T12:22:39","session":"589a34dc-4482-4104-b003-a5ad62caa63a","project":"meta","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":0.4,"cost_usd":0.25488975,"context_pct":24,"lines_added":0,"lines_removed":0,"transcript_lines":8}
{"ts":"2026-03-01T12:26:17","session":"b25be6a7-97a6-4155-844e-5967c5e16848","project":"intel","model":"Opus 4.6","branch":"main","reason":"prompt_input_exit","duration_min":19.5,"cost_usd":2.0942350000000003,"context_pct":26,"lines_added":61,"lines_removed":1,"transcript_lines":33}


## Current Hook Inventory

<reference_data>
## Cross-Project Architecture
| Layer | Location | Syncs how |
|-------|----------|-----------|
| Global CLAUDE.md | `~/.claude/CLAUDE.md` | Loaded in every project (universal rules) |
| Shared skills | `~/Projects/skills/` | Symlinked into each project's `.claude/skills/` |
| Shared hooks | `~/Projects/skills/hooks/` | Referenced by path in each project's `settings.json` |
| Project rules | `.claude/rules/` per project | Diverges intentionally (domain-specific) |
| Project hooks | `.claude/settings.json` per project | Per-project, similar patterns |
| Global hooks | `~/.claude/settings.json` | Loaded in every project |
| Research MCP | `~/Projects/papers-mcp/` | Configured in `.mcp.json` per project |
| Genomics pipeline | `~/Projects/genomics/` | Extracted from selve 2026-02-28 |

## Intel-Local Skills

| Shared skill | Intel-local variant | Difference |
|-------------|---------------------|------------|
| `competing-hypotheses` | `intel/.claude/skills/competing-hypotheses/` | Adds Bayesian LLR scoring via `ach_scorer.py` |
| (none) | `intel/.claude/skills/thesis-check/` | Full adversarial trade-thesis stress-test (432 lines) |
| `model-review` | `intel/.claude/skills/multi-model-review/` | Intel-specific review routing |

## Shared Hooks Inventory

Scripts in `~/Projects/skills/hooks/`. Referenced by absolute path from settings.json.

| Hook | Event | Blocks? | Deployed where | What it does |
|------|-------|---------|----------------|--------------|
| `pretool-bash-loop-guard.sh` | PreToolUse:Bash | exit 2 | Global | Blocks multiline for/while/if (zsh parse error #1) |
| *(inline)* bare-python-guard | PreToolUse:Bash | exit 2 | Global | Blocks bare `python`/`python3` without `uv run` |
| `pretool-search-burst.sh` | PreToolUse:search tools | exit 0/2 | Global | Warns at 4, blocks at 8 consecutive searches |
| `pretool-data-guard.sh` | PreToolUse:Write\|Edit | exit 2 | (available) | Blocks writes to protected paths |
| `postwrite-source-check.sh` | PostToolUse:Write\|Edit | exit 2 | Intel | Blocks research writes without source tags |
| `posttool-bash-failure-loop.sh` | PostToolUse:Bash | exit 0 (warns) | Global | Warns after 5 consecutive Bash failures |
| `stop-research-gate.sh` | Stop | exit 2 | Intel | Blocks stop if research files lack source tags |
| `precompact-log.sh` | PreCompact | exit 0 (async) | Global | Logs compaction events |
| `session-init.sh` | SessionStart | exit 0 | Global | Persists session ID to `.claude/current-session-id` |
| `sessionend-log.sh` | SessionEnd | exit 0 (async) | Global | Logs session end + flight receipt + recent commits |
| `stop-notify.sh` | Stop | exit 0 | Global | macOS notification on idle |
| `spinning-detector.sh` | PostToolUse | exit 0 (warns) | Global | Warns at 4/8 consecutive same-tool calls (uses additionalContext) |
| `userprompt-context-warn.sh` | UserPromptSubmit | exit 0 (warns) | Global | Detects continuation boilerplate |
| `pretool-commit-check.sh` | PreToolUse:Bash | exit 0/2 | Global | Checks git commits: [prefix], no Co-Authored-By, governance trailers |

### Skill-Embedded Hooks (new pattern, 2026-03-01)
| Skill | Event | Type | What it does |
|-------|-------|------|-------------|
| `researcher` | PostToolUse:Write\|Edit | prompt | Checks source citations on factual claims |

### Intel-Only Hooks (in .claude/settings.json)
| Hook | Event | What it does |
|------|-------|-------------|
| Large file guard | PreToolUse:Read | Advisory when file >256KB without offset/limit |
| DuckDB dry-run | PostToolUse:Write\|Edit | Advisory when setup_duckdb.py or tools/datasets/ modified |
| Backtest guard | PreToolUse:search tools | Blocks external queries during active backtests |
| Data protection | PreToolUse:Write\|Edit | Blocks writes to datasets/, .parquet, intel.duckdb |
| Secrets guard | PreToolUse:Write\|Edit | Blocks writes to .env, credentials, secrets files |

## Hook Design Principles
- Deterministic > LLM-judged. Guard concrete invariants, not vibes.
- Fail open unless blocking is clearly worth it.
- `trap 'exit 0' ERR` swallows `exit 2` from Python — disable trap before critical Python calls.
- Stop hooks must check `stop_hook_active` to prevent infinite loops.

## Claude Code Hook Events (verified 2026-02-28)

17 events total. Source: https://code.claude.com/docs/en/hooks

| Event | Fires when | Can block? | Hook types |
|-------|-----------|------------|------------|
| SessionStart | Session begins/resumes | No | command |
| UserPromptSubmit | User submits prompt | Yes | command, prompt, agent |
| PreToolUse | Before tool call | Yes (deny/allow/ask) | command, prompt, agent |
| PermissionRequest | Permission dialog | Yes (allow/deny) | command, prompt, agent |
| PostToolUse | After tool succeeds | No | command, prompt, agent |
| PostToolUseFailure | After tool fails | No | command, prompt, agent |
| Notification | Notification sent | No | command |
| SubagentStart | Subagent spawned | No | command |
| SubagentStop | Subagent finishes | Yes (block) | command, prompt, agent |
| Stop | Claude finishes | Yes (block) | command, prompt, agent |
| TeammateIdle | Teammate idle | Yes (exit 2) | command |
| TaskCompleted | Task completed | Yes (exit 2) | command |
| ConfigChange | Config changes | Yes (block) | command |
| WorktreeCreate | Worktree created | Yes (non-zero fails) | command |
| WorktreeRemove | Worktree removed | No | command |
| PreCompact | Before compaction | No | command |
| SessionEnd | Session terminates | No | command |

### Decision control patterns
- PreToolUse: JSON `hookSpecificOutput.permissionDecision` (allow/deny/ask)
- PermissionRequest: JSON `hookSpecificOutput.decision.behavior` (allow/deny)
- Stop, PostToolUse, SubagentStop, ConfigChange, UserPromptSubmit: JSON `decision: "block"`
- TeammateIdle, TaskCompleted: exit code 2 blocks
- PreCompact, SessionEnd, Notification, WorktreeRemove: no decision control
</reference_data>
