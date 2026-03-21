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

import time as _time

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
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
STALL_TIMEOUT_SECONDS = 900  # Kill claude tasks silent for >15 min
MAX_CONCURRENT_PER_PIPELINE = 3  # Max running tasks from same pipeline
MAX_VERIFY_RETRIES = 1  # Max retries per step on verification failure

# Default effort by pipeline when not specified in step definition.
DEFAULT_EFFORT = {
    "entity-refresh": "low",
    "session-retro": "medium",
    "morning-prep": "low",
    "skills-drift": "low",
    "research-sweep": "high",
    "earnings-refresh": "low",
    "vendor-landscape": "medium",
    "deep-dive": "high",
    "trigger-monitor": "low",
    "epistemic-baseline": "medium",
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    from common.db import open_db
    db = open_db(DB_PATH)
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
    if "step_options" not in cols:
        db.execute("ALTER TABLE tasks ADD COLUMN step_options TEXT")
    # Ensure scheduled_runs table exists (Phase 3 scheduler)
    db.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_runs (
            id INTEGER PRIMARY KEY,
            pipeline_name TEXT NOT NULL,
            period_start TEXT NOT NULL,
            submitted_at TEXT DEFAULT (datetime('now','localtime')),
            task_id INTEGER REFERENCES tasks(id),
            UNIQUE(pipeline_name, period_start)
        )
    """)
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
    candidates = db.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND (requires_approval = 0 OR approved_at IS NOT NULL)
          AND (depends_on IS NULL
               OR depends_on IN (SELECT id FROM tasks WHERE status IN ('done', 'done_with_denials')))
        ORDER BY priority ASC, created_at ASC
    """).fetchall()

    task = None
    for candidate in candidates:
        # Per-pipeline concurrency limit
        if candidate["pipeline"]:
            running = db.execute(
                "SELECT COUNT(*) as n FROM tasks WHERE pipeline=? AND status='running'",
                (candidate["pipeline"],),
            ).fetchone()["n"]
            if running >= MAX_CONCURRENT_PER_PIPELINE:
                continue
        task = candidate
        break

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


def _build_telemetry_hooks(metrics_path: Path) -> dict:
    """Build PostToolUse/PostToolUseFailure hooks that write metrics to JSONL."""
    _tool_start_times: dict[str, float] = {}

    async def on_tool_use(input_data, tool_use_id, context):
        ts = _time.time()
        start = _tool_start_times.pop(tool_use_id, ts)
        event = {
            "ts": datetime.now().isoformat(),
            "tool_name": input_data.get("tool_name", "?"),
            "tool_use_id": tool_use_id,
            "duration_ms": int((ts - start) * 1000),
            "success": True,
        }
        # Extract file_path from file tools
        tool_input = input_data.get("tool_input", {})
        if "file_path" in tool_input:
            event["file_path"] = tool_input["file_path"]
        with open(metrics_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        return {}

    async def on_tool_start(input_data, tool_use_id, context):
        """PreToolUse: record start time for duration calculation."""
        _tool_start_times[tool_use_id] = _time.time()
        return {}

    async def on_tool_failure(input_data, tool_use_id, context):
        ts = _time.time()
        start = _tool_start_times.pop(tool_use_id, ts)
        event = {
            "ts": datetime.now().isoformat(),
            "tool_name": input_data.get("tool_name", "?"),
            "tool_use_id": tool_use_id,
            "duration_ms": int((ts - start) * 1000),
            "success": False,
            "error": input_data.get("error", "")[:200],
        }
        with open(metrics_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        return {}

    return {
        "PreToolUse": [HookMatcher(hooks=[on_tool_start])],
        "PostToolUse": [HookMatcher(hooks=[on_tool_use])],
        "PostToolUseFailure": [HookMatcher(hooks=[on_tool_failure])],
    }


async def _run_claude_task_async(task, cwd, progress_file=None):
    """Run a claude task via Agent SDK query(). Returns TaskResult-like dict."""
    effort = task["effort"] or DEFAULT_EFFORT.get(task["pipeline"] or "", "medium")
    allowed_tools = (
        task["allowed_tools"].split(",") if task["allowed_tools"] else None
    )

    # Parse step_options
    raw_opts = task["step_options"]
    step_options = json.loads(raw_opts) if raw_opts else {}

    # Build subagent definitions if present
    agents = _build_agents(task["subagents"])

    # Set subagent model for search-heavy tasks (effort=low implies lightweight)
    # SDK's version check (claude -v) and main subprocess both inherit os.environ.
    # Must unset CLAUDECODE from os.environ itself, not just the env dict overlay.
    saved_claudecode = os.environ.pop("CLAUDECODE", None)
    os.environ["CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"] = "1"  # belt-and-suspenders
    # Filter out vars that trigger nested-session detection in the bundled claude binary
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    if effort == "low":
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = "haiku"
    if effort:
        env["CLAUDE_CODE_EFFORT_LEVEL"] = effort

    # Build optional SDK kwargs from step_options
    sdk_kwargs: dict[str, Any] = {}
    if step_options.get("output_format"):
        sdk_kwargs["output_format"] = step_options["output_format"]
    if step_options.get("disallowed_tools"):
        sdk_kwargs["disallowed_tools"] = step_options["disallowed_tools"]

    # Telemetry hooks — always inject for tool usage metrics
    metrics_path = OUTPUT_DIR / f"{task['id']}.metrics.jsonl"
    sdk_kwargs["hooks"] = _build_telemetry_hooks(metrics_path)

    # Meta-infra MCP — inject for meta-project tasks by default, override via step_options
    inject_meta = step_options.get("inject_meta_infra")
    if inject_meta is None:
        inject_meta = (task["project"] == "meta")
    if inject_meta:
        from scripts.meta_infra_mcp import meta_infra_server
        sdk_kwargs["mcp_servers"] = {"meta-infra": meta_infra_server}

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
        stderr=lambda line: print(f"[sdk-stderr] {line}", flush=True),
        **sdk_kwargs,
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
                        if progress_file:
                            with open(progress_file, "a") as pf:
                                pf.write(block.text + "\n")
            elif isinstance(message, ResultMessage):
                result_msg = message
    except (RuntimeError, Exception) as e:
        # Agent SDK has a known cleanup bug: the async generator's TaskGroup
        # cancel scope exits in a different task during shutdown. If we already
        # have a ResultMessage, the task actually completed — swallow the
        # cleanup error. If we don't have a result, re-raise.
        err = str(e)
        is_cleanup = (
            "cancel scope" in err
            or "ProcessTransport" in err
            or "message reader" in err.lower()
        )
        if is_cleanup and result_msg is not None:
            log_event({
                "action": "sdk_cleanup_error_swallowed",
                "task_id": task["id"],
                "error": err[:200],
            })
        else:
            raise
    finally:
        # Restore CLAUDECODE so rest of process isn't affected
        if saved_claudecode is not None:
            os.environ["CLAUDECODE"] = saved_claudecode

    return {
        "result_msg": result_msg,
        "text_parts": text_parts,
        "last_model": last_model,
    }


def _run_claude_subprocess(task, cwd, progress_file=None):
    """Fallback: run via `claude -p` subprocess when Agent SDK fails.

    Trades structured output for reliability. Returns same dict shape as SDK path.
    """
    prompt = task["prompt"] or ""
    effort = task["effort"] or "medium"
    model = task["model"] or "sonnet"
    max_turns = task["max_turns"] or 15

    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--output-format", "json",
        "--verbose",
    ]

    allowed = task["allowed_tools"]
    if allowed:
        for tool in allowed.split(","):
            cmd.extend(["--allowedTools", tool.strip()])

    env = {**os.environ}
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    if effort:
        env["CLAUDE_CODE_EFFORT_LEVEL"] = effort

    log_event({
        "action": "subprocess_fallback",
        "task_id": task["id"],
        "reason": "Agent SDK CLIConnectionError",
    })

    # Per-step timeout override via step_options, else global default
    raw_opts = task["step_options"] or ""
    opts = json.loads(raw_opts) if raw_opts else {}
    timeout = opts.get("timeout_s", STALL_TIMEOUT_SECONDS)

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd,
        timeout=timeout, env=env,
    )

    # Write progress
    if progress_file and result.stdout:
        with open(progress_file, "w") as f:
            f.write(result.stdout[:5000])

    # Parse JSON output — claude -p --output-format json returns a JSON array
    result_text = result.stdout or ""
    cost = 0.0
    session_id = None
    try:
        parsed = json.loads(result_text)
        # Handle array format: [{type: "result", result: "...", ...}]
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    if item.get("type") == "result":
                        result_text = item.get("result", result_text)
                        cost = item.get("cost_usd", item.get("total_cost_usd", 0.0))
                        session_id = item.get("session_id")
                        break
        elif isinstance(parsed, dict):
            result_text = parsed.get("result", result_text)
            cost = parsed.get("cost_usd", 0.0)
            session_id = parsed.get("session_id")
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        pass

    if result.returncode != 0 and not result_text:
        raise RuntimeError(f"claude -p failed (exit {result.returncode}): {result.stderr[:300]}")

    # Build a minimal ResultMessage-like object
    class _FakeResult:
        def __init__(self):
            self.result = result_text[:2000]
            self.total_cost_usd = cost
            self.session_id = session_id
            self.duration_ms = None
            self.duration_api_ms = None
            self.is_error = result.returncode != 0
            self.usage = {}
            self.model = model
            self.num_turns = 0
            self.structured_output = None

    return {
        "result_msg": _FakeResult(),
        "text_parts": [result_text[:2000]] if result_text else [],
        "last_model": model,
    }


def run_claude_task(task, cwd, progress_file=None):
    """Sync wrapper: try Agent SDK, fall back to subprocess on connection errors.

    Agent SDK has known anyio cancel scope bugs that cause CLIConnectionError
    on startup. When this happens, fall back to `claude -p` subprocess which
    is slower but reliable.
    """
    try:
        return anyio.run(
            lambda: _run_claude_task_async(task, cwd, progress_file)
        )
    except BaseException as e:
        err = str(e)
        is_sdk_bug = (
            "ProcessTransport" in err
            or "cancel scope" in err
            or "CLIConnectionError" in err
            or "TaskGroup" in err
        )
        if is_sdk_bug:
            log_event({
                "action": "sdk_fallback",
                "task_id": task["id"],
                "error": err[:200],
            })
            return _run_claude_subprocess(task, cwd, progress_file)
        raise


def verify_step_output(task, output_summary: str) -> dict:
    """VMAO-derived: verify step output with Haiku before marking done.

    Returns {"pass": True/False, "reasoning": str, "retry": bool}
    Uses the Anthropic API directly (not Agent SDK) for cheap verification.
    """
    try:
        import anthropic
    except ImportError:
        # Can't verify without SDK — pass by default (fail open)
        return {"pass": True, "reasoning": "anthropic SDK not available", "retry": False}

    prompt_text = task["prompt"] or ""
    step_name = task["step"] or "unknown"

    verify_prompt = f"""You are verifying the output of a pipeline step. Be concise.

STEP: {step_name}
TASK PROMPT (what was asked):
{prompt_text[:2000]}

STEP OUTPUT (what was produced):
{output_summary[:3000]}

Answer these 3 questions:
1. Did the output address the task prompt? (yes/partially/no)
2. Are there obvious gaps or contradictions? (list them or "none")
3. Should this step be retried? (yes/no — only yes if output is clearly wrong or empty)

Respond as JSON: {{"addressed": "yes|partially|no", "gaps": "...", "retry": true|false, "reasoning": "one sentence"}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": verify_prompt}],
        )
        text = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        )

        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "pass": not result.get("retry", False),
                "reasoning": result.get("reasoning", ""),
                "retry": result.get("retry", False),
                "addressed": result.get("addressed", "unknown"),
                "gaps": result.get("gaps", ""),
            }
    except Exception as e:
        log_event({"action": "verify_error", "task_id": task["id"], "error": str(e)[:200]})

    # Fail open — if verification itself fails, don't block the pipeline
    return {"pass": True, "reasoning": "verification error — passing by default", "retry": False}


def check_pipeline_stop_conditions(db, task) -> str | None:
    """Check pipeline-level stop conditions before executing a step.

    Returns None if OK to proceed, or a reason string if should stop.
    Stop conditions are defined in pipeline JSON templates.
    """
    pipeline = task["pipeline"]
    if not pipeline:
        return None

    # Load template to get stop_conditions
    template_path = PIPELINE_DIR / f"{pipeline}.json"
    if not template_path.exists():
        return None

    try:
        template = json.loads(template_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    stop = template.get("stop_conditions", {})
    if not stop:
        return None

    # max_pipeline_cost: total cost across all tasks in this pipeline submission
    max_cost = stop.get("max_pipeline_cost")
    if max_cost:
        row = db.execute("""
            SELECT COALESCE(SUM(cost_usd), 0) as total
            FROM tasks WHERE pipeline = ? AND status IN ('done', 'done_with_denials', 'failed')
        """, (pipeline,)).fetchone()
        if row["total"] >= max_cost:
            return f"pipeline_cost_cap: ${row['total']:.2f} >= ${max_cost:.2f}"

    # max_iterations: max completed tasks for this pipeline today
    max_iter = stop.get("max_iterations")
    if max_iter:
        row = db.execute("""
            SELECT COUNT(*) as n FROM tasks
            WHERE pipeline = ? AND status IN ('done', 'done_with_denials')
              AND date(finished_at) = date('now', 'localtime')
        """, (pipeline,)).fetchone()
        if row["n"] >= max_iter:
            return f"max_iterations: {row['n']} >= {max_iter}"

    return None


def execute_one(db):
    daily_cost = check_daily_cost(db)
    if daily_cost >= DAILY_COST_CAP:
        log_event({"action": "cost_cap", "daily_cost": daily_cost})
        return False

    task = claim_task(db)
    if not task:
        return False

    # Check pipeline-level stop conditions before executing
    stop_reason = check_pipeline_stop_conditions(db, task)
    if stop_reason:
        db.execute("""
            UPDATE tasks SET status='skipped', finished_at=datetime('now','localtime'),
                error=? WHERE id=?
        """, (f"stop_condition: {stop_reason}", task["id"]))
        log_event({"action": "stop_condition", "task_id": task["id"], "reason": stop_reason})
        db.commit()
        return True

    # Budget-aware degradation: downgrade effort or skip non-critical tasks
    remaining = DAILY_COST_CAP - daily_cost
    max_budget = task["max_budget_usd"] or 5.0
    task_effort = task["effort"] or DEFAULT_EFFORT.get(task["pipeline"] or "", "medium")
    pipeline = task["pipeline"] or ""
    if max_budget > remaining:
        if task_effort in ("high", "max"):
            log_event({"action": "budget_degrade", "task_id": task["id"],
                        "from": task_effort, "to": "medium", "remaining": remaining})
            # effort is applied in _run_claude_task_async via DEFAULT_EFFORT fallback;
            # override the task's effort column directly
            db.execute("UPDATE tasks SET effort='medium' WHERE id=?", (task["id"],))
            db.commit()
        elif remaining < 2.0 and not pipeline.startswith("trigger-"):
            db.execute("""
                UPDATE tasks SET status='skipped', finished_at=datetime('now','localtime'),
                    error='budget_exhausted' WHERE id=?
            """, (task["id"],))
            log_event({"action": "budget_skip", "task_id": task["id"], "remaining": remaining})
            db.commit()
            return True

    task_id = task["id"]
    engine = task["engine"] or "claude"
    cwd = resolve_cwd(task)

    log_event({
        "action": "start", "task_id": task_id,
        "pipeline": task["pipeline"], "step": task["step"],
        "project": task["project"], "engine": engine,
    })

    if engine != "script":
        live_path = OUTPUT_DIR / f"{task_id}.live"
        print(f"Task #{task_id} running — tail -f {live_path}")

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
            progress_file = OUTPUT_DIR / f"{task_id}.live"
            metrics_path = OUTPUT_DIR / f"{task_id}.metrics.jsonl"
            raw_opts = task["step_options"]
            step_options = json.loads(raw_opts) if raw_opts else {}
            sdk_result = run_claude_task(task, cwd, progress_file=progress_file)
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
            tokens_in = (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
            )
            tokens_out = usage.get("output_tokens", 0)
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
            # Include metrics file path if it has data
            if metrics_path.exists():
                output_data["metrics_file"] = str(metrics_path)

            # Capture structured output if output_format was requested
            if result_msg.structured_output is not None:
                output_data["structured_output"] = result_msg.structured_output
            elif step_options.get("output_format") and not result_msg.is_error:
                # Model returned text instead of structured — log warning, don't fail
                log_event({"action": "warning", "task_id": task_id,
                           "warning": "output_format requested but structured_output is None"})
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
                # VMAO-derived: optional verification step before marking done
                verify_result = None
                if step_options.get("verify") and status == "done":
                    verify_result = verify_step_output(task, summary)
                    log_event({
                        "action": "verify", "task_id": task_id,
                        "pass": verify_result["pass"],
                        "reasoning": verify_result.get("reasoning", ""),
                    })
                    output_data["verification"] = verify_result

                    if not verify_result["pass"] and verify_result.get("retry"):
                        # Check retry budget
                        retry_count = db.execute(
                            "SELECT COUNT(*) FROM tasks WHERE pipeline=? AND step=? AND status='failed'",
                            (task["pipeline"], task["step"]),
                        ).fetchone()[0]

                        if retry_count < MAX_VERIFY_RETRIES:
                            # Reset to pending for retry
                            db.execute("""
                                UPDATE tasks SET status='pending', started_at=NULL,
                                    error=? WHERE id=?
                            """, (f"verify_retry: {verify_result.get('reasoning', '')[:200]}", task_id))
                            log_event({"action": "verify_retry", "task_id": task_id,
                                       "reasoning": verify_result.get("reasoning", "")[:200]})
                            db.commit()
                            return True
                        else:
                            # Exhausted retries — mark done with warning
                            log_event({"action": "verify_exhausted", "task_id": task_id})

                    # Re-write output with verification data
                    output_file.write_text(json.dumps(output_data, indent=2, default=str))

                db.execute("""
                    UPDATE tasks SET status=?, finished_at=datetime('now','localtime'),
                        output_file=?, result_summary=?, cost_usd=?,
                        tokens_in=?, tokens_out=? WHERE id=?
                """, (status, str(output_file), summary, cost, tokens_in, tokens_out, task_id))
                log_event({"action": status, "task_id": task_id, "cost_usd": cost})

    except BaseException as e:
        # Extract nested exceptions from ExceptionGroup/TaskGroup
        error_msg = str(e)
        if hasattr(e, 'exceptions'):
            nested = "; ".join(f"{type(sub).__name__}: {sub}" for sub in e.exceptions)
            error_msg = f"{error_msg} [{nested}]"
        db.execute(
            "UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'), error=? WHERE id=?",
            (error_msg[:500], task_id),
        )
        cascade_failure(db, task_id)
        log_event({"action": "error", "task_id": task_id, "error": error_msg[:500]})

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
        # Support "type" as alias for "engine" (pipeline templates use "type": "script")
        if "type" in step_def and "engine" not in step_def:
            step_def["engine"] = step_def["type"]
        # For script steps, use "command" as the prompt (stored in prompt column)
        if step_def.get("engine") == "script" and "command" in step_def:
            step_def.setdefault("prompt", step_def["command"])
        prompt = substitute_vars(step_def.get("prompt", ""), variables)
        step_project = step_def.get("project", project)
        needs_approval = 1 if step_name in pause_before else 0

        # Cross-project execute steps always need approval
        if step_project != "meta" and step_name == "execute":
            needs_approval = 1

        # Build step_options from step-level config keys
        step_options_keys = ("output_format", "inject_meta_infra", "verify", "disallowed_tools", "timeout_s")
        step_options = {k: step_def[k] for k in step_options_keys if k in step_def}
        step_options_json = json.dumps(step_options) if step_options else None

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
                requires_approval, depends_on, subagents, step_options)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            step_options_json,
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


def cmd_show(args):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (args.task_id,)).fetchone()
    if not task:
        print(f"Task #{args.task_id} not found.")
        db.close()
        return

    # Header
    print(f"{'=' * 60}")
    print(f"  Task #{task['id']}  {task['status'].upper()}")
    print(f"{'=' * 60}")
    print()

    # Metadata
    print(f"  Pipeline:    {task['pipeline'] or '-'}/{task['step'] or '-'}")
    print(f"  Project:     {task['project']}")
    print(f"  Engine:      {task['engine'] or 'claude'}")
    print(f"  Model:       {task['model'] or 'default'}")
    print(f"  Effort:      {task['effort'] or 'default'}")
    print(f"  Max turns:   {task['max_turns']}")
    print(f"  Max budget:  ${task['max_budget_usd'] or 0:.2f}")
    print()

    # Timing
    print(f"  Created:     {task['created_at'] or '-'}")
    print(f"  Started:     {task['started_at'] or '-'}")
    print(f"  Finished:    {task['finished_at'] or '-'}")
    if task["started_at"] and task["finished_at"]:
        try:
            start = datetime.strptime(task["started_at"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(task["finished_at"], "%Y-%m-%d %H:%M:%S")
            dur = end - start
            print(f"  Duration:    {dur}")
        except ValueError:
            pass
    print()

    # Cost & tokens
    if task["cost_usd"] is not None:
        print(f"  Cost:        ${task['cost_usd']:.2f}")
    if task["tokens_in"] or task["tokens_out"]:
        print(f"  Tokens:      {task['tokens_in'] or 0:,} in / {task['tokens_out'] or 0:,} out")
    print()

    # Approval
    if task["requires_approval"]:
        print(f"  Approval:    {'APPROVED at ' + task['approved_at'] if task['approved_at'] else 'WAITING'}")
        print()

    # Error
    if task["error"]:
        print(f"  Error:       {task['error']}")
        print()

    # Prompt (truncated)
    prompt = task["prompt"] or ""
    if args.full:
        print("  Prompt:")
        for line in prompt.split("\n"):
            print(f"    {line}")
    else:
        preview = prompt[:300].replace("\n", " ")
        if len(prompt) > 300:
            preview += "..."
        print(f"  Prompt:      {preview}")
    print()

    # Output
    output_file = task["output_file"]
    if output_file and Path(output_file).exists():
        output_data = json.loads(Path(output_file).read_text())
        session_id = output_data.get("session_id")
        num_turns = output_data.get("num_turns")
        duration_ms = output_data.get("duration_ms")

        if session_id:
            print(f"  Session ID:  {session_id}")
            # Find transcript
            project_slug = f"-Users-alien-Projects-{task['project']}"
            from common.paths import PROJECTS_DIR
            transcript = PROJECTS_DIR / project_slug / f"{session_id}.jsonl"
            if transcript.exists():
                print(f"  Transcript:  {transcript}")
            else:
                print(f"  Transcript:  (not found at {transcript})")
        if num_turns:
            print(f"  Turns:       {num_turns}")
        if duration_ms:
            print(f"  SDK time:    {duration_ms / 1000:.1f}s")
        print()

        result = output_data.get("result", "")
        if result:
            if args.full:
                print("  Result:")
                for line in result.split("\n"):
                    print(f"    {line}")
            else:
                preview = result[:500].replace("\n", " ")
                if len(result) > 500:
                    preview += "..."
                print(f"  Result:      {preview}")
    elif task["result_summary"]:
        print(f"  Summary:     {task['result_summary'][:500]}")

    print()
    print(f"  Output file: {output_file or '-'}")
    db.close()


def cmd_log(args):
    if not LOG_PATH.exists():
        print("No log file yet.")
        return

    lines = LOG_PATH.read_text().strip().split("\n")
    if args.today:
        today = date.today().isoformat()
        lines = [l for l in lines if today in l]

    # Filter by pipeline or project
    if args.pipeline or args.project:
        filtered = []
        for line in lines:
            try:
                evt = json.loads(line)
                if args.pipeline and evt.get("pipeline") != args.pipeline:
                    continue
                if args.project and evt.get("project") != args.project:
                    continue
                filtered.append(line)
            except json.JSONDecodeError:
                pass
        lines = filtered

    limit = args.last or 50
    for line in lines[-limit:]:
        try:
            evt = json.loads(line)
            ts = evt.get("ts", "")[:19]
            action = evt.get("action", "?")
            tid = evt.get("task_id", "")
            extra = ""
            if "pipeline" in evt:
                extra += f" {evt['pipeline']}/{evt.get('step', '?')}"
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


def notify(title, message):
    """Send macOS notification. Fails silently."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            timeout=5, capture_output=True,
        )
    except Exception:
        pass


def cmd_pipelines(args):
    db = get_db()
    rows = db.execute("""
        SELECT pipeline,
               COUNT(*) as total,
               SUM(CASE WHEN status IN ('done','done_with_denials') THEN 1 ELSE 0 END) as done,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN status IN ('pending','running','blocked') THEN 1 ELSE 0 END) as active,
               COALESCE(SUM(cost_usd), 0) as cost,
               COALESCE(SUM(tokens_in), 0) as tokens_in,
               COALESCE(SUM(tokens_out), 0) as tokens_out,
               MIN(created_at) as first_created,
               MAX(finished_at) as last_finished
        FROM tasks
        WHERE pipeline IS NOT NULL
        GROUP BY pipeline
        ORDER BY first_created DESC
    """).fetchall()

    if not rows:
        print("No pipelines.")
        db.close()
        return

    print(f"{'PIPELINE':<30} {'DONE':>5} {'FAIL':>5} {'PEND':>5} {'COST':>8} {'TOKENS':>12} {'LAST ACTIVITY'}")
    print("-" * 95)
    for r in rows:
        tokens = f"{(r['tokens_in'] + r['tokens_out']):,}"
        last = (r["last_finished"] or r["first_created"] or "")[:16]
        print(f"{r['pipeline']:<30} {r['done']:>5} {r['failed']:>5} {r['active']:>5} "
              f"${r['cost']:>7.2f} {tokens:>12} {last}")

    # Total
    total_cost = sum(r["cost"] for r in rows)
    total_tokens = sum(r["tokens_in"] + r["tokens_out"] for r in rows)
    print("-" * 95)
    print(f"{'TOTAL':<30} {'':>5} {'':>5} {'':>5} ${total_cost:>7.2f} {total_tokens:>12,}")

    db.close()


def cmd_efficiency(args):
    """Token efficiency breakdown by pipeline — avg tokens, cost, duration per completed task."""
    db = get_db()
    rows = db.execute("""
        SELECT pipeline,
               COUNT(*) as completed,
               COALESCE(AVG(tokens_in), 0) as avg_in,
               COALESCE(AVG(tokens_out), 0) as avg_out,
               COALESCE(AVG(tokens_in + tokens_out), 0) as avg_total,
               COALESCE(AVG(cost_usd), 0) as avg_cost,
               COALESCE(AVG(
                   CAST((julianday(finished_at) - julianday(started_at)) * 86400 AS INTEGER)
               ), 0) as avg_secs,
               COALESCE(SUM(cost_usd), 0) as total_cost,
               COALESCE(SUM(tokens_in + tokens_out), 0) as total_tokens
        FROM tasks
        WHERE status IN ('done', 'done_with_denials')
          AND tokens_in IS NOT NULL
          AND pipeline IS NOT NULL
        GROUP BY pipeline
        ORDER BY avg_total DESC
    """).fetchall()

    if not rows:
        print("No completed tasks with token data.")
        db.close()
        return

    # Also get one-off tasks (no pipeline)
    adhoc = db.execute("""
        SELECT COUNT(*) as completed,
               COALESCE(AVG(tokens_in), 0) as avg_in,
               COALESCE(AVG(tokens_out), 0) as avg_out,
               COALESCE(AVG(tokens_in + tokens_out), 0) as avg_total,
               COALESCE(AVG(cost_usd), 0) as avg_cost,
               COALESCE(AVG(
                   CAST((julianday(finished_at) - julianday(started_at)) * 86400 AS INTEGER)
               ), 0) as avg_secs,
               COALESCE(SUM(cost_usd), 0) as total_cost,
               COALESCE(SUM(tokens_in + tokens_out), 0) as total_tokens
        FROM tasks
        WHERE status IN ('done', 'done_with_denials')
          AND tokens_in IS NOT NULL
          AND pipeline IS NULL
    """).fetchone()

    fmt = "{:<30} {:>5} {:>10} {:>10} {:>10} {:>8} {:>6}"
    print(fmt.format("PIPELINE", "TASKS", "AVG_IN", "AVG_OUT", "AVG_TOT", "AVG_$", "AVG_s"))
    print("-" * 85)

    for r in rows:
        print(fmt.format(
            r["pipeline"][:30],
            r["completed"],
            f"{int(r['avg_in']):,}",
            f"{int(r['avg_out']):,}",
            f"{int(r['avg_total']):,}",
            f"${r['avg_cost']:.2f}",
            int(r["avg_secs"]),
        ))

    if adhoc and adhoc["completed"] > 0:
        print(fmt.format(
            "(ad-hoc)",
            adhoc["completed"],
            f"{int(adhoc['avg_in']):,}",
            f"{int(adhoc['avg_out']):,}",
            f"{int(adhoc['avg_total']):,}",
            f"${adhoc['avg_cost']:.2f}",
            int(adhoc["avg_secs"]),
        ))

    total_cost = sum(r["total_cost"] for r in rows) + (adhoc["total_cost"] if adhoc else 0)
    total_tokens = sum(r["total_tokens"] for r in rows) + (adhoc["total_tokens"] if adhoc else 0)
    print("-" * 85)
    print(f"Total: ${total_cost:.2f} / {total_tokens:,} tokens across all completed tasks")

    db.close()


def _check_scheduled_pipelines(db):
    """Auto-submit scheduled pipelines if their period has elapsed.

    Uses the scheduled_runs table with a unique (pipeline_name, period_start)
    constraint to prevent duplicate submissions. Cron-style schedules parsed
    as daily-only (hour check against current time).
    """
    pipelines = db.execute(
        "SELECT name, schedule, project FROM pipelines WHERE enabled = 1 AND schedule IS NOT NULL"
    ).fetchall()

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    for pipeline in pipelines:
        name = pipeline["name"]
        schedule = pipeline["schedule"]

        # Parse simple cron: "0 22 * * *" -> hour=22
        parts = schedule.split()
        if len(parts) < 5:
            continue
        try:
            sched_hour = int(parts[1])
        except ValueError:
            continue

        # Only submit if current hour >= scheduled hour (run once per day)
        if now.hour < sched_hour:
            continue

        # Check if already submitted for today
        existing = db.execute(
            "SELECT id FROM scheduled_runs WHERE pipeline_name = ? AND period_start = ?",
            (name, today),
        ).fetchone()

        if existing:
            continue

        # Submit the pipeline
        template_path = PIPELINE_DIR / f"{name}.json"
        if not template_path.exists():
            log_event({"action": "schedule_skip", "pipeline": name, "reason": "template_not_found"})
            continue

        template = json.loads(template_path.read_text())
        project = pipeline["project"]
        pause_before = template.get("pause_before", [])
        steps = template.get("steps", [])

        prev_task_id = None
        for step_def in steps:
            step_name = step_def["step"]
            # Support "type" as alias for "engine" (pipeline templates use "type": "script")
            if "type" in step_def and "engine" not in step_def:
                step_def["engine"] = step_def["type"]
            # For script steps, use "command" as the prompt (stored in prompt column)
            if step_def.get("engine") == "script" and "command" in step_def:
                step_def.setdefault("prompt", step_def["command"])
            prompt = step_def.get("prompt", "")
            step_project = step_def.get("project", project)
            needs_approval = 1 if step_name in pause_before else 0
            if step_project != "meta" and step_name == "execute":
                needs_approval = 1

            step_options_keys = ("output_format", "inject_meta_infra", "disallowed_tools", "timeout_s")
            step_options = {k: step_def[k] for k in step_options_keys if k in step_def}
            step_options_json = json.dumps(step_options) if step_options else None

            subagents_raw = step_def.get("subagents")
            subagents_json = json.dumps(subagents_raw) if subagents_raw else None

            db.execute("""
                INSERT INTO tasks (pipeline, step, project, prompt, engine, priority,
                    max_turns, max_budget_usd, model, agent, allowed_tools, effort, cwd,
                    requires_approval, depends_on, subagents, step_options)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, step_name, step_project, prompt,
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
                step_options_json,
            ))
            prev_task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Record in scheduled_runs ledger
        db.execute(
            "INSERT INTO scheduled_runs (pipeline_name, period_start, task_id) VALUES (?, ?, ?)",
            (name, today, prev_task_id),
        )
        db.commit()
        log_event({"action": "scheduled_submit", "pipeline": name, "period": today,
                   "task_id": prev_task_id})


def cmd_retry(args):
    db = get_db()
    task = db.execute("SELECT id, status, pipeline, step FROM tasks WHERE id=?",
                      (args.task_id,)).fetchone()
    if not task:
        print(f"Task #{args.task_id} not found", file=sys.stderr)
        return
    if task["status"] not in ("failed", "blocked", "skipped"):
        print(f"Task #{args.task_id} is {task['status']}, not retryable", file=sys.stderr)
        return

    db.execute("""
        UPDATE tasks SET status='pending', started_at=NULL, finished_at=NULL,
            error=NULL, blocked_reason=NULL, cost_usd=NULL,
            tokens_in=NULL, tokens_out=NULL
        WHERE id=?
    """, (args.task_id,))

    # Also unblock any downstream tasks that were blocked by this failure
    db.execute("""
        UPDATE tasks SET status='pending', blocked_reason=NULL
        WHERE depends_on=? AND status='blocked' AND blocked_reason='dependency_failed'
    """, (args.task_id,))
    unblocked = db.execute("SELECT changes()").fetchone()[0]

    db.commit()
    log_event({"action": "retry", "task_id": args.task_id})
    print(f"Task #{args.task_id} ({task['pipeline']}/{task['step']}) reset to pending")
    if unblocked:
        print(f"  Unblocked {unblocked} downstream task(s)")
    db.close()


def cmd_tick(args):
    lock_fd = acquire_lock()
    if not lock_fd:
        return

    db = get_db()

    # Check if any scheduled pipelines need submission
    _check_scheduled_pipelines(db)

    ran = execute_one(db)

    # Send macOS notification for completed/failed tasks
    if ran:
        last = db.execute("""
            SELECT id, pipeline, step, status, cost_usd, error
            FROM tasks WHERE status IN ('done', 'done_with_denials', 'failed')
            ORDER BY finished_at DESC LIMIT 1
        """).fetchone()
        if last:
            if last["status"] == "failed":
                notify("Orchestrator FAILED",
                       f"#{last['id']} {last['pipeline']}/{last['step']}: {(last['error'] or '?')[:60]}")
            else:
                notify("Orchestrator Done",
                       f"#{last['id']} {last['pipeline']}/{last['step']} (${last['cost_usd'] or 0:.2f})")

    db.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def cmd_run_pipeline(args):
    """Submit pipeline and execute steps synchronously (interactive mode).

    Unlike submit+tick (async/cron), this runs each step immediately in the
    calling process, streaming live output. Designed for use from within
    Claude Code sessions — the agent calls this instead of manually typing
    each phase transition.
    """
    # First submit the pipeline to create tasks in DB
    cmd_submit(args)

    db = get_db()
    pipeline = args.pipeline

    # Get all tasks from this pipeline submission (most recent batch)
    tasks = db.execute("""
        SELECT id, step, status, requires_approval, depends_on
        FROM tasks WHERE pipeline = ?
        ORDER BY id DESC LIMIT 20
    """, (pipeline,)).fetchall()
    tasks = list(reversed(tasks))  # oldest first

    if not tasks:
        print("No tasks found after submission.")
        return

    print(f"\n{'='*60}")
    print(f"  Running pipeline: {pipeline} ({len(tasks)} steps)")
    print(f"{'='*60}\n")

    for i, task_row in enumerate(tasks):
        task_id = task_row["id"]
        step = task_row["step"]

        # Check approval gate
        if task_row["requires_approval"] and not task_row["approved_at"]:
            print(f"\n  Step {i+1}/{len(tasks)}: {step} — REQUIRES APPROVAL")
            print(f"  Run: orchestrator.py approve {task_id}")
            print(f"  Remaining steps paused.")
            break

        # Skip if dependency failed
        if task_row["depends_on"]:
            dep = db.execute(
                "SELECT status FROM tasks WHERE id=?",
                (task_row["depends_on"],),
            ).fetchone()
            if dep and dep["status"] not in ("done", "done_with_denials"):
                print(f"\n  Step {i+1}/{len(tasks)}: {step} — SKIPPED (dependency failed)")
                continue

        print(f"\n  Step {i+1}/{len(tasks)}: {step}")
        print(f"  {'─'*50}")

        # Execute this task directly (bypass queue, no lock needed)
        task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not task:
            continue

        # Mark running
        db.execute(
            "UPDATE tasks SET status='running', started_at=datetime('now','localtime') WHERE id=?",
            (task_id,),
        )
        db.commit()

        cwd = resolve_cwd(task)
        engine = task["engine"] or "claude"

        try:
            if engine == "script":
                result = run_script_task(task, cwd)
                if result.returncode != 0:
                    print(f"  FAILED (exit {result.returncode}): {result.stderr[:200]}")
                    db.execute("""
                        UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                            error=? WHERE id=?
                    """, (f"exit_{result.returncode}: {result.stderr[:500]}", task_id))
                    cascade_failure(db, task_id)
                else:
                    summary = result.stdout[:2000] if result.stdout else "(empty)"
                    output_file = OUTPUT_DIR / f"{task_id}.json"
                    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                    output_file.write_text(result.stdout or "")
                    db.execute("""
                        UPDATE tasks SET status='done', finished_at=datetime('now','localtime'),
                            output_file=?, result_summary=?, cost_usd=0 WHERE id=?
                    """, (str(output_file), summary, task_id))
                    print(f"  Done (script)")
            else:
                # Agent SDK path
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                progress_file = OUTPUT_DIR / f"{task_id}.live"
                sdk_result = run_claude_task(task, cwd, progress_file=progress_file)
                result_msg = sdk_result["result_msg"]
                text_parts = sdk_result["text_parts"]

                if result_msg is None:
                    db.execute("""
                        UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                            error='no_result_message' WHERE id=?
                    """, (task_id,))
                    cascade_failure(db, task_id)
                    print(f"  FAILED: no result from SDK")
                else:
                    cost = result_msg.total_cost_usd or 0
                    summary = (result_msg.result or "\n".join(text_parts))[:2000]
                    status = "done" if not result_msg.is_error else "failed"
                    output_file = OUTPUT_DIR / f"{task_id}.json"
                    output_file.write_text(json.dumps({
                        "result": result_msg.result,
                        "total_cost_usd": cost,
                        "session_id": result_msg.session_id,
                    }, indent=2))
                    db.execute("""
                        UPDATE tasks SET status=?, finished_at=datetime('now','localtime'),
                            cost_usd=?, output_file=?, result_summary=? WHERE id=?
                    """, (status, cost, str(output_file), summary, task_id))
                    print(f"  {status.upper()} (${cost:.2f})")
                    if summary:
                        # Show first 500 chars of result
                        print(f"  {summary[:500]}")

        except Exception as e:
            err = str(e)[:500]
            db.execute("""
                UPDATE tasks SET status='failed', finished_at=datetime('now','localtime'),
                    error=? WHERE id=?
            """, (err, task_id))
            cascade_failure(db, task_id)
            print(f"  FAILED: {err[:200]}")

        db.commit()

        # Check if we should continue
        refreshed = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if refreshed and refreshed["status"] == "failed":
            print(f"\n  Pipeline stopped — step '{step}' failed.")
            break

    # Final status
    print(f"\n{'='*60}")
    final = db.execute("""
        SELECT status, COUNT(*) as n FROM tasks WHERE pipeline=?
        GROUP BY status ORDER BY status
    """, (pipeline,)).fetchall()
    for row in final:
        print(f"  {row['status']}: {row['n']}")
    print(f"{'='*60}\n")
    db.close()


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

    p_show = sub.add_parser("show", help="Show full task details")
    p_show.add_argument("task_id", type=int, help="Task ID")
    p_show.add_argument("--full", action="store_true", help="Show full prompt and result")

    p_approve = sub.add_parser("approve", help="Approve a pending task/pipeline")
    p_approve.add_argument("target", help="Task ID or pipeline name")

    p_log = sub.add_parser("log", help="Show event log")
    p_log.add_argument("--today", action="store_true")
    p_log.add_argument("--pipeline", help="Filter by pipeline name")
    p_log.add_argument("--project", help="Filter by project name")
    p_log.add_argument("--last", type=int, help="Show last N entries (default 50)")

    sub.add_parser("pipelines", help="Show cost/status rollup by pipeline")

    sub.add_parser("efficiency", help="Token efficiency breakdown by pipeline")

    sub.add_parser("summary", help="Generate daily summary")

    p_retry = sub.add_parser("retry", help="Reset failed/blocked task to pending")
    p_retry.add_argument("task_id", type=int, help="Task ID to retry")

    sub.add_parser("tick", help="Run one task (called by launchd)")

    p_rp = sub.add_parser("run-pipeline", help="Submit + run pipeline synchronously (interactive)")
    p_rp.add_argument("pipeline", help="Pipeline template name")
    p_rp.add_argument("--project", "-p", help="Override project")
    p_rp.add_argument("--vars", nargs="*", help="Template variables: key=value")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "approve":
        cmd_approve(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "pipelines":
        cmd_pipelines(args)
    elif args.command == "efficiency":
        cmd_efficiency(args)
    elif args.command == "summary":
        cmd_summary(args)
    elif args.command == "retry":
        cmd_retry(args)
    elif args.command == "tick":
        cmd_tick(args)
    elif args.command == "run-pipeline":
        cmd_run_pipeline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
