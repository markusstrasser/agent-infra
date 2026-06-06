#!/usr/bin/env python3
"""Codex hook compatibility checker.

Runs generated `.codex/hooks.json` command hooks with benign Codex-shaped
payloads and flags the two failure classes that Claude-derived hooks commonly
hide:

- non-empty stdout that is not JSON on Codex JSON-parsed hook events
- accidental non-zero exits such as 1 or 64 on normal smoke inputs

Exit 2 is preserved as an intentional block only when the hook emits a clear
block/deny message. Everything else is reported as a compatibility failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HOME = Path.home()
PROJECTS = HOME / "Projects"
GLOBAL_CODEX_HOOKS = HOME / ".codex" / "hooks.json"
REPOS = ("agent-infra", "intel", "genomics", "phenome")

JSON_STDOUT_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostCompact",
    "Stop",
    "SubagentStart",
    "SubagentStop",
}

BLOCK_RE = re.compile(r"\b(BLOCK(?:ED)?|DENY|DENIED|FORBID|FORBIDDEN|ABORT|STOP)\b", re.I)
DEFAULT_EVENTS = tuple(sorted(JSON_STDOUT_EVENTS))


@dataclass
class HookRef:
    source: str
    event: str
    matcher: str
    index: int
    command: str
    status_message: str | None = None


@dataclass
class HookResult:
    repo: str
    source: str
    event: str
    matcher: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    status: str
    problem: str | None = None


def repo_dir(name: str) -> Path:
    return PROJECTS / name


def load_hooks(path: Path) -> list[HookRef]:
    data = json.loads(path.read_text())
    refs: list[HookRef] = []
    for event, groups in data.get("hooks", {}).items():
        for group_index, group in enumerate(groups):
            matcher = group.get("matcher") or "<all>"
            for hook_index, hook in enumerate(group.get("hooks", [])):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command")
                if not command:
                    continue
                refs.append(
                    HookRef(
                        source=str(path),
                        event=event,
                        matcher=matcher,
                        index=(group_index * 1000) + hook_index,
                        command=command,
                        status_message=hook.get("statusMessage"),
                    )
                )
    return refs


def matcher_tools(matcher: str) -> list[str]:
    if matcher in ("", "*", "<all>"):
        return ["Bash"]
    return [part.strip() for part in matcher.split("|") if part.strip()]


def select_tool_name(event: str, matcher: str) -> str:
    tools = matcher_tools(matcher)
    if event in {"SessionStart", "UserPromptSubmit", "Stop", "SubagentStart", "SubagentStop", "PostCompact"}:
        return tools[0]
    for preferred in ("Bash", "Write", "Edit", "Read", "Agent", "WebSearch", "WebFetch"):
        if preferred in tools:
            return preferred
    return tools[0]


def smoke_payload(event: str, tool_name: str, temp_file: Path) -> dict[str, Any]:
    session_id = "codex-hook-compat-smoke"
    if event == "SessionStart":
        return {
            "hook_event_name": event,
            "session_id": session_id,
            "source": "startup",
        }
    if event == "UserPromptSubmit":
        return {"hook_event_name": event, "session_id": session_id, "prompt": "hook compatibility smoke"}
    if event in {"Stop", "SubagentStop"}:
        return {"hook_event_name": event, "session_id": session_id, "stop_hook_active": False}
    if event == "SubagentStart":
        return {"hook_event_name": event, "session_id": session_id, "agent_name": "compat-smoke"}
    if event == "PostCompact":
        return {"hook_event_name": event, "session_id": session_id, "compact_id": "compat-smoke"}

    tool_input: dict[str, Any]
    tool_response: dict[str, Any] = {"output": "codex hook compatibility smoke\n"}
    if tool_name == "Bash":
        tool_input = {"command": "printf 'codex hook compatibility smoke\\n'"}
    elif tool_name in {"Write", "Edit", "MultiEdit"}:
        tool_input = {"file_path": str(temp_file), "content": "codex hook compatibility smoke\n"}
    elif tool_name == "Read":
        tool_input = {"file_path": str(temp_file)}
    elif tool_name == "Agent":
        tool_input = {"description": "compat smoke", "prompt": "No-op compatibility smoke."}
    elif tool_name in {"WebSearch", "WebFetch"}:
        tool_input = {"query": "codex hook compatibility smoke"}
    elif tool_name.startswith("mcp__"):
        tool_input = {"query": "codex hook compatibility smoke"}
    else:
        tool_input = {}

    payload: dict[str, Any] = {
        "hook_event_name": event,
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if event == "PostToolUse":
        payload["tool_response"] = tool_response
    return payload


def timeout_for_hook(hook: HookRef, default_timeout: float) -> float:
    # Hook JSON commonly stores timeout in milliseconds, but generated project
    # hooks are inconsistent. Cap to keep smoke checks interactive.
    return default_timeout


def run_hook(repo: str, root: Path, hook: HookRef, timeout: float) -> HookResult:
    tool_name = select_tool_name(hook.event, hook.matcher)
    with tempfile.TemporaryDirectory(prefix="codex-hook-compat-") as tmp:
        tmp_root = Path(tmp)
        temp_file = Path(tmp) / "smoke.md"
        temp_file.write_text("codex hook compatibility smoke\n", encoding="utf-8")
        payload = smoke_payload(hook.event, tool_name, temp_file)
        if hook.event == "SessionStart":
            payload["cwd"] = str(root)
        payload_text = json.dumps(payload)
        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_PROJECT_DIR": str(root),
                "CLAUDE_TOOL_INPUT": payload_text,
                "CLAUDE_TOOL_NAME": tool_name,
                "CLAUDE_HOOK_EVENT": hook.event,
                "CODEX_HOOK_COMPAT_SMOKE": "1",
                # Stateful loop/circuit hooks must not share production session
                # counters during compatibility smoke tests.
                "SPIN_STATE_OVERRIDE": str(tmp_root / "spinning-state"),
            }
        )
        try:
            proc = subprocess.run(
                hook.command,
                input=payload_text,
                text=True,
                capture_output=True,
                shell=True,
                cwd=root,
                env=env,
                timeout=timeout_for_hook(hook, timeout),
            )
        except subprocess.TimeoutExpired as exc:
            return HookResult(
                repo=repo,
                source=hook.source,
                event=hook.event,
                matcher=hook.matcher,
                command=hook.command,
                returncode=124,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                status="fail",
                problem=f"timeout after {timeout:g}s",
            )

    return classify_result(repo, hook, proc.returncode, proc.stdout, proc.stderr)


def _valid_json_stdout(stdout: str) -> bool:
    if not stdout.strip():
        return True
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict)


def classify_result(repo: str, hook: HookRef, returncode: int, stdout: str, stderr: str) -> HookResult:
    status = "pass"
    problem: str | None = None
    if hook.event in JSON_STDOUT_EVENTS and stdout.strip() and not _valid_json_stdout(stdout):
        status = "fail"
        problem = f"non-empty stdout is not a JSON object for {hook.event}"

    if returncode == 0:
        pass
    elif returncode == 2 and BLOCK_RE.search(stdout + "\n" + stderr):
        if status == "pass":
            status = "intentional_block"
    else:
        status = "fail"
        exit_problem = f"unexpected exit {returncode} on benign smoke input"
        problem = f"{problem}; {exit_problem}" if problem else exit_problem

    return HookResult(
        repo=repo,
        source=hook.source,
        event=hook.event,
        matcher=hook.matcher,
        command=hook.command,
        returncode=returncode,
        stdout=stdout.strip(),
        stderr=stderr.strip(),
        status=status,
        problem=problem,
    )


def collect_hooks(
    repo: str,
    include_global: bool,
    project_only: bool,
    hooks_file: Path | None,
    events: set[str] | None,
) -> tuple[Path, list[HookRef]]:
    root = repo_dir(repo)
    files: list[Path] = []
    if hooks_file is not None:
        files.append(hooks_file)
    else:
        if include_global and not project_only and GLOBAL_CODEX_HOOKS.exists():
            files.append(GLOBAL_CODEX_HOOKS)
        project_hooks = root / ".codex" / "hooks.json"
        if project_hooks.exists():
            files.append(project_hooks)
    refs: list[HookRef] = []
    for path in files:
        refs.extend(load_hooks(path))
    if events:
        refs = [ref for ref in refs if ref.event in events]
    return root, refs


def print_text(results: list[HookResult]) -> None:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print(
        "codex hook compat: "
        + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    )
    for result in results:
        if result.status == "pass":
            continue
        print(f"\n[{result.status}] {result.repo} {result.event} {result.matcher}")
        print(f"source: {result.source}")
        print(f"command: {result.command}")
        print(f"exit: {result.returncode}")
        if result.problem:
            print(f"problem: {result.problem}")
        if result.stdout:
            print(f"stdout: {result.stdout[:500]}")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test Codex hook JSON/exit compatibility.")
    parser.add_argument("--repo", action="append", choices=REPOS, help="repo(s) to check; default all")
    parser.add_argument("--hooks-file", type=Path, help="explicit hooks.json to check")
    parser.add_argument("--project-root", type=Path, help="project root when --hooks-file is used")
    parser.add_argument("--event", action="append", choices=DEFAULT_EVENTS, help="limit to hook event(s)")
    parser.add_argument("--project-only", action="store_true", help="skip ~/.codex/hooks.json")
    parser.add_argument(
        "--include-global",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include ~/.codex/hooks.json with each repo's generated hooks (default: true)",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="per-hook timeout in seconds")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)

    repos = args.repo or list(REPOS)
    events = set(args.event or [])
    results: list[HookResult] = []
    for repo in repos:
        root, hooks = collect_hooks(repo, args.include_global, args.project_only, args.hooks_file, events or None)
        if args.project_root is not None:
            root = args.project_root
        if not root.exists():
            results.append(
                HookResult(repo, str(root), "meta", "<all>", "", 1, "", "", "fail", "repo root missing")
            )
            continue
        for hook in hooks:
            results.append(run_hook(repo, root, hook, args.timeout))

    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print_text(results)
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
