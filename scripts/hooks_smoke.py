#!/usr/bin/env python3
"""Claude hook smoke — catch silently-dead hooks at edit time.

# Gov-ID: hook:hooks-smoke-gate
# goal: silently-dead hooks (SyntaxError/missing-file/bad-shape hidden by fail-open traps) go undetected for weeks
# verifier: scripts/hooks_smoke.py (self — deterministic, no LLM)
# blast_radius: local

Pipes canned event JSON through every registered command hook in
~/.claude/settings.json and per-repo .claude/settings.json, inside a throwaway
git repo, and flags the failure classes that `trap 'exit 0' ERR` + 2>/dev/null
hide in production:

- interpreter death on stderr (Traceback, SyntaxError, ImportError,
  ModuleNotFoundError, "command not found") even when the exit code is 0
- stdout that starts with '{' but is not a valid JSON object
- unexpected non-zero exits (anything but 0, or 2 with a block-ish message)
  on benign smoke input
- timeouts
- PreToolUse `updatedInput` rewrites with unknown or missing tool-input keys
  (CC 2.1.300 drops unknown keys and denies invalid input), driven by
  REWRITE_CASES so every mutator actually rewrites at least once
- a hook-env `python3` older than 3.10 on a clean PATH
- hook commands whose script path is cwd-relative (dead from any subdirectory
  or worktree); linted across every ~/Projects/*/.claude/settings*.json

Evidence: 2026-06-11 — the Stop auto-commit hook was dead for weeks from a
SyntaxError swallowed by its fail-open trap; three Stop advisories were dead
from an invalid output shape. Both classes are invisible in normal operation.

Reuses the hook enumeration + payload machinery from codex_hook_compat.py
(settings.json and .codex/hooks.json share the same `hooks` schema).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_hook_compat import (  # noqa: E402
    BLOCK_RE,
    HookRef,
    load_hooks,
    matcher_tools,
    select_tool_name,
    smoke_payload,
)
from common.project_registry import MIRRORED_REPOS  # noqa: E402

HOME = Path.home()
GLOBAL_SETTINGS = HOME / ".claude" / "settings.json"
SESSION_ID = "hooks-smoke"

# Interpreter-death markers on stderr — fail even when exit code is 0,
# because fail-open traps and 2>/dev/null hide these in production.
DEATH_RE = re.compile(
    r"Traceback \(most recent call last\)|SyntaxError|ModuleNotFoundError"
    r"|ImportError|command not found|/bin/sh: .*: not found",
)

# (required, allowed) tool-input keys. CC 2.1.300 validates updatedInput: unknown
# keys are dropped and invalid input denies the call, so a mutator that drops a
# required key or invents one breaks every call it rewrites.
TOOL_INPUT_KEYS: dict[str, tuple[set[str], set[str]]] = {
    "Bash": ({"command"}, {"command", "timeout", "description", "run_in_background", "dangerouslyDisableSandbox"}),
    "Agent": (
        {"description", "prompt"},
        {"description", "prompt", "subagent_type", "model", "isolation", "name", "mode", "team_name", "effort"},
    ),
}

# Inputs that make each known mutator rewrite (positive control: a case that no
# hook rewrites fails, so a mutator that silently stops firing is caught too).
REWRITE_CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("git-noext", "Bash", {"command": "git diff HEAD", "description": "smoke"}),
    ("pyunbuffered", "Bash", {"command": "uv run python3 x.py > x.log 2>&1", "run_in_background": True}),
    ("uv-python", "Bash", {"command": "python3 -c 'print(1)'", "timeout": 60000}),
    ("bare-modal", "Bash", {"command": "modal app list"}),
    ("subagent-model", "Agent", {"description": "smoke", "prompt": "Reply OK.", "subagent_type": "general-purpose"}),
]

# Hooks run under the CC process PATH; this is its brew-first core. 2026-10-13:
# the python@3.14 upgrade left no unversioned /opt/homebrew/bin/python3, so every
# `python3` hook silently ran Apple's 3.9.6 (TypeError in live-batch-edit-guard).
CLEAN_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
MIN_HOOK_PYTHON = (3, 10)
LAUNCHERS = {"bash", "sh", "zsh", "python", "python3", "node", "uv", "uvx", "exec", "env"}


@dataclass
class SmokeResult:
    source: str
    event: str
    matcher: str
    command: str
    returncode: int
    status: str  # pass | intentional_block | async_timeout | leak (report-only) | fail
    problem: str | None = None
    stdout: str = ""
    stderr: str = ""
    rewrote: bool = False


def check_updated_input(tool_name: str, stdout: str) -> tuple[bool, str | None]:
    """(rewrote, problem) for a PreToolUse stdout carrying updatedInput."""
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return False, None
    hso = parsed.get("hookSpecificOutput") if isinstance(parsed, dict) else None
    if not isinstance(hso, dict) or "updatedInput" not in hso:
        return False, None
    updated = hso["updatedInput"]
    if not isinstance(updated, dict):
        return True, "updatedInput is not an object"
    if tool_name not in TOOL_INPUT_KEYS:
        return True, None
    required, allowed = TOOL_INPUT_KEYS[tool_name]
    problems = []
    if extra := sorted(set(updated) - allowed):
        problems.append(f"unknown {tool_name} keys {extra}")
    if missing := sorted(required - set(updated)):
        problems.append(f"drops required {tool_name} keys {missing}")
    return True, ("updatedInput " + "; ".join(problems)) if problems else None


def relative_script(command: str) -> str | None:
    """First cwd-relative script token in a hook command, else None.

    Walks each shell segment past VAR=value prefixes and launchers (bash, uv run
    python3, ...) to the token that names the script. Bare names are PATH lookups;
    absolute, ~ and $VAR-anchored paths are fine.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    at_start = True
    prev = ""
    for tok in tokens:
        if prev == "cd" and tok.startswith(("/", "~", "$")):
            return None  # later relative paths resolve against an anchored cwd
        prev = tok
        if tok and set(tok) <= set(";&|()"):
            at_start = True
            continue
        if not at_start:
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok) or tok.startswith("-") or tok in LAUNCHERS or tok == "run":
            continue
        at_start = False
        if "/" in tok and not tok.startswith(("/", "~", "$")):
            return tok
    return None


def lint_relative_paths(files: list[Path]) -> list[SmokeResult]:
    out = []
    for path in files:
        try:
            refs = load_hooks(path)
        except (OSError, json.JSONDecodeError):
            continue
        for ref in refs:
            if tok := relative_script(ref.command):
                out.append(SmokeResult(
                    ref.source, ref.event, ref.matcher, ref.command, 0, "fail",
                    f"cwd-relative hook script {tok!r}: dead from subdirectories/worktrees — anchor it with \"$CLAUDE_PROJECT_DIR\"/",
                ))
    return out


def interpreter_check() -> SmokeResult:
    probe = "import sys; print('%d.%d' % sys.version_info[:2])"
    proc = subprocess.run(["/usr/bin/env", "-i", f"PATH={CLEAN_PATH}", "python3", "-c", probe],
                          capture_output=True, text=True, timeout=10, check=False)
    found = proc.stdout.strip()
    ok = proc.returncode == 0 and tuple(int(x) for x in found.split(".")) >= MIN_HOOK_PYTHON
    return SmokeResult(
        "(hook env)", "(interpreter)", "<all>", f"PATH={CLEAN_PATH} python3", proc.returncode,
        "pass" if ok else "fail",
        None if ok else f"hook-env python3 is {found or 'missing'}; need >= {'.'.join(map(str, MIN_HOOK_PYTHON))} "
        "(check `brew link` / /opt/homebrew/bin/python3)",
        stdout=found, stderr=proc.stderr.strip()[:300],
    )


def hook_root(source: str, tmp: Path) -> Path:
    """Project root for a settings file; temp sandbox for global hooks."""
    path = Path(source)
    if path.parent.name == ".claude" and path.parent.parent != HOME:
        return path.parent.parent
    return tmp


def claude_payload(event: str, hook: HookRef, tmp: Path) -> dict[str, Any]:
    """Canned payload for one event; extends codex smoke_payload's coverage."""
    tool_name = select_tool_name(event, hook.matcher) if hook.matcher != "<all>" else "Bash"
    temp_file = tmp / "smoke.md"
    transcript = tmp / "transcript.jsonl"

    if event in {"PreCompact", "PostCompact"}:
        return {
            "hook_event_name": event,
            "session_id": SESSION_ID,
            "transcript_path": str(transcript),
            "trigger": "manual",
            "cwd": str(tmp),
        }
    if event in {"PermissionRequest", "PermissionDenied"}:
        return {
            "hook_event_name": event,
            "session_id": SESSION_ID,
            "tool_name": "Bash",
            "tool_input": {"command": "printf 'hooks smoke\\n'"},
            "cwd": str(tmp),
        }
    if event == "SessionEnd":
        return {"hook_event_name": event, "session_id": SESSION_ID, "reason": "other", "cwd": str(tmp)}
    if event in {"StopFailure", "PostToolUseFailure"}:
        return {
            "hook_event_name": event,
            "session_id": SESSION_ID,
            "error": "hooks smoke synthetic failure",
            "tool_name": "Bash",
            "tool_input": {"command": "true"},
            "cwd": str(tmp),
        }
    if event == "TaskCreated":
        return {"hook_event_name": event, "session_id": SESSION_ID, "task_id": "1", "subject": "hooks smoke"}

    payload = smoke_payload(event, tool_name, temp_file)
    payload["cwd"] = str(tmp)
    payload["transcript_path"] = str(transcript)
    return payload


def seed_tmp_repo(tmp: Path) -> None:
    # Sandboxed HOME so hooks that append to ~/.claude state files
    # (compact-log.jsonl, hook-trigger logs, session ledgers) write here,
    # not into production telemetry. Discovered the hard way: the first
    # live run added 4 event:null rows to the real compact-log.jsonl.
    home = tmp / "home"
    (home / ".claude").mkdir(parents=True)
    # Hooks that resolve tools under ~/.local/bin (bare-modal-guard) must see the real ones.
    real_bin = HOME / ".local" / "bin"
    if real_bin.is_dir():
        (home / ".local").mkdir()
        (home / ".local" / "bin").symlink_to(real_bin)
    (tmp / "smoke.md").write_text("hooks smoke\n")
    # Minimal plausible transcript for hooks that read transcript_path.
    lines = [
        {"type": "user", "message": {"role": "user", "content": "hooks smoke probe"}},
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "Smoke reply — no real work."}]},
        },
    ]
    (tmp / "transcript.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=False, capture_output=True)
    subprocess.run(["git", "add", "smoke.md"], cwd=tmp, check=False, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=smoke@local", "-c", "user.name=smoke", "commit", "-qm", "smoke seed"],
        cwd=tmp,
        check=False,
        capture_output=True,
    )


def run_hook(
    hook: HookRef, tmp: Path, timeout: float, async_hooks: set[tuple[str, str]],
    payload: dict[str, Any] | None = None,
) -> SmokeResult:
    # payload cwd stays at the sandbox repo so mutating hooks (auto-commit,
    # checkpoint writers) act on the throwaway clone; CLAUDE_PROJECT_DIR and
    # the shell cwd are the real project root so $CLAUDE_PROJECT_DIR/...
    # hook scripts resolve as in production.
    root = hook_root(hook.source, tmp)
    payload = payload or claude_payload(hook.event, hook, tmp)
    payload_text = json.dumps(payload)
    # HOME is sandboxed below, so pre-expand `~/` AND `$HOME/` to the real home —
    # in production these resolve against the user's home, and the sandbox must not
    # change which script gets executed (a $HOME/ command would otherwise point at
    # the empty sandbox home → spurious "no such file" failure).
    command = hook.command.replace("~/", f"{HOME}/").replace("$HOME/", f"{HOME}/").replace("${HOME}/", f"{HOME}/")
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(root),
            "CLAUDE_SESSION_ID": SESSION_ID,
            "CODEX_HOOK_COMPAT_SMOKE": "1",  # existing opt-out convention in hooks
            "CLAUDE_HOOK_SMOKE": "1",
            "SPIN_STATE_OVERRIDE": str(tmp / "spinning-state"),
            # Sandbox $HOME-relative state writes; keep tool caches real so
            # uvx/uv-run hooks don't re-resolve environments per smoke run.
            "HOME": str(tmp / "home"),
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(HOME / ".cache" / "uv")),
            "UV_PYTHON_INSTALL_DIR": os.environ.get(
                "UV_PYTHON_INSTALL_DIR", str(HOME / ".local" / "share" / "uv" / "python")
            ),
        }
    )
    try:
        proc = subprocess.run(
            command,
            input=payload_text,
            text=True,
            capture_output=True,
            shell=True,
            cwd=root,
            env=env,
            timeout=timeout,
        )
        returncode, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        is_async = (hook.event, hook.command) in async_hooks
        return SmokeResult(
            hook.source, hook.event, hook.matcher, hook.command, 124,
            "async_timeout" if is_async else "fail",
            f"timeout after {timeout:g}s" + (" (async hook — not a production hazard)" if is_async else ""),
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
        )

    status, problem = "pass", None
    death = DEATH_RE.search(stderr or "")
    if death:
        status = "fail"
        problem = f"interpreter death on stderr: {death.group(0)!r}"
    if stdout.lstrip().startswith("{"):
        try:
            parsed = json.loads(stdout)
            if not isinstance(parsed, dict):
                status, problem = "fail", "JSON stdout is not an object"
        except json.JSONDecodeError:
            status, problem = "fail", "stdout starts with '{' but is not valid JSON"
    rewrote = False
    if hook.event == "PreToolUse":
        rewrote, input_problem = check_updated_input(payload.get("tool_name", ""), stdout)
        if input_problem:
            status, problem = "fail", input_problem

    if returncode == 0:
        pass
    elif returncode == 2 and BLOCK_RE.search(stdout + "\n" + stderr):
        if status == "pass":
            status = "intentional_block"
    else:
        exit_problem = f"unexpected exit {returncode} on benign smoke input"
        problem = f"{problem}; {exit_problem}" if problem else exit_problem
        status = "fail"

    return SmokeResult(
        hook.source, hook.event, hook.matcher, hook.command,
        returncode, status, problem, stdout.strip()[:500], stderr.strip()[:500], rewrote,
    )


def case_payload(tool_name: str, tool_input: dict[str, Any], tmp: Path) -> dict[str, Any]:
    return {
        "hook_event_name": "PreToolUse", "session_id": SESSION_ID, "tool_name": tool_name,
        "tool_input": tool_input, "cwd": str(tmp), "transcript_path": str(tmp / "transcript.jsonl"),
    }


def run_rewrite_cases(
    hooks: list[HookRef], tmp: Path, timeout: float, async_hooks: set[tuple[str, str]], jobs: int,
    require_rewrites: bool,
) -> list[SmokeResult]:
    """Drive every PreToolUse hook with each REWRITE_CASE; with require_rewrites
    (the full production set), fail cases nobody rewrites."""
    pre = [h for h in hooks if h.event == "PreToolUse"]
    work = [
        (name, h, case_payload(tool, tool_input, tmp))
        for name, tool, tool_input in REWRITE_CASES
        for h in pre
        if tool in matcher_tools(h.matcher)
    ]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        ran = list(pool.map(lambda w: (w[0], run_hook(w[1], tmp, timeout, async_hooks, w[2])), work))
    results = [r for _, r in ran]
    for name, tool, tool_input in REWRITE_CASES if require_rewrites else []:
        if not any(r.rewrote for n, r in ran if n == name):
            results.append(SmokeResult(
                "(rewrite cases)", "PreToolUse", tool, json.dumps(tool_input), 0, "fail",
                f"positive control {name!r}: no registered hook rewrote this input",
            ))
    return results


def collect(
    repos: list[str], project_only: bool, explicit: Path | None = None
) -> tuple[list[HookRef], set[tuple[str, str]]]:
    files: list[Path] = []
    if explicit is not None:
        files.append(explicit)
    if not project_only and GLOBAL_SETTINGS.exists():
        files.append(GLOBAL_SETTINGS)
    for repo in repos:
        for name in ("settings.json", "settings.local.json"):
            p = HOME / "Projects" / repo / ".claude" / name
            if p.exists():
                files.append(p)
    refs: list[HookRef] = []
    async_hooks: set[tuple[str, str]] = set()
    for path in files:
        refs.extend(load_hooks(path))
        data = json.loads(path.read_text())
        for event, groups in data.get("hooks", {}).items():
            for group in groups:
                for hook in group.get("hooks", []):
                    if hook.get("async") and hook.get("command"):
                        async_hooks.add((event, hook["command"]))
    return refs, async_hooks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke every registered Claude hook with canned event JSON.")
    parser.add_argument("--repo", action="append", help="repo(s) whose .claude/settings.json to include; default: all mirrored + skills consumers")
    parser.add_argument("--settings-file", type=Path, help="smoke an explicit settings.json instead of the default set")
    parser.add_argument("--project-only", action="store_true", help="skip ~/.claude/settings.json")
    parser.add_argument("--event", action="append", help="limit to hook event(s)")
    parser.add_argument("--timeout", type=float, default=15.0, help="per-hook timeout in seconds")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.settings_file:
        hooks, async_hooks = collect([], True, explicit=args.settings_file)
    else:
        repos = args.repo or list(MIRRORED_REPOS) + ["evals", "hutter"]
        hooks, async_hooks = collect(repos, args.project_only)
    if args.event:
        hooks = [h for h in hooks if h.event in set(args.event)]
    if not hooks:
        print("no hooks found")
        return 1

    # Production-write guard: per-repo hooks run with cwd + CLAUDE_PROJECT_DIR at
    # the REAL repo root (so $CLAUDE_PROJECT_DIR/... scripts resolve), so an
    # unguarded hook that writes there or runs git in cwd can mutate production —
    # and the maintain loop re-runs this every tick. Sandboxing HOME covers
    # ~/.claude but NOT $CLAUDE_PROJECT_DIR writes. Snapshot each real root's git
    # state before/after and fail loudly if the smoke dirtied a real repo.
    def porcelain(root: Path) -> set[str] | None:
        """Dirty PATHS in the working tree, or None if git failed/timed out.

        Paths, not raw porcelain lines: a pre-existing dirty file whose index
        state shifts during the smoke window (' M' -> 'MM', unstaged -> staged
        by a concurrent session) must not read as a new write. And None — not
        an empty set — on failure: a timed-out BEFORE snapshot returning set()
        manufactures a 'leak' out of every pre-existing dirty file (false
        positive observed 2026-06-12: a live phenome session's +176-line WIP
        on canonicalize.py flagged as a hook write).
        """
        try:
            proc = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                                  capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                return None
            paths = set()
            for line in proc.stdout.splitlines():
                # porcelain v1: XY <path>, renames as XY <old> -> <new>
                path = line[3:]
                paths.add(path.split(" -> ", 1)[-1] if " -> " in path else path)
            return paths
        except Exception:
            return None

    with tempfile.TemporaryDirectory(prefix="hooks-smoke-") as tmpdir:
        tmp = Path(tmpdir)
        seed_tmp_repo(tmp)
        # hook_root returns the real repo root for per-repo hooks, tmp for global ones.
        real_roots = sorted({hook_root(h.source, tmp) for h in hooks if hook_root(h.source, tmp) != tmp})
        before = {r: porcelain(r) for r in real_roots}
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(lambda h: run_hook(h, tmp, args.timeout, async_hooks), hooks))
        full_set = not (args.settings_file or args.repo or args.project_only or args.event)
        results.extend(run_rewrite_cases(hooks, tmp, args.timeout, async_hooks, args.jobs, full_set))
        results.append(interpreter_check())
        lint_files = [args.settings_file] if args.settings_file else [
            GLOBAL_SETTINGS, *sorted((HOME / "Projects").glob("*/.claude/settings*.json"))
        ]
        results.extend(lint_relative_paths([p for p in lint_files if p.exists()]))
        for r in real_roots:
            # Only NEW paths (in after, not before) are smoke-caused; pre-existing
            # dirty/untracked files are in both and must not be flagged (else the guard
            # cries wolf every run and gets ignored — the habituation failure).
            pre, after = before[r], porcelain(r)
            if pre is None or after is None:
                continue  # snapshot failed — can't attribute, don't fabricate a leak
            new_lines = sorted(after - pre)
            if new_lines:
                # Report-only (status 'leak', non-failing) for now — measure before
                # enforcing. Failing the build on every benign write would keep
                # `just smoke` permanently red; auto-revert is unsafe with other agents
                # active. Surfaces the leak so the offending hook gets a
                # CLAUDE_HOOK_SMOKE guard; promote to 'fail' once known leakers are fixed.
                results.append(SmokeResult(
                    source=str(r / ".claude/settings.json"), event="(post-run guard)", matcher="<all>",
                    command="git status diff", returncode=0, status="leak",
                    problem=f"a hook wrote to the real repo {r.name} during smoke (sandbox leak — $CLAUDE_PROJECT_DIR write or git-in-cwd). Add CLAUDE_HOOK_SMOKE guard to the offending hook. New changes:\n" + "\n".join(new_lines[:10]),
                ))

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        counts: dict[str, int] = {}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1
        print("hooks smoke: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        for r in results:
            if r.status == "leak":
                print(f"\n[LEAK] {r.source}\n  {r.problem}")
                continue
            if r.status != "fail":
                continue
            print(f"\n[FAIL] {r.event} {r.matcher}  (exit {r.returncode})")
            print(f"  source: {r.source}")
            print(f"  command: {r.command[:200]}")
            print(f"  problem: {r.problem}")
            if r.stderr:
                print(f"  stderr: {r.stderr[:300]}")
            if r.stdout:
                print(f"  stdout: {r.stdout[:200]}")
    return 1 if any(r.status == "fail" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
