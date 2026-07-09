#!/usr/bin/env python3
"""Read-only scout dispatch backends — single owner for cursor/codex/claude audit scouts.

Consumers: debug_scout.py, debug_until_dry.py. Both need a WORKSPACE-GROUNDED
agent (the scout greps/reads the target repo itself), so this dispatches the
agentic CLIs directly — not llmx chat (context-piping transport; right for
code-review-scout's diff-as-context, wrong for repo-roaming scouts).

Backends (read-only enforcement is structural, not prompt-trusted):
  cursor — `agent` CLI ask mode (read-only by mode), composer-2.5 default;
           override with --scout-model (e.g. grok-4.5-xhigh for Grok 4.5 niche lens —
           always pass an effort slug; bare grok-4.5 → fast-xhigh)
  codex  — `codex exec -s read-only` (sandbox), config-default model (gpt-5.5),
           effort defaults to `medium` (user-config xhigh blows scout timeouts)
  claude — `claude -p` headless: Write/Edit/arbitrary-Bash auto-DENIED in -p
           (no interactive prompt), only a curated read-only Bash allowlist is
           granted. Key-stripped env = OAuth subscription, never API billing
           (llmx-guide bare-lean contract). `--strict-mcp-config` drops MCPs.

Token capture: each backend parses its CLI's usage report (codex `--json`
turn.completed events split out reasoning tokens; cursor/claude json usage has
input/output only). Subscription lanes are $0 but NOT cost-free — tokens are
reported per eval-token-costs rule. Zeros mean "CLI reported nothing".
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

AGENT = Path.home() / ".local/bin/agent"

# per-backend default model ("" = the CLI's own config default)
DEFAULT_MODEL = {"cursor": "composer-2.5", "codex": "", "claude": "sonnet"}
# codex/claude scout-lane effort. Codex user-config default is xhigh (30+ min) —
# a 600s scout needs a cheaper lane. Cursor's agent CLI has no effort knob.
DEFAULT_EFFORT = "medium"

# claude -p read-only probe allowlist: headless mode auto-denies every tool that
# would need a permission prompt, so Write/Edit/other-Bash are structurally off;
# this grants only the cheap read-only probes the scout prompt asks for.
# The `git --no-pager` variants are load-bearing: the harness rewrites `git log`
# to `git --no-pager log --no-ext-diff …`, which misses a bare `Bash(git log:*)`
# prefix pattern (verified via permission_denials in stream-json, 2026-07-03).
CLAUDE_READONLY_BASH = (
    [f"Bash(git {sub}:*)" for sub in ("log", "diff", "show", "blame")]
    + [f"Bash(git --no-pager {sub}:*)" for sub in ("log", "diff", "show", "blame")]
    + [
        "Bash(rg:*)",
        "Bash(grep:*)",
        "Bash(ls:*)",
        "Bash(wc:*)",
    ]
)


@dataclass
class ScoutReply:
    ok: bool
    body: str
    in_tok: int = 0
    out_tok: int = 0  # completion/output tokens (reasoning excluded where split)
    reason_tok: int = 0  # reasoning/thinking tokens where the CLI splits them
    cached_tok: int = 0

    @property
    def timed_out(self) -> bool:
        return self.body == "(timeout)"


def parse_backend_spec(spec: str) -> list[str]:
    """'cursor,codex' → ['cursor', 'codex']; validates names."""
    backends = [b.strip() for b in spec.split(",") if b.strip()]
    unknown = [b for b in backends if b not in DEFAULT_MODEL]
    if unknown or not backends:
        raise ValueError(
            f"unknown scout backend(s): {unknown or spec!r} (valid: {', '.join(DEFAULT_MODEL)})"
        )
    return backends


def _sub_env() -> dict[str, str]:
    """Strip API keys + nested-session markers → subscription auth, clean session."""
    drop = {"ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "CLAUDECODE", "CLAUDE_SESSION_ID"}
    return {k: v for k, v in os.environ.items() if k not in drop}


def _cursor_ask(repo: Path, prompt: str, timeout: int, model: str) -> ScoutReply:
    if not AGENT.is_file():
        return ScoutReply(False, "agent CLI not found (~/.local/bin/agent)")
    cmd = [
        str(AGENT), "-p", "--trust", "--mode", "ask",
        "--model", model or DEFAULT_MODEL["cursor"],
        "--workspace", str(repo), "--output-format", "json",
        prompt,
    ]  # fmt: skip
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ScoutReply(False, "(timeout)")
    try:
        d = json.loads(r.stdout)
        u = d.get("usage", {})
        return ScoutReply(
            ok=r.returncode == 0 and not d.get("is_error", False),
            body=(d.get("result") or "").strip() or "(empty)",
            in_tok=u.get("inputTokens", 0),
            out_tok=u.get("outputTokens", 0),
            cached_tok=u.get("cacheReadTokens", 0),
        )
    except (json.JSONDecodeError, AttributeError):
        # json shape drift — keep the raw text usable, tokens unknown
        body = r.stdout.strip() or r.stderr.strip() or "(empty)"
        return ScoutReply(r.returncode == 0, body)


def _codex_ask(
    repo: Path, prompt: str, timeout: int, model: str, effort: str
) -> ScoutReply:
    with tempfile.NamedTemporaryFile(mode="r", suffix=".md", delete=False) as tf:
        out_path = Path(tf.name)
    cmd = [
        "codex", "exec",
        "-s", "read-only",  # sandbox enforces the AUDIT-ONLY contract structurally
        "-C", str(repo),
        "--skip-git-repo-check",
        "--ephemeral",  # scouts are fire-and-forget; don't litter ~/.codex/sessions
        "--color", "never",
        "--json",  # JSONL events on stdout → usage from turn.completed
        "-c", f'model_reasoning_effort="{effort or DEFAULT_EFFORT}"',
        "-o", str(out_path),
    ]  # fmt: skip
    if model:
        cmd += ["-m", model]
    cmd.append(prompt)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        out_path.unlink(missing_ok=True)
        return ScoutReply(False, "(timeout)")
    reply = ScoutReply(ok=r.returncode == 0, body="")
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "turn.completed":
            u = ev.get("usage", {})
            reply.in_tok += u.get("input_tokens", 0)
            reply.out_tok += u.get("output_tokens", 0)
            reply.reason_tok += u.get("reasoning_output_tokens", 0)
            reply.cached_tok += u.get("cached_input_tokens", 0)
    body = out_path.read_text().strip() if out_path.is_file() else ""
    out_path.unlink(missing_ok=True)
    if not body:  # -o unwritten (crash/auth failure) — surface stderr, not event noise
        return ScoutReply(False, (r.stderr.strip() or "(empty)")[-2000:])
    reply.body = body
    return reply


def _claude_ask(
    repo: Path, prompt: str, timeout: int, model: str, effort: str
) -> ScoutReply:
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", model or DEFAULT_MODEL["claude"],
        "--effort", effort or DEFAULT_EFFORT,
        "--strict-mcp-config",  # drop project MCPs — scouts probe the repo, not tools
        "--allowedTools", *CLAUDE_READONLY_BASH,
    ]  # fmt: skip
    try:
        # prompt via stdin: --allowedTools is variadic and would swallow a trailing arg
        r = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            timeout=timeout, cwd=repo, env=_sub_env(),
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return ScoutReply(False, "(timeout)")
    try:
        d = json.loads(r.stdout)
        u = d.get("usage", {})
        return ScoutReply(
            ok=r.returncode == 0 and not d.get("is_error", False),
            body=(d.get("result") or "").strip() or "(empty)",
            in_tok=u.get("input_tokens", 0),
            out_tok=u.get("output_tokens", 0),
            cached_tok=u.get("cache_read_input_tokens", 0),
        )
    except (json.JSONDecodeError, AttributeError):
        body = r.stdout.strip() or r.stderr.strip() or "(empty)"
        return ScoutReply(r.returncode == 0, body)


def scout_ask(
    backend: str,
    repo: Path,
    prompt: str,
    *,
    timeout: int,
    model: str = "",
    effort: str = "",
    dry_run: bool = False,
) -> ScoutReply:
    """Dispatch one read-only scout; returns ScoutReply(ok, final_message, tokens)."""
    if dry_run:
        return ScoutReply(True, f"## NO_FINDINGS\n(dry-run — no {backend} call made)")
    if backend == "cursor":
        return _cursor_ask(repo, prompt, timeout, model)
    if backend == "codex":
        return _codex_ask(repo, prompt, timeout, model, effort)
    if backend == "claude":
        return _claude_ask(repo, prompt, timeout, model, effort)
    raise ValueError(f"unknown scout backend: {backend}")
