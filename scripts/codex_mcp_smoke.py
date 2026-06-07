#!/usr/bin/env python3
"""Smoke-test project-scoped Codex stdio MCP deltas.

`codex mcp list` proves config visibility. This proves the generated
`.codex/config.toml` stdio servers actually start and respond to
`initialize` + `tools/list`.
"""
from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.project_registry import MIRRORED_REPOS  # noqa: E402

HOME = Path.home()
PROJECTS = HOME / "Projects"
REPOS = MIRRORED_REPOS


@dataclass
class ServerResult:
    repo: str
    server: str
    status: str
    tools: int = 0
    problem: str = ""
    stderr: str = ""


def load_project_servers(repo: str) -> tuple[Path, dict[str, dict[str, Any]]]:
    path = PROJECTS / repo / ".codex" / "config.toml"
    if not path.exists():
        return path, {}
    with open(path, "rb") as f:
        return path, tomllib.load(f).get("mcp_servers", {})


def _env_var_binding(item: str | dict[str, str]) -> tuple[str, str]:
    if isinstance(item, str):
        return item, item
    name = item["name"]
    return name, item.get("source", name)


def server_env(spec: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    for item in spec.get("env_vars") or []:
        name, source = _env_var_binding(item)
        if source in os.environ:
            env[name] = os.environ[source]
    env.update({str(k): str(v) for k, v in (spec.get("env") or {}).items()})
    return env


def missing_env_vars(spec: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for item in spec.get("env_vars") or []:
        _, source = _env_var_binding(item)
        if not os.environ.get(source):
            missing.append(source)
    return missing


def _read_response(
    proc: subprocess.Popen[str],
    selector: selectors.BaseSelector,
    expected_id: int,
    deadline: float,
) -> dict[str, Any]:
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with code {proc.returncode}")
        events = selector.select(timeout=max(0.05, min(0.5, deadline - time.monotonic())))
        for key, _ in events:
            line = key.fileobj.readline()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"non-JSON stdout line: {line[:160]!r}") from exc
            if msg.get("id") == expected_id:
                return msg
    raise TimeoutError(f"timed out waiting for JSON-RPC id={expected_id}")


def probe_stdio(repo: str, server: str, spec: dict[str, Any], timeout: float) -> ServerResult:
    cmd = [spec["command"], *spec.get("args", [])]
    env = server_env(spec)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(PROJECTS / repo),
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    result: ServerResult
    try:
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "codex-mcp-smoke", "version": "1"},
            },
        }
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        init_response = _read_response(proc, selector, 1, deadline)
        if "error" in init_response:
            raise RuntimeError(f"initialize error: {init_response['error']}")

        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
        proc.stdin.flush()
        tools_response = _read_response(proc, selector, 2, deadline)
        if "error" in tools_response:
            raise RuntimeError(f"tools/list error: {tools_response['error']}")
        tools = tools_response.get("result", {}).get("tools", [])
        result = ServerResult(repo, server, "pass", tools=len(tools))
    except Exception as exc:  # noqa: BLE001 - report all startup failures uniformly
        result = ServerResult(repo, server, "fail", problem=str(exc))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        stderr = ""
        if proc.stderr is not None:
            try:
                stderr = proc.stderr.read()
            except Exception:
                stderr = ""
        selector.close()
    result.stderr = stderr.strip()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test project Codex stdio MCP deltas.")
    parser.add_argument("--repo", action="append", choices=REPOS, help="repo(s) to check; default all")
    parser.add_argument("--server", action="append", help="server id(s) to check; default all stdio deltas")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-server timeout in seconds")
    args = parser.parse_args(argv)

    wanted_repos = args.repo or list(REPOS)
    wanted_servers = set(args.server or [])
    results: list[ServerResult] = []
    skipped: list[tuple[str, str, str]] = []
    for repo in wanted_repos:
        config_path, servers = load_project_servers(repo)
        if not servers:
            results.append(ServerResult(repo, "<config>", "fail", problem=f"missing or empty {config_path}"))
            continue
        for sid, spec in sorted(servers.items()):
            if wanted_servers and sid not in wanted_servers:
                continue
            if "url" in spec:
                skipped.append((repo, sid, "url server"))
                continue
            missing = missing_env_vars(spec)
            if missing and not wanted_servers:
                skipped.append((repo, sid, "missing env_vars: " + ", ".join(sorted(missing))))
                continue
            if missing:
                results.append(ServerResult(repo, sid, "fail", problem="missing env_vars: " + ", ".join(sorted(missing))))
                continue
            results.append(probe_stdio(repo, sid, spec, args.timeout))

    for repo, sid, reason in skipped:
        print(f"skip {repo}:{sid} ({reason})")
    for result in results:
        if result.status == "pass":
            print(f"pass {result.repo}:{result.server} tools={result.tools}")
        else:
            print(f"fail {result.repo}:{result.server} {result.problem}")
            if result.stderr:
                print(f"stderr: {result.stderr[:500]}")
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
