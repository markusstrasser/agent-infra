#!/usr/bin/env python3
"""Read-only scout dispatch backends — single owner for cursor/codex audit scouts.

Consumers: debug_scout.py, debug_until_dry.py. Both need a WORKSPACE-GROUNDED
agent (the scout greps/reads the target repo itself), so this dispatches the
agentic CLIs directly — not llmx chat (context-piping transport; right for
code-review-scout's diff-as-context, wrong for repo-roaming scouts).

Backends:
  cursor — `agent` CLI, ask mode (read-only by mode), composer-2.5 default
  codex  — `codex exec -s read-only` (read-only by sandbox), config-default
           model (gpt-5.5), effort forced to `medium` unless overridden —
           the user-config default (xhigh) blows the scout timeout

Every backend returns (ok, final_message_text). Timeouts return (False, "(timeout)").
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

AGENT = Path.home() / ".local/bin/agent"

# per-backend default model ("" = the CLI's own config default)
DEFAULT_MODEL = {"cursor": "composer-2.5", "codex": ""}
# codex-only: scout-lane effort. User config default is xhigh (30+ min) — a
# 600s scout needs a cheaper lane. Cursor's agent CLI has no effort knob.
DEFAULT_CODEX_EFFORT = "medium"


def parse_backend_spec(spec: str) -> list[str]:
    """'cursor,codex' → ['cursor', 'codex']; validates names."""
    backends = [b.strip() for b in spec.split(",") if b.strip()]
    unknown = [b for b in backends if b not in DEFAULT_MODEL]
    if unknown or not backends:
        raise ValueError(
            f"unknown scout backend(s): {unknown or spec!r} (valid: cursor, codex)"
        )
    return backends


def _cursor_ask(repo: Path, prompt: str, timeout: int, model: str) -> tuple[bool, str]:
    if not AGENT.is_file():
        return False, "agent CLI not found (~/.local/bin/agent)"
    cmd = [
        str(AGENT),
        "-p",
        "--trust",
        "--mode",
        "ask",
        "--model",
        model or DEFAULT_MODEL["cursor"],
        "--workspace",
        str(repo),
        "--output-format",
        "text",
        prompt,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "(timeout)"
    return r.returncode == 0, (r.stdout.strip() or r.stderr.strip() or "(empty)")


def _codex_ask(
    repo: Path, prompt: str, timeout: int, model: str, effort: str
) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(mode="r", suffix=".md", delete=False) as tf:
        out_path = Path(tf.name)
    cmd = [
        "codex",
        "exec",
        "-s",
        "read-only",  # sandbox enforces the AUDIT-ONLY contract structurally
        "-C",
        str(repo),
        "--skip-git-repo-check",
        "--ephemeral",  # scouts are fire-and-forget; don't litter ~/.codex/sessions
        "--color",
        "never",
        "-c",
        f'model_reasoning_effort="{effort or DEFAULT_CODEX_EFFORT}"',
        "-o",
        str(out_path),
    ]
    if model:
        cmd += ["-m", model]
    cmd.append(prompt)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        out_path.unlink(missing_ok=True)
        return False, "(timeout)"
    body = out_path.read_text().strip() if out_path.is_file() else ""
    out_path.unlink(missing_ok=True)
    if (
        not body
    ):  # -o unwritten (crash/auth failure) — surface stderr, not stdout event noise
        return False, (r.stderr.strip() or r.stdout.strip() or "(empty)")[-2000:]
    return r.returncode == 0, body


def scout_ask(
    backend: str,
    repo: Path,
    prompt: str,
    *,
    timeout: int,
    model: str = "",
    effort: str = "",
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Dispatch one read-only scout; returns (ok, final_message_text)."""
    if dry_run:
        return True, f"## NO_FINDINGS\n(dry-run — no {backend} call made)"
    if backend == "cursor":
        return _cursor_ask(repo, prompt, timeout, model)
    if backend == "codex":
        return _codex_ask(repo, prompt, timeout, model, effort)
    raise ValueError(f"unknown scout backend: {backend}")
