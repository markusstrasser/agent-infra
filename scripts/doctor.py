#!/usr/bin/env python3
"""Claude Code infrastructure health checker.

Checks hooks, settings, skills, MCP, memory, git state, and symlinks
across all configured projects. Structured pass/warn/fail output.

Usage: uv run python3 scripts/doctor.py [--project PROJECT] [--json]
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import PROJECT_ROOTS

# --- Configuration ---

PROJECTS_DIR = Path.home() / "Projects"
PROJECTS = list(PROJECT_ROOTS.keys())
from common.paths import CLAUDE_DIR
from common.db import open_db_ro
GLOBAL_SETTINGS = CLAUDE_DIR / "settings.json"
GLOBAL_CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
MEMORY_WARN_LINES = 180
MEMORY_MAX_LINES = 200


class Check:
    """Single health check result."""

    def __init__(self, name: str, scope: str):
        self.name = name
        self.scope = scope
        self.status = "pass"  # pass, warn, fail
        self.message = ""

    def warn(self, msg: str):
        self.status = "warn"
        self.message = msg
        return self

    def fail(self, msg: str):
        self.status = "fail"
        self.message = msg
        return self

    def ok(self, msg: str = ""):
        self.status = "pass"
        self.message = msg
        return self


def run(cmd: list[str], cwd: str | None = None, timeout: int = 5) -> str | None:
    """Run a command, return stdout or None on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


# --- Check Functions ---


def check_settings_json(path: Path, scope: str) -> list[Check]:
    """Validate a settings.json file."""
    c = Check("settings.json", scope)
    if not path.exists():
        return [c.warn("No settings.json")]
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [c.fail(f"Invalid JSON: {e}")]

    checks = [c.ok(f"{len(data.get('hooks', {}))} hook events")]

    # $CLAUDE_PROJECT_DIR is expanded by Claude/Codex at hook execution time.
    # For the global settings file (scope == "global") it's not bound to one
    # project, so skip path checks for those entries rather than reporting
    # bogus misses against meta's directory.
    project_dir = path.parent.parent if scope != "global" else None

    def resolve(token: str, base: Path | None = None) -> Path | None:
        if scope == "global" and "$CLAUDE_PROJECT_DIR" in token:
            return None
        # Strip surrounding quotes some hooks use to handle paths with spaces
        token = token.strip("'\"")
        if project_dir is not None:
            token = token.replace("$CLAUDE_PROJECT_DIR", str(project_dir))
        p = Path(os.path.expandvars(token)).expanduser()
        # Relative hook paths (.claude/hooks/foo.sh) resolve relative to the
        # base directory — usually the project dir (cwd Claude/Codex runs hooks
        # under), but `uv run --directory X` overrides this.
        resolve_base = base if base is not None else project_dir
        if not p.is_absolute() and resolve_base is not None:
            p = resolve_base / p
        return p

    # Validate hook command paths exist
    for event, hook_groups in data.get("hooks", {}).items():
        for group in hook_groups:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                cmd = hook.get("command", "")
                # Use shlex so we don't pull tokens out of quoted strings
                # (e.g. error messages that mention ".sh/.py" or paths
                # embedded in `python3 -c '...'` blocks).
                try:
                    parts = shlex.split(cmd, posix=True)
                except ValueError:
                    parts = cmd.split()
                # `uv run --directory X script.py` resolves script.py against X,
                # not the project dir. Honor that here so the script check
                # doesn't false-positive cross-project hooks.
                resolve_base = project_dir
                for i, p in enumerate(parts):
                    if p == "--directory" and i + 1 < len(parts):
                        resolve_base = Path(os.path.expandvars(parts[i + 1])).expanduser()
                        break
                # Find the script file — may be the command itself or an argument to bash/python3
                script_token = next((p for p in parts if p.endswith(('.sh', '.py'))), None)
                if script_token:
                    script = resolve(script_token, resolve_base)
                elif parts and (parts[0].startswith(("/", "~", "$"))):
                    script = resolve(parts[0], resolve_base)
                else:
                    script = None
                if script is not None:
                    hc = Check(f"hook:{event}:{script.name}", scope)
                    if not script.exists():
                        checks.append(hc.fail(f"Script missing: {script}"))
                    elif not os.access(script, os.X_OK):
                        checks.append(hc.fail(f"Not executable: {script}"))
                    else:
                        checks.append(hc.ok())

    return checks


def check_skill_symlinks(project_dir: Path) -> list[Check]:
    """Check for broken skill symlinks."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.exists():
        return []

    checks = []
    for entry in skills_dir.iterdir():
        if entry.is_symlink():
            c = Check(f"skill:{entry.name}", project_dir.name)
            if not entry.exists():  # broken symlink
                checks.append(c.fail(f"Broken symlink → {os.readlink(entry)}"))
            else:
                checks.append(c.ok())
    return checks


def check_skill_frontmatter(project_dir: Path) -> list[Check]:
    """Validate SKILL.md files have required frontmatter fields."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.exists():
        return []

    checks = []
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            # Check if it's a symlinked SKILL.md directly
            if skill_dir.is_symlink():
                continue
            c = Check(f"frontmatter:{skill_dir.name}", project_dir.name)
            checks.append(c.warn("No SKILL.md"))
            continue

        c = Check(f"frontmatter:{skill_dir.name}", project_dir.name)
        try:
            content = skill_md.read_text()
            # Check for frontmatter delimiter
            if not content.startswith("---"):
                checks.append(c.warn("Missing frontmatter"))
                continue
            # Extract frontmatter
            parts = content.split("---", 2)
            if len(parts) < 3:
                checks.append(c.warn("Malformed frontmatter"))
                continue
            # Basic field check
            fm = parts[1]
            required = ["name"]
            missing = [f for f in required if f"{f}:" not in fm]
            if missing:
                checks.append(c.warn(f"Missing fields: {', '.join(missing)}"))
            else:
                checks.append(c.ok())
        except Exception as e:
            checks.append(c.fail(f"Read error: {e}"))

    return checks


def check_memory_health() -> list[Check]:
    """Check MEMORY.md sizes across projects."""
    checks = []
    memory_base = CLAUDE_DIR / "projects"
    if not memory_base.exists():
        return []

    for proj_dir in memory_base.iterdir():
        if not proj_dir.is_dir():
            continue
        memory_dir = proj_dir / "memory"
        if not memory_dir.exists():
            continue
        memory_md = memory_dir / "MEMORY.md"
        if not memory_md.exists():
            continue

        # Extract project name from path
        proj_name = proj_dir.name.split("-")[-1] if "-" in proj_dir.name else proj_dir.name
        c = Check(f"memory:{proj_name}", "global")
        lines = memory_md.read_text().count("\n")
        if lines > MEMORY_MAX_LINES:
            checks.append(c.fail(f"{lines} lines (max {MEMORY_MAX_LINES}, will be truncated)"))
        elif lines > MEMORY_WARN_LINES:
            checks.append(c.warn(f"{lines} lines (warn at {MEMORY_WARN_LINES})"))
        else:
            checks.append(c.ok(f"{lines} lines"))

    return checks


def check_test_health() -> list[Check]:
    """Surface the latest per-repo test-suite outcome (scripts/test_health.py).

    A suite that did NOT complete (crash / collection-abort / timeout) is a
    FAIL: it produces no regression verdict, so drift accumulates invisibly.
    A stale sentinel (>2 days) is itself a blind spot → warn."""
    log = CLAUDE_DIR / "test-health.jsonl"
    if not log.exists():
        return [Check("test-health", "global").warn("never run — `just test-health`")]
    latest: dict[str, dict] = {}
    try:
        for line in log.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                latest[rec["repo"]] = rec  # append-ordered → last wins
    except (json.JSONDecodeError, OSError, KeyError):
        return [Check("test-health", "global").warn("unreadable test-health.jsonl")]

    checks: list[Check] = []
    newest = ""
    for repo, rec in sorted(latest.items()):
        newest = max(newest, rec.get("ts", ""))
        c = Check(f"test-health:{repo}", "global")
        counts = rec.get("counts", {})
        if not rec.get("completed"):
            checks.append(c.fail(f"suite did NOT complete: {rec.get('outcome', '?')}"))
        elif rec.get("regressed"):
            # got worse since last run — escalate above chronic-but-stable failures
            checks.append(c.fail(f"regressed: {rec.get('regression_note', '?')}"))
        elif counts.get("failed") or counts.get("errors"):
            checks.append(c.warn(f"{counts.get('failed', 0)} failed, {counts.get('errors', 0)} errors (stable)"))
        else:
            checks.append(c.ok(f"{counts.get('passed', 0)} passed"))

    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(newest)
        if age > timedelta(days=2):
            checks.append(Check("test-health:freshness", "global").warn(
                f"last run {age.days}d ago — sentinel may not be running"))
    except (ValueError, TypeError):
        pass
    return checks


def check_git_state(project_dir: Path) -> list[Check]:
    """Check git repository health."""
    c = Check("git", project_dir.name)
    if not (project_dir / ".git").exists():
        return [c.warn("Not a git repo")]

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(project_dir))
    if branch is None:
        return [c.fail("git rev-parse failed")]

    checks = [c.ok(f"branch={branch}")]

    # Check for uncommitted changes
    status = run(["git", "status", "--porcelain"], cwd=str(project_dir))
    if status:
        line_count = len(status.strip().split("\n"))
        sc = Check("git:uncommitted", project_dir.name)
        checks.append(sc.warn(f"{line_count} uncommitted changes"))

    return checks


def check_mcp(project_dir: Path) -> list[Check]:
    """Check MCP configuration exists and is valid JSON."""
    mcp_path = project_dir / ".mcp.json"
    c = Check("mcp", project_dir.name)
    if not mcp_path.exists():
        return [c.warn("No .mcp.json")]
    try:
        with open(mcp_path) as f:
            data = json.load(f)
        servers = data.get("mcpServers", {})
        return [c.ok(f"{len(servers)} servers configured")]
    except json.JSONDecodeError as e:
        return [c.fail(f"Invalid JSON: {e}")]


def check_stale_agents() -> list[Check]:
    """Check for subagent JSONL files with no matching process (crashed agents)."""
    checks = []
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return checks

    stale_threshold = 30 * 60  # 30 minutes
    max_age = 2 * 60 * 60  # only check last 2 hours (older = completed, not crashed)
    now = time.time()

    for subagents_dir in projects_dir.glob("*/*/subagents"):
        for jsonl in subagents_dir.glob("agent-*.jsonl"):
            age = now - jsonl.stat().st_mtime
            if age < stale_threshold or age > max_age:
                continue
            # Extract agent ID, check if any claude process references it
            agent_id = jsonl.stem.replace("agent-", "")
            try:
                ps = subprocess.run(
                    ["pgrep", "-f", agent_id], capture_output=True, timeout=5
                )
                has_process = ps.returncode == 0
            except Exception:
                has_process = True  # fail open — don't report if pgrep fails

            if not has_process:
                c = Check("stale-agent", agent_id[:12])
                age_min = int(age / 60)
                c.warn(f"No process found, last write {age_min}m ago: {jsonl.name}")
                checks.append(c)

    if not checks:
        c = Check("stale-agents", "global")
        checks.append(c.ok("No stale agents"))
    return checks


def check_gitignore(project_dir: Path) -> list[Check]:
    """Check that .claude/ artifacts are gitignored."""
    c = Check("gitignore:.claude", project_dir.name)
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        return [c.warn("No .gitignore")]
    content = gitignore.read_text()
    if ".claude/" in content or ".claude" in content:
        return [c.ok()]
    # Check if plans dir would be committed
    plans = project_dir / ".claude" / "plans"
    if plans.exists():
        return [c.warn(".claude/plans/ exists but .claude not in .gitignore")]
    return [c.ok("No .claude artifacts to ignore")]


def check_codebase_map_gitignore(project_dir: Path) -> list[Check]:
    """Mapped repos must gitignore generated codebase-map outputs."""
    from codebase_map_config import assert_maps_gitignored, config_for_repo

    cfg = config_for_repo(project_dir)
    if not cfg:
        return []
    c = Check("gitignore:codebase-map", cfg.name)
    try:
        assert_maps_gitignored(cfg)
    except RuntimeError as exc:
        return [c.fail(str(exc))]
    return [c.ok("generated map outputs gitignored + untracked")]


def check_launchd_script_integrity() -> list[Check]:
    """A loaded launchd job whose ProgramArguments script was deleted.

    This is the LEADING orphan signal — distinct from a non-zero last_exit
    (lagging: the job must fire and fail first). A consolidation that deletes a
    wrapper .sh but leaves the plist loaded makes the job fail `exit 127` daily,
    silently, until someone reads `launchctl list`. system_inventory owns the
    truth; this is doctor's daily reader (the d4c553a consolidation leaked 4
    such orphans for days before a SWEEP caught them — 2026-06-24)."""
    try:
        from system_inventory import collect_orphan_scripts
        orphans = collect_orphan_scripts()
    except Exception as exc:
        return [Check("launchd-integrity", "global").warn(f"check failed: {exc}")]
    if not orphans:
        return [Check("launchd-integrity", "global").ok("all loaded agent-infra jobs resolve their scripts")]
    checks = []
    for o in orphans:
        exit_note = f", exit {o['last_exit']}" if o.get("last_exit") else ""
        checks.append(Check(f"launchd-integrity:{o['name']}", "global").fail(
            f"loaded but script deleted{exit_note}: {', '.join(o['missing_paths'])} "
            f"— `launchctl bootout gui/$(id -u)/{o['label']}` + rm the plist, or restore the script"))
    return checks


def check_launchd_spawn_health() -> list[Check]:
    """A loaded launchd job that launchd cannot even spawn (EX_CONFIG, no process).

    Distinct from script-integrity (script deleted) and from a job that runs and
    fails: `job state = spawn failed` means launchd could not exec at all — e.g.
    StandardOutPath unwritable. 2026-07-11 incident: ~/.claude/logs was symlinked
    to /Volumes/2TBPNY; ALL 11 agent-infra jobs spawn-failed silently for 3 days
    (indexer, archive, spend-alarm, vendor-sweep, ...) until a storage question
    surfaced it. launchctl list shows only the stale last-exit 78 — this check
    reads the authoritative per-job state."""
    uid = os.getuid()
    try:
        listing = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
    except Exception as exc:
        return [Check("launchd-spawn", "global").warn(f"launchctl list failed: {exc}")]
    labels = [line.split()[-1] for line in listing.splitlines() if "com.agent-infra." in line]
    failed = []
    for label in labels:
        try:
            info = subprocess.run(["launchctl", "print", f"gui/{uid}/{label}"],
                                  capture_output=True, text=True, timeout=10).stdout
        except Exception:
            continue
        if "job state = spawn failed" in info:
            failed.append(label)
    if not failed:
        return [Check("launchd-spawn", "global").ok(f"no spawn-failed jobs among {len(labels)} loaded")]
    return [Check(f"launchd-spawn:{label}", "global").fail(
        "job state = spawn failed — launchd cannot exec it (check StandardOut/ErrorPath "
        "is a writable LOCAL path, not a symlink onto an external volume; then "
        f"`launchctl kickstart -k gui/{uid}/{label}`)") for label in failed]


def check_agentlogs_archive_recency() -> list[Check]:
    """The weekly keep-everything archive (agentlogs-*.db.zst on 2TBPNY) went stale.

    Retention safety depends on archive cadence (weekly) < prune retention (30d);
    a quietly-failing weekly job erodes that invariant until pruned history is
    unrecoverable. Warn at >14d (two missed weeks), fail at >24d (approaching the
    30d prune window). Skips cleanly when the volume isn't mounted."""
    c = Check("agentlogs-archive-recency", "global")
    root = Path("/Volumes/2TBPNY/agentlogs-archive")
    if not root.is_dir():
        return [c.warn("2TBPNY not mounted — archive recency unverifiable (plug in the SSD)")]
    snaps = sorted(root.glob("agentlogs-*.db.zst"))
    if not snaps:
        return [c.fail(f"no agentlogs-*.db.zst snapshots in {root}")]
    age_days = (time.time() - snaps[-1].stat().st_mtime) / 86400
    msg = f"newest snapshot {snaps[-1].name} is {age_days:.1f}d old (weekly cadence, 30d prune window)"
    if age_days > 24:
        return [c.fail(msg + " — run `just agentlogs-archive` NOW, before prune outruns the archive")]
    if age_days > 14:
        return [c.warn(msg + " — check com.agent-infra.agentlogs-archive (spawn health, volume mounted at Sun 03:30)")]
    return [c.ok(msg)]


def check_metered_spend() -> list[Check]:
    """Surface today's genuinely-billed (transport==api) llmx spend across ALL surfaces.

    The foreground-Bash cost-guard hook cannot see metered calls made inside backgrounded
    workers / Python subprocesses (the $70-silent-spend gap, improvement-log 2026-06-25).
    Every llmx call lands in the funnel ledger regardless of surface, so a daily rollup over
    `transport==api` rows makes background spend visible. Warn at $10, fail at the
    constitutional $25 daily cap (invariants.md). Observability/alarm only — hard block
    enforcement is the human-gated decisions-pending fork.
    """
    c = Check("metered-spend:today", "global")
    out = run(
        ["uv", "run", "python3", str(Path(__file__).parent / "usage-check.py"),
         "--metered-today", "--json"],
        cwd=str(Path(__file__).parent.parent), timeout=20,
    )
    if out is None:
        return [c.ok("usage-check unavailable — skipped")]
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return [c.ok("unparseable — skipped")]
    spend = data.get("metered_total_usd", 0.0)
    calls = data.get("metered_calls", 0)
    top = data.get("by_spender", [])
    who = f" top={top[0]['caller']}@{top[0]['repo']}" if top else ""
    if spend >= 25:
        return [c.fail(f"${spend:.2f} metered today ({calls} calls, cap $25){who}")]
    if spend >= 10:
        return [c.warn(f"${spend:.2f} metered today ({calls} calls){who}")]
    return [c.ok(f"${spend:.2f} metered today ({calls} calls)")]


def check_telemetry_freshness() -> list[Check]:
    """Detect silent hook failures by comparing transcript activity to receipt/log output."""
    checks = []
    now = time.time()
    cutoff = now - 86400  # 24 hours
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=24)

    # 1. Count JSONL transcript files modified in last 24h
    projects_base = CLAUDE_DIR / "projects"
    transcript_count = 0
    if projects_base.exists():
        for jsonl in projects_base.glob("-Users-alien-Projects-*/*.jsonl"):
            try:
                if jsonl.stat().st_mtime > cutoff:
                    transcript_count += 1
            except OSError:
                continue

    # 2. Count receipt entries in last 24h
    receipts_path = CLAUDE_DIR / "session-receipts.jsonl"
    receipt_count = 0
    if receipts_path.exists():
        try:
            for line in receipts_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("ts", "")
                    if ts:
                        entry_dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                        if entry_dt >= cutoff_dt:
                            receipt_count += 1
                except (json.JSONDecodeError, ValueError):
                    continue
        except OSError:
            pass

    # 3. Count session-log entries in last 24h
    session_log_path = CLAUDE_DIR / "session-log.jsonl"
    session_log_count = 0
    if session_log_path.exists():
        try:
            for line in session_log_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("ts", "")
                    if ts:
                        entry_dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                        if entry_dt >= cutoff_dt:
                            session_log_count += 1
                except (json.JSONDecodeError, ValueError):
                    continue
        except OSError:
            pass

    # 4-7. Compare and report
    if transcript_count == 0:
        c = Check("telemetry:freshness", "global")
        checks.append(c.ok("No sessions in last 24h — skipped"))
        return checks

    # Receipt check
    c_receipt = Check("telemetry:receipts", "global")
    if receipt_count == 0:
        c_receipt.fail(
            f"SessionEnd receipt hook not firing ({transcript_count} transcripts, 0 receipts in 24h)"
        )
    elif receipt_count / transcript_count < 0.5:
        c_receipt.warn(
            f"Receipt coverage low ({receipt_count}/{transcript_count} = {receipt_count/transcript_count:.0%} in 24h)"
        )
    else:
        c_receipt.ok(f"{receipt_count} receipts / {transcript_count} transcripts in 24h")
    checks.append(c_receipt)

    # Session-log check
    c_log = Check("telemetry:session-log", "global")
    if session_log_count == 0:
        c_log.fail(
            f"SessionEnd session-log hook not firing ({transcript_count} transcripts, 0 session-log entries in 24h)"
        )
    elif session_log_count / transcript_count < 0.5:
        c_log.warn(
            f"Session-log coverage low ({session_log_count}/{transcript_count} = {session_log_count/transcript_count:.0%} in 24h)"
        )
    else:
        c_log.ok(f"{session_log_count} log entries / {transcript_count} transcripts in 24h")
    checks.append(c_log)

    # Close-queue drain check: unprocessed intents aging past 48h = the drain is
    # wedged (the 2026-06-18→07-06 starvation sat 18 days with zero signal; a
    # backlog-age check catches the class on day 2 regardless of digest cadence).
    c_drain = Check("telemetry:close-queue-drain", "global")
    queue_dir = CLAUDE_DIR / "close-queue"
    stale_cutoff = now - 48 * 3600
    unprocessed_total = 0
    stale_count = 0
    oldest_age_h = 0.0
    if queue_dir.is_dir():
        for intent_file in queue_dir.glob("*.json"):
            try:
                intent = json.loads(intent_file.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if intent.get("processed"):
                continue
            unprocessed_total += 1
            mtime = intent_file.stat().st_mtime
            if mtime < stale_cutoff:
                stale_count += 1
                oldest_age_h = max(oldest_age_h, (now - mtime) / 3600)
    if stale_count:
        c_drain.fail(
            f"{stale_count} close-intents unprocessed >48h (oldest {oldest_age_h:.0f}h; "
            f"{unprocessed_total} pending total) — run reflect_session_close.py --drain"
        )
    else:
        c_drain.ok(f"{unprocessed_total} pending close-intents, none older than 48h")
    checks.append(c_drain)

    return checks


# --- Main ---


def check_orphaned_generators() -> list[Check]:
    """Report-only ratchet: flag scripts/ generators with no consumer.

    Standing consumer for the orphaned-generator disease (generation-without-
    consumption). Advisory — never fails the suite; a flag means re-verify by hand
    via `just orphan-check`. See research/2026-06-08-orphaned-generator-sweep.md."""
    c = Check("global:orphan-generators", "global")
    try:
        import orphan_check
        rep = orphan_check.scan()
    except Exception as e:  # noqa: BLE001 — advisory, fail open
        return [c.warn(f"orphan_check unavailable: {str(e)[:80]}")]
    flagged = rep["flagged"]
    if not flagged:
        return [c.ok(f"{rep['total_generators']} generators, 0 orphaned")]
    names = ", ".join(r["script"] for r in flagged[:6])
    extra = f" (+{len(flagged) - 6})" if len(flagged) > 6 else ""
    return [c.warn(f"{len(flagged)} candidate orphan(s): {names}{extra} — "
                   f"re-verify via `just orphan-check`")]


def check_orphaned_findings() -> list[Check]:
    """Report-only ratchet: flag trending-scout memos with adopt-grade verdicts
    not yet routed to improvement-log (the loop's read path).

    Sibling to check_orphaned_generators — same generation-without-consumption
    disease, findings axis. Advisory; a flag means a memo's findings never reached
    the loop. Re-verify + promote live ones via `just orphan-findings`. See
    decisions/2026-06-04-consumption-over-autonomy.md Finding 1."""
    c = Check("global:orphan-findings", "global")
    try:
        import orphan_findings
        rep = orphan_findings.scan(all_memos=True)
    except Exception as e:  # noqa: BLE001 — advisory, fail open
        return [c.warn(f"orphan_findings unavailable: {str(e)[:80]}")]
    flagged = rep["flagged_memos"]
    if not flagged:
        return [c.ok(f"{rep['actionable']} actionable verdicts, 0 un-harvested")]
    memos = ", ".join(m["memo"].replace("trending-scout-", "ts-").replace(".md", "")
                      for m in flagged[:5])
    extra = f" (+{len(flagged) - 5})" if len(flagged) > 5 else ""
    return [c.warn(f"{rep['orphaned_findings']} un-harvested finding(s) in "
                   f"{len(flagged)} memo(s): {memos}{extra} — "
                   f"promote live ones via `just orphan-findings`")]


def check_decisions_pending() -> list[Check]:
    """Surface the escalation queue so it isn't write-only.

    decisions-pending/ holds sign-off-ready items the loop escalated (taste/money/
    irreversible/shared/discovery). Nothing else notifies the human, so an unread
    item ages silently — defeating the 'wake up to N ideas, say yes/no' point.
    Advisory: report the count + flag any item older than 7 days."""
    c = Check("global:decisions-pending", "global")
    d = PROJECTS_DIR / "agent-infra" / "decisions-pending"
    if not d.is_dir():
        return [c.ok("no escalation queue")]
    items = [p for p in d.glob("*.md") if p.name != "README.md"]
    if not items:
        return [c.ok("0 pending decisions")]
    import time
    stale = [p for p in items if (time.time() - p.stat().st_mtime) > 7 * 86400]
    names = ", ".join(p.stem for p in items[:5])
    if stale:
        return [c.warn(f"{len(items)} pending decision(s) — {len(stale)} >7d unread: {names} — review/disposition")]
    return [c.warn(f"{len(items)} pending decision(s) awaiting sign-off: {names}")]


def check_agentlogs_indexer() -> list[Check]:
    """Surface a stalled cross-vendor session indexer.

    The agentlogs indexer (launchd, every 2h) is the substrate for the agentlogs
    CLI, /leverage's measure step, and the tool-friction back-edge. It can stall
    silently: a single hung `executemany` holds the fcntl lock, every later cron
    fire hits IndexerLockBusy and exits 0, and the vendor's `indexer_runs` row
    sits 'running' forever — which is exactly how Codex went dark for a month
    (PID 1897, 18h CPU). `v_indexer_health` recorded it the whole time but had
    zero readers. This is that reader: warn if a vendor hasn't had a successful
    index in 48h, or if a run has been 'running' for >2h (a dead/hung holder).
    """
    import sqlite3

    checks: list[Check] = []
    db_path = CLAUDE_DIR / "agentlogs.db"
    if not db_path.exists():
        return [Check("indexer", "global").warn("agentlogs.db not found")]
    try:
        # mode=ro (not immutable=1) — the DB is live/WAL; immutable would risk
        # stale reads while the indexer writes. ro respects WAL + locks.
        con = open_db_ro(db_path)
    except sqlite3.Error as exc:
        return [Check("indexer", "global").warn(f"cannot open agentlogs.db: {exc}")]
    try:
        rows = con.execute(
            "SELECT vendor, last_success_at, success_7d FROM v_indexer_health"
        ).fetchall()
        stuck = con.execute(
            "SELECT vendor, count(*) FROM indexer_runs "
            "WHERE status='running' AND started_at < datetime('now','-2 hours') "
            "GROUP BY vendor"
        ).fetchall()
    except sqlite3.Error as exc:
        return [Check("indexer", "global").warn(f"query failed: {exc}")]
    finally:
        con.close()

    now = datetime.now(timezone.utc)
    for vendor, last_success_at, success_7d in rows:
        c = Check(f"indexer:{vendor}", "global")
        if not last_success_at:
            checks.append(c.warn("no successful index on record"))
            continue
        try:
            last = datetime.fromisoformat(last_success_at.replace("Z", "+00:00"))
            age_h = (now - last).total_seconds() / 3600
        except (ValueError, AttributeError):
            checks.append(c.warn(f"unparseable last_success_at={last_success_at!r}"))
            continue
        if age_h > 48:
            checks.append(c.warn(f"stale: last success {age_h:.0f}h ago (>48h), {success_7d} ok/7d"))
        else:
            checks.append(c.ok(f"fresh ({age_h:.0f}h ago)"))

    for vendor, n in stuck:
        checks.append(Check(f"indexer:{vendor}", "global").warn(
            f"{n} run(s) stuck 'running' >2h — likely a hung/dead holder; reap + investigate"))

    try:
        row = con.execute("SELECT MAX(authored_at) FROM git_commits").fetchone()
        if row and row[0]:
            try:
                last_git = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
                age_d = (now - last_git).total_seconds() / 86400
                c = Check("agentlogs:git-import-cache", "global")
                if age_d > 3:
                    checks.append(c.warn(
                        f"git_commits cache stale: newest {age_d:.0f}d ago (>3d) — "
                        f"run `agentlogs git-import` or rely on whence reconstruct"))
                else:
                    checks.append(c.ok(f"git_commits fresh ({age_d:.1f}d ago)"))
            except (ValueError, TypeError):
                pass
    except sqlite3.Error:
        pass
    return checks


def check_uv_tool_editables() -> list[Check]:
    """Validate uv-tool editable installs still point at real source dirs.

    A `uv tool install --editable` records the source dir in uv-receipt.toml
    (`editable = "..."`) and in a `_editable_impl_*.pth`. When a package is
    promoted/moved — e.g. a package moved from a monorepo to a standalone repo —
    the pointer goes stale: the
    import can half-work off a leftover copy while the CLI entry point is gone,
    and NO launchd/import check catches it (the library still imports; only
    invoking the CLI fails). 2026-06-14: the `corpus` CLI was dead for exactly
    this reason and a full /improve health loop missed it — every check was
    green because none exercised this surface. Deterministic: the recorded
    source dir either exists or it doesn't.
    """
    import re

    checks: list[Check] = []
    tools_dir = Path.home() / ".local" / "share" / "uv" / "tools"
    if not tools_dir.is_dir():
        return checks  # no uv tools on this machine

    seen: set[tuple[str, str]] = set()  # (tool, source_dir)
    for tool_dir in sorted(tools_dir.iterdir()):
        if not tool_dir.is_dir():
            continue
        tool = tool_dir.name
        receipt = tool_dir / "uv-receipt.toml"
        if receipt.exists():
            for m in re.finditer(r'editable\s*=\s*"([^"]+)"', receipt.read_text()):
                seen.add((tool, m.group(1)))
        for pth in tool_dir.glob("lib/python*/site-packages/_editable_impl_*.pth"):
            content = pth.read_text().strip()
            target = content.splitlines()[0].strip() if content else ""
            if target.startswith("/"):
                seen.add((tool, target))

    if not seen:
        return checks
    dead = [(t, s) for t, s in sorted(seen) if not Path(s).is_dir()]
    for tool, src in dead:
        checks.append(Check(f"uv-tool:{tool}", "global").warn(
            f"editable -> MISSING {src} (stale pointer; package moved? "
            f"fix: uv tool install --force --editable <new-path>)"))
    checks.append(Check("uv-tools", "global").ok(
        f"{len(seen) - len(dead)}/{len(seen)} editable installs resolve"))
    return checks


def check_approval_tiers() -> list[Check]:
    """Validate config/approval-tiers.json ↔ hook files ↔ global PreToolUse wiring."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import approval_tiers as at  # noqa: E402

    c = Check("approval-tiers", "global")
    chk = at.validate_manifest()
    if chk.missing_files:
        return [c.fail(f"missing hook files: {', '.join(chk.missing_files[:5])}"
                        + ("…" if len(chk.missing_files) > 5 else ""))]
    if chk.uncovered_global:
        return [c.warn(f"{len(chk.uncovered_global)} global pretool(s) not in manifest: "
                       f"{', '.join(chk.uncovered_global[:4])}"
                       + ("…" if len(chk.uncovered_global) > 4 else ""))]
    n = len(at.manifest_hooks())
    g = len(at.global_pretool_hooks())
    return [c.ok(f"{n} manifest hooks, {g} global pretools covered")]


def check_critique_routing_verdict() -> list[Check]:
    """Fail-closed gate: ROUTING_VERDICT JSON must parse; pending freezes cross2 default."""
    c = Check("evals:critique-routing-verdict", "global")
    path = PROJECTS_DIR / "evals" / "critique_replay" / "ROUTING_VERDICT.md"
    if not path.is_file():
        return [c.warn("ROUTING_VERDICT.md missing — model-review default stays standard")]
    text = path.read_text()
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        return [c.fail("ROUTING_VERDICT.md missing ```json block")]
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        return [c.fail(f"ROUTING_VERDICT JSON invalid: {exc}")]
    if data.get("status") == "pending":
        return [c.ok("ROUTING_VERDICT pending — defaults frozen at standard")]
    preset = data.get("default_preset")
    if not preset:
        return [c.fail("ROUTING_VERDICT missing default_preset")]
    return [c.ok(f"default_preset={preset}")]


def check_cross_harness_shell_env() -> list[Check]:
    """Cross-harness shell env parity — zsh footguns + Cursor hook gap detector.

    Catches the class fixed 2026-06-28: agent shells load full .zshrc (nomatch,
    alias t/dl collisions) while Cursor lacked PreToolUse guards. A dead `corpus`
    CLI hid for days because doctor never exercised home-dir shell config."""
    home = Path.home()
    zshenv = home / ".zshenv"
    zshrc = home / ".zshrc"
    agent_safe = PROJECTS_DIR / "skills" / "hooks" / "agent-zsh-safe.sh"
    cursor_hooks = home / ".cursor" / "hooks.json"
    cursor_guards = PROJECTS_DIR / "skills" / "hooks" / "cursor_shell_guards.py"
    claude_uv = PROJECTS_DIR / "skills" / "hooks" / "pretool-uv-python-guard.py"

    checks: list[Check] = []

    c = Check("global:shell-env-agent-zsh-safe", "global")
    if not agent_safe.is_file():
        checks.append(c.fail(f"missing {agent_safe}"))
    elif not zshenv.is_file() or "agent-zsh-safe.sh" not in zshenv.read_text():
        checks.append(c.fail("~/.zshenv does not source agent-zsh-safe.sh"))
    elif not zshrc.is_file() or "AGENT_ZSH_SAFE_PHASE=rc" not in zshrc.read_text():
        checks.append(c.fail("~/.zshrc missing rc-phase agent-zsh-safe sourcing"))
    else:
        checks.append(c.ok("agent-zsh-safe wired in zshenv + zshrc"))

    c = Check("global:shell-env-cursor-hooks", "global")
    if not cursor_hooks.is_file():
        checks.append(c.fail("missing ~/.cursor/hooks.json (Cursor shell guards)"))
    elif "cursor_shell_guards.py" not in cursor_hooks.read_text():
        checks.append(c.fail("~/.cursor/hooks.json missing cursor_shell_guards.py"))
    elif not cursor_guards.is_file():
        checks.append(c.fail(f"missing {cursor_guards.name}"))
    else:
        checks.append(c.ok("Cursor shell guards wired"))

    c = Check("global:shell-env-claude-uv-guard", "global")
    # Standalone hook OR absorbed into pretool-bash-dispatch (fleet dispatcher,
    # 2026-07-13) — settings may only name the dispatcher while the gate still
    # runs as GATES entry "uv-python-guard".
    if not claude_uv.is_file():
        checks.append(c.warn("pretool-uv-python-guard.py missing"))
    elif GLOBAL_SETTINGS.is_file():
        settings_txt = GLOBAL_SETTINGS.read_text()
        named = "pretool-uv-python-guard.py" in settings_txt
        via_dispatch = "pretool-bash-dispatch.py" in settings_txt
        if named or via_dispatch:
            how = "standalone" if named else "via bash-dispatch"
            checks.append(c.ok(f"Claude uv-python guard present ({how})"))
        else:
            checks.append(c.warn("Claude global settings missing uv-python guard"))
    else:
        checks.append(c.warn("Claude global settings missing"))

    return checks


def run_all_checks(project_filter: str | None = None) -> list[Check]:
    """Run all checks, optionally filtered to one project."""
    all_checks: list[Check] = []

    # Global checks
    if not project_filter:
        all_checks.extend(check_settings_json(GLOBAL_SETTINGS, "global"))
        all_checks.extend(check_memory_health())
        all_checks.extend(check_stale_agents())
        all_checks.extend(check_telemetry_freshness())
        all_checks.extend(check_metered_spend())
        all_checks.extend(check_test_health())
        all_checks.extend(check_orphaned_generators())
        all_checks.extend(check_orphaned_findings())
        all_checks.extend(check_decisions_pending())
        all_checks.extend(check_agentlogs_indexer())
        all_checks.extend(check_launchd_script_integrity())
        all_checks.extend(check_launchd_spawn_health())
        all_checks.extend(check_agentlogs_archive_recency())
        all_checks.extend(check_uv_tool_editables())
        all_checks.extend(check_approval_tiers())
        all_checks.extend(check_critique_routing_verdict())
        all_checks.extend(check_cross_harness_shell_env())

        # Global CLAUDE.md
        gc = Check("global:CLAUDE.md", "global")
        if GLOBAL_CLAUDE_MD.exists():
            lines = GLOBAL_CLAUDE_MD.read_text().count("\n")
            all_checks.append(gc.ok(f"{lines} lines"))
        else:
            all_checks.append(gc.fail("Missing"))

    # Per-project checks
    for proj in PROJECTS:
        if project_filter and proj != project_filter:
            continue
        proj_dir = PROJECTS_DIR / proj
        if not proj_dir.exists():
            c = Check("project", proj)
            all_checks.append(c.warn(f"Directory not found: {proj_dir}"))
            continue

        settings = proj_dir / ".claude" / "settings.json"
        all_checks.extend(check_settings_json(settings, proj))
        all_checks.extend(check_skill_symlinks(proj_dir))
        all_checks.extend(check_skill_frontmatter(proj_dir))
        all_checks.extend(check_git_state(proj_dir))
        all_checks.extend(check_mcp(proj_dir))
        all_checks.extend(check_gitignore(proj_dir))
        all_checks.extend(check_codebase_map_gitignore(proj_dir))

    return all_checks


from common.console import con as _con


def print_results(checks: list[Check], as_json: bool = False):
    """Print check results."""
    if as_json:
        out = [{"name": c.name, "scope": c.scope, "status": c.status, "message": c.message} for c in checks]
        print(json.dumps(out, indent=2))
        return

    # Group by scope
    by_scope: dict[str, list[Check]] = {}
    for c in checks:
        by_scope.setdefault(c.scope, []).append(c)

    total = len(checks)
    passes = sum(1 for c in checks if c.status == "pass")
    warns = sum(1 for c in checks if c.status == "warn")
    fails = sum(1 for c in checks if c.status == "fail")

    for scope in sorted(by_scope.keys()):
        scope_checks = by_scope[scope]
        _con.header(scope)
        for c in scope_checks:
            label = f"{c.name}  {c.message}" if c.message else c.name
            getattr(_con, c.status, _con.ok)(label)

    _con.summary(total, ok=passes, warn=warns, fail=fails)


def main():
    project_filter = None
    as_json = False

    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--project" and args:
            project_filter = args.pop(0)
        elif arg == "--json":
            as_json = True
        elif arg in ("--help", "-h"):
            print((__doc__ or "").strip())
            sys.exit(0)

    checks = run_all_checks(project_filter)
    print_results(checks, as_json)

    # Exit code: 1 if any failures
    if any(c.status == "fail" for c in checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
