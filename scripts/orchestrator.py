#!/usr/bin/env python3
"""Orchestrator: cron-driven task runner for Agent SDK and deterministic scripts.

Dual-engine architecture:
  engine='claude'  -> Agent SDK query() with effort, max_budget_usd, hooks
  engine='script'  -> subprocess.run(command) -- no LLM, no tokens

Usage:
  orchestrator.py init-db                          # create/migrate DB
  orchestrator.py submit <pipeline> [--project P] [--vars k=v ...]
  orchestrator.py run --project P --prompt "..."   # submit one-off task
  orchestrator.py status                           # show task queue
  orchestrator.py approve <task_id|pipeline>       # approve a paused task
  orchestrator.py log [--today]                    # show event log
  orchestrator.py summary                          # generate daily markdown summary
  orchestrator.py tick                             # run one task (called by launchd)
"""

import argparse
import fcntl
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

import anyio

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

DB_PATH = Path("~/.claude/orchestrator.db").expanduser()
LOG_PATH = Path("~/.claude/orchestrator-log.jsonl").expanduser()
LOCK_PATH = Path("/tmp/orchestrator.lock")
OUTPUT_DIR = Path("~/.claude/orchestrator-outputs").expanduser()
PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipelines"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DAILY_COST_CAP = 25.0


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    _migrate_if_needed(db)
    return db


_migrated = False


def _migrate_if_needed(db):
    global _migrated
    if _migrated:
        return
    cols = {row[1] for row in db.execute("PRAGMA table_info(tasks)").fetchall()}
    if "subagents" not in cols:
        db.execute("ALTER TABLE tasks ADD COLUMN subagents TEXT")
        db.commit()
    _migrated = True


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    schema = SCHEMA_PATH.read_text()
    db.executescript(schema)
    db.close()
    print(f"Database initialized at {DB_PATH}")


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------

def acquire_lock():
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        return None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_event(event):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        event["ts"] = datetime.now().isoformat()
        f.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# Core: claim + execute one task
# ---------------------------------------------------------------------------

def claim_task(db):
    db.execute("BEGIN IMMEDIATE")
    task = db.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND (requires_approval = 0 OR approved_at IS NOT NULL)
          AND (depends_on IS NULL
               OR depends_on IN (SELECT id FROM tasks WHERE status IN ('done', 'done_with_denials')))
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """).fetchone()
    if task:
        db.execute(
            "UPDATE tasks SET status='running', started_at=datetime('now','localtime') WHERE id=?",
            (task["id"],),
        )
    db.commit()
    return task


def cascade_failure(db, task_id):
    dependents = db.execute(
        "SELECT id FROM tasks WHERE depends_on = ? AND status = 'pending'",
        (task_id,),
    ).fetchall()
    for row in dependents:
        db.execute(
            "UPDATE tasks SET status='blocked', blocked_reason='dependency_failed' WHERE id=?",
            (row["id"],),
        )
        cascade_failure(db, row["id"])


def check_daily_cost(db):
    row = db.execute("""
        SELECT COALESCE(SUM(cost_usd), 0) as total
        FROM tasks WHERE date(finished_at) = date('now', 'localtime')
    """).fetchone()
    return row["total"]


def resolve_cwd(task):
    cwd = task["cwd"] or f"~/Projects/{task['project']}"
    return os.path.expanduser(cwd)


def run_script_task(task, cwd):
    return subprocess.run(
        task["prompt"], shell=True, capture_output=True, text=True,
        cwd=cwd, timeout=300,
    )


def _build_agents(subagents_json: str | None) -> dict[str, AgentDefinition] | None:
    """Build AgentDefinition dict from JSON-encoded subagent specs.

    Variable substitution is already applied at submit time, so this just
    converts the stored JSON into SDK AgentDefinition objects.
    """
    if not subagents_json:
        return None
    raw = json.loads(subagents_json)
    if not raw:
        return None
    agents = {}
    for name, spec in raw.items():
        agents[name] = AgentDefinition(
            description=spec.get("description", f"{name} subagent"),
            prompt=spec.get("prompt", ""),
            tools=spec.get("tools"),
            model=spec.get("model"),
        )
    return agents


async def _run_claude_task_async(task, cwd):
    """Run a claude task via Agent SDK query(). Returns TaskResult-like dict."""
    effort = task["effort"]
    allowed_tools = (
        task["allowed_tools"].split(",") if task["allowed_tools"] else None
    )

    # Build subagent definitions if present
    agents = _build_agents(task["subagents"])

    # Set subagent model for search-heavy tasks (effort=low implies lightweight)
    # SDK's version check (claude -v) and main subprocess both inherit os.environ.
    # Must unset CLAUDECODE from os.environ itself, not just the env dict overlay.
    saved_claudecode = os.environ.pop("CLAUDECODE", None)
    os.environ["CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"] = "1"  # belt-and-suspenders
    env = dict(os.environ)
    if effort == "low":
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = "haiku"
    if effort:
        env["CLAUDE_CODE_EFFORT_LEVEL"] = effort

    options = ClaudeAgentOptions(
        model=task["model"],
        max_turns=task["max_turns"] or 15,
        max_budget_usd=task["max_budget_usd"] or 5.0,
        permission_mode="acceptEdits",
        cwd=cwd,
        effort=effort,
        allowed_tools=allowed_tools or [],
        setting_sources=["user", "project"],
        fallback_model="haiku" if task["model"] == "sonnet" else "sonnet",
        system_prompt={"type": "preset", "preset": "claude_code"},
        env=env,
        agents=agents,
    )

    text_parts: list[str] = []
    result_msg: ResultMessage | None = None
    last_model: str | None = None

    try:
        async for message in query(prompt=task["prompt"], options=options):
            if isinstance(message, AssistantMessage):
                last_model = message.model
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(message, ResultMessage):
                result_msg = message
    finally:
        # Restore CLAUDECODE so rest of process isn't affected
        if saved_claudecode is not None:
            os.environ["CLAUDECODE"] = saved_claudecode

    return {
        "result_msg": result_msg,
        "text_parts": text_parts,
        "last_model": last_model,
    }


def run_claude_task(task, cwd):
    """Sync wrapper around async SDK query()."""
    return anyio.run(_run_claude_task_async, task, cwd)


def execute_one(db):
    daily_cost = check_daily_cost(db)
    if daily_cost >= DAILY_COST_CAP:
        log_event({"action": "cost_cap", "daily_cost": daily_cost})
        return False

    task = claim_task(db)
    if not task:
        return False

    task_id = task["id"]
    engine = task["engine"] or "claude"
    cwd = resolve_cwd(task)

    log_event({
        "action": "start", "task_id": task_id,
        "pipeline": task["pipeline"], "step": task["step"],
        "project": task["project"], "engine": engine,
    })

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / f"{task_id}.json"

        if engine == "script":
            result = run_script_task(task, cwd)
            if result.returncode != 0:
                error_msg = f"exit_{result.returncode}: {result.stderr[:500]}"
                db.execute("""
                    UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                        error=? WHERE id=?
                """, (error_msg, task_id))
                cascade_failure(db, task_id)
                log_event({"action": "failed", "task_id": task_id,
                           "exit_code": result.returncode, "stderr": result.stderr[:200]})
                db.commit()
                return True

            summary = result.stdout[:2000] if result.stdout else "(empty)"
            output_file.write_text(result.stdout or "")
            db.execute("""
                UPDATE tasks SET status='done', finished_at=datetime('now','localtime'),
                    output_file=?, result_summary=?, cost_usd=0 WHERE id=?
            """, (str(output_file), summary, task_id))
            log_event({"action": "done", "task_id": task_id, "engine": "script", "cost_usd": 0})

        else:
            # Agent SDK path
            sdk_result = run_claude_task(task, cwd)
            result_msg = sdk_result["result_msg"]
            text_parts = sdk_result["text_parts"]

            if result_msg is None:
                db.execute("""
                    UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                        error='no_result_message' WHERE id=?
                """, (task_id,))
                cascade_failure(db, task_id)
                log_event({"action": "failed", "task_id": task_id, "error": "no ResultMessage from SDK"})
                db.commit()
                return True

            usage = result_msg.usage or {}
            tokens_in = sum(
                v.get("inputTokens", 0) + v.get("cacheReadInputTokens", 0)
                for v in usage.values()
                if isinstance(v, dict)
            )
            tokens_out = sum(
                v.get("outputTokens", 0)
                for v in usage.values()
                if isinstance(v, dict)
            )
            cost = result_msg.total_cost_usd or 0
            summary = (result_msg.result or "\n".join(text_parts))[:2000]
            status = "done" if not result_msg.is_error else "failed"

            output_data = {
                "result": result_msg.result,
                "total_cost_usd": cost,
                "session_id": result_msg.session_id,
                "duration_ms": result_msg.duration_ms,
                "duration_api_ms": result_msg.duration_api_ms,
                "num_turns": result_msg.num_turns,
                "is_error": result_msg.is_error,
                "model": sdk_result["last_model"],
                "usage": usage,
            }
            output_file.write_text(json.dumps(output_data, indent=2, default=str))

            if result_msg.is_error:
                db.execute("""
                    UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                        output_file=?, error=?, cost_usd=?,
                        tokens_in=?, tokens_out=? WHERE id=?
                """, (str(output_file), summary[:500], cost, tokens_in, tokens_out, task_id))
                cascade_failure(db, task_id)
                log_event({"action": "failed", "task_id": task_id, "cost_usd": cost,
                           "error": summary[:200]})
            else:
                db.execute("""
                    UPDATE tasks SET status=?, finished_at=datetime('now','localtime'),
                        output_file=?, result_summary=?, cost_usd=?,
                        tokens_in=?, tokens_out=? WHERE id=?
                """, (status, str(output_file), summary, cost, tokens_in, tokens_out, task_id))
                log_event({"action": status, "task_id": task_id, "cost_usd": cost})

    except Exception as e:
        db.execute(
            "UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'), error=? WHERE id=?",
            (str(e)[:500], task_id),
        )
        cascade_failure(db, task_id)
        log_event({"action": "error", "task_id": task_id, "error": str(e)[:200]})

    db.commit()
    return True


# ---------------------------------------------------------------------------
# Pipeline submission
# ---------------------------------------------------------------------------

def load_pipeline_template(name):
    path = PIPELINE_DIR / f"{name}.json"
    if not path.exists():
        print(f"Pipeline template not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def substitute_vars(text, variables):
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", value)
    return text


def cmd_submit(args):
    template = load_pipeline_template(args.pipeline)
    variables = {"pipeline": args.pipeline}
    if args.vars:
        for kv in args.vars:
            if "=" in kv:
                k, v = kv.split("=", 1)
                variables[k] = v

    project = args.project or template.get("project", "meta")
    pause_before = template.get("pause_before", [])
    steps = template.get("steps", [])

    db = get_db()
    prev_task_id = None

    for step_def in steps:
        step_name = step_def["step"]
        prompt = substitute_vars(step_def.get("prompt", ""), variables)
        step_project = step_def.get("project", project)
        needs_approval = 1 if step_name in pause_before else 0

        # Cross-project execute steps always need approval
        if step_project != "meta" and step_name == "execute":
            needs_approval = 1

        # Serialize subagents with variable substitution baked into descriptions/prompts
        subagents_raw = step_def.get("subagents")
        subagents_json = None
        if subagents_raw:
            # Apply variable substitution to subagent prompts and descriptions
            substituted = {}
            for sa_name, sa_spec in subagents_raw.items():
                substituted[sa_name] = {
                    **sa_spec,
                    "description": substitute_vars(sa_spec.get("description", ""), variables),
                    "prompt": substitute_vars(sa_spec.get("prompt", ""), variables),
                }
            subagents_json = json.dumps(substituted)

        db.execute("""
            INSERT INTO tasks (pipeline, step, project, prompt, engine, priority,
                max_turns, max_budget_usd, model, agent, allowed_tools, effort, cwd,
                requires_approval, depends_on, subagents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            args.pipeline,
            step_name,
            step_project,
            prompt,
            step_def.get("engine", "claude"),
            step_def.get("priority", 5),
            step_def.get("max_turns", 15),
            step_def.get("max_budget_usd", 5.0),
            step_def.get("model"),
            step_def.get("agent"),
            step_def.get("allowed_tools"),
            step_def.get("effort"),
            step_def.get("cwd"),
            needs_approval,
            prev_task_id,
            subagents_json,
        ))
        prev_task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Register pipeline if scheduled
    if template.get("schedule"):
        db.execute("""
            INSERT OR REPLACE INTO pipelines (name, template, project, schedule, pause_before, last_run, enabled)
            VALUES (?, ?, ?, ?, ?, datetime('now','localtime'), 1)
        """, (
            args.pipeline,
            json.dumps(template),
            project,
            template.get("schedule"),
            json.dumps(pause_before),
        ))

    db.commit()
    db.close()

    print(f"Submitted pipeline '{args.pipeline}' with {len(steps)} steps (project={project})")
    for i, step_def in enumerate(steps):
        marker = " [APPROVAL]" if step_def["step"] in pause_before else ""
        print(f"  {i+1}. {step_def['step']}{marker}")


def cmd_run(args):
    db = get_db()
    db.execute("""
        INSERT INTO tasks (project, prompt, engine, max_turns, max_budget_usd, model, effort, cwd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        args.project,
        args.prompt,
        args.engine,
        args.max_turns,
        args.max_budget,
        args.model,
        args.effort,
        args.cwd,
    ))
    task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    print(f"Submitted task #{task_id} (project={args.project}, engine={args.engine})")


def cmd_status(args):
    db = get_db()
    tasks = db.execute("""
        SELECT id, pipeline, step, project, engine, status, priority,
               requires_approval, approved_at, cost_usd, error,
               created_at, started_at, finished_at
        FROM tasks
        ORDER BY
            CASE status
                WHEN 'running' THEN 0
                WHEN 'pending' THEN 1
                WHEN 'blocked' THEN 2
                WHEN 'done' THEN 3
                WHEN 'done_with_denials' THEN 4
                WHEN 'failed' THEN 5
            END,
            priority ASC, created_at ASC
    """).fetchall()

    if not tasks:
        print("No tasks in queue.")
        db.close()
        return

    by_status = {}
    total_cost = 0.0
    for t in tasks:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        total_cost += t["cost_usd"] or 0

    status_parts = [f"{v} {k}" for k, v in sorted(by_status.items())]
    print(f"Tasks: {len(tasks)} ({', '.join(status_parts)}) -- ${total_cost:.2f} spent today")
    print()

    fmt = "{:<5} {:<18} {:<22} {:<10} {:<8} {:<4} {:<22} {}"
    print(fmt.format("ID", "STATUS", "PIPELINE/STEP", "PROJECT", "ENGINE", "PRI", "COST/ERR", "APPROVAL"))
    print("-" * 100)

    for t in tasks:
        pipeline_step = f"{t['pipeline'] or '-'}/{t['step'] or '-'}"
        cost_err = ""
        if t["status"] in ("done", "done_with_denials"):
            cost_err = f"${t['cost_usd'] or 0:.2f}"
        elif t["status"] == "failed":
            cost_err = (t["error"] or "")[:22]
        elif t["status"] == "blocked":
            cost_err = "dep failed"

        approval = ""
        if t["requires_approval"]:
            approval = "APPROVED" if t["approved_at"] else "WAITING"

        print(fmt.format(
            t["id"], t["status"], pipeline_step[:22], t["project"],
            t["engine"] or "claude", t["priority"], cost_err, approval,
        ))

    db.close()


def cmd_approve(args):
    db = get_db()
    target = args.target

    if target.isdigit():
        n = db.execute(
            "UPDATE tasks SET approved_at=datetime('now','localtime') WHERE id=? AND requires_approval=1 AND approved_at IS NULL",
            (int(target),),
        ).rowcount
        what = f"task #{target}"
    else:
        n = db.execute(
            "UPDATE tasks SET approved_at=datetime('now','localtime') WHERE pipeline=? AND requires_approval=1 AND approved_at IS NULL",
            (target,),
        ).rowcount
        what = f"pipeline '{target}'"

    db.commit()
    db.close()

    if n > 0:
        print(f"Approved {n} task(s) in {what}")
    else:
        print(f"No pending approval tasks found for {what}")


def cmd_log(args):
    if not LOG_PATH.exists():
        print("No log file yet.")
        return

    lines = LOG_PATH.read_text().strip().split("\n")
    if args.today:
        today = date.today().isoformat()
        lines = [l for l in lines if today in l]

    for line in lines[-50:]:
        try:
            evt = json.loads(line)
            ts = evt.get("ts", "")[:19]
            action = evt.get("action", "?")
            tid = evt.get("task_id", "")
            extra = ""
            if "cost_usd" in evt:
                extra += f" ${evt['cost_usd']:.2f}"
            if "error" in evt:
                extra += f" err={evt['error'][:40]}"
            print(f"[{ts}] {action:<15} task={tid}{extra}")
        except json.JSONDecodeError:
            print(line)


def cmd_summary(args):
    db = get_db()
    today = date.today().isoformat()

    tasks = db.execute("""
        SELECT * FROM tasks
        WHERE date(created_at) = ? OR date(finished_at) = ?
        ORDER BY finished_at
    """, (today, today)).fetchall()

    if not tasks:
        print("No tasks today.")
        db.close()
        return

    done = [t for t in tasks if t["status"] in ("done", "done_with_denials")]
    failed = [t for t in tasks if t["status"] == "failed"]
    pending = [t for t in tasks if t["status"] in ("pending", "running", "blocked")]
    total_cost = sum(t["cost_usd"] or 0 for t in tasks)

    lines = [
        f"# Orchestrator Summary: {today}",
        "",
        f"- **{len(done)}** done, **{len(failed)}** failed, **{len(pending)}** pending/blocked",
        f"- **${total_cost:.2f}** spent",
        "",
    ]

    if done:
        lines.append("## Completed")
        for t in done:
            denials = " [DENIALS]" if t["status"] == "done_with_denials" else ""
            summary = (t["result_summary"] or "")[:100].replace("\n", " ")
            lines.append(f"- #{t['id']} {t['pipeline'] or ''}/{t['step'] or ''} "
                         f"({t['project']}, ${t['cost_usd'] or 0:.2f}){denials}: {summary}")

    if failed:
        lines.append("\n## Failed")
        for t in failed:
            lines.append(f"- #{t['id']} {t['pipeline'] or ''}/{t['step'] or ''}: {t['error'] or '?'}")

    if pending:
        lines.append("\n## Pending")
        for t in pending:
            approval = " [NEEDS APPROVAL]" if t["requires_approval"] and not t["approved_at"] else ""
            lines.append(f"- #{t['id']} {t['pipeline'] or ''}/{t['step'] or ''} "
                         f"({t['status']}){approval}")

    output = "\n".join(lines) + "\n"

    summary_path = Path("~/.claude/orchestrator-summaries").expanduser()
    summary_path.mkdir(parents=True, exist_ok=True)
    out_file = summary_path / f"{today}.md"
    out_file.write_text(output)

    print(output)
    print(f"Written to {out_file}")
    db.close()


def cmd_tick(args):
    lock_fd = acquire_lock()
    if not lock_fd:
        return

    db = get_db()
    execute_one(db)
    db.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Orchestrator: cron-driven task runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init-db", help="Create/migrate the database")

    p_submit = sub.add_parser("submit", help="Submit a pipeline")
    p_submit.add_argument("pipeline", help="Pipeline template name")
    p_submit.add_argument("--project", "-p", help="Override project")
    p_submit.add_argument("--vars", nargs="*", help="Template variables: key=value")

    p_run = sub.add_parser("run", help="Submit a one-off task")
    p_run.add_argument("--project", "-p", required=True)
    p_run.add_argument("--prompt", required=True)
    p_run.add_argument("--engine", default="claude", choices=["claude", "script"])
    p_run.add_argument("--max-turns", type=int, default=15)
    p_run.add_argument("--max-budget", type=float, default=5.0)
    p_run.add_argument("--model", default=None)
    p_run.add_argument("--effort", default=None, choices=["low", "medium", "high", "max"])
    p_run.add_argument("--cwd", default=None)

    sub.add_parser("status", help="Show task queue")

    p_approve = sub.add_parser("approve", help="Approve a pending task/pipeline")
    p_approve.add_argument("target", help="Task ID or pipeline name")

    p_log = sub.add_parser("log", help="Show event log")
    p_log.add_argument("--today", action="store_true")

    sub.add_parser("summary", help="Generate daily summary")

    sub.add_parser("tick", help="Run one task (called by launchd)")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "approve":
        cmd_approve(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "summary":
        cmd_summary(args)
    elif args.command == "tick":
        cmd_tick(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
