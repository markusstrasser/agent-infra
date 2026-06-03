#!/usr/bin/env python3
"""reflect_capture.py — zero-LLM session-end capture for the learning loop.

Called by the SessionEnd hook with the session's transcript on stdin. Extracts
deterministic correction signals (corrections-mode C1) + SHADOW omission-probe
firings, appends them to ~/.claude/reflect-capture.jsonl. The deep pass
(reflect.py) consumes that file later. No LLM, fail-open, fast.

SHADOW means: omission-probes record firings but emit NO user/agent surface.
The advisory nudge stays off until a probe clears its PPV gate (>=60% on >=30
labeled firings) — see .claude/plans/4d40085a-recursive-session-learning-loop.md.

Project-scoped: omission-probes only run for projects in TESTBED, and only for
rules declared in that project's CLAUDE.md `<!-- omission-rules ... -->` block.

Pure core (extract_signals / extract_corrections / extract_omissions) is
side-effect-free for unit testing; main() does the IO.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

CAPTURE_LOG = Path.home() / ".claude" / "reflect-capture.jsonl"
# Meta-side central probe config, keyed by project. Co-located with the loop
# (which meta owns) so probe declarations don't require editing busy repos.
CENTRAL_RULES = Path(__file__).resolve().parent.parent / "config" / "reflect-omission-rules.json"
# Build in meta, intel is the single test bed (plan scope). Other projects: no-op.
TESTBED = {"intel", "agent-infra"}

# Correction tokens, split by strength so downstream clustering can weight them.
_STRONG = [
    "#f", "you should have", "why didn't you", "why didnt you", "that's not",
    "thats not", "i told you", "not what i", "that is wrong", "you forgot",
]
_MEDIUM = ["wrong", "instead", "don't", "dont", "not that", "incorrect", "no,"]
_WEAK = ["actually", "stop", "no "]
_NEG_RE = re.compile(
    "|".join(re.escape(t) for t in _STRONG + _MEDIUM + _WEAK), re.IGNORECASE
)
_OMISSION_BLOCK = re.compile(r"<!--\s*omission-rules\s*(.*?)-->", re.DOTALL)


# ── transcript parsing ───────────────────────────────────────────────────────
def parse_events(lines: list[str]) -> list[dict]:
    """Normalize a Claude Code transcript (JSONL) into ordered events.

    Each event: {role, texts:[str], tools:[{name,input}], errors:int}. Tool
    results arrive as role='user' with tool_result blocks; we separate genuine
    user text from tool_result envelopes.
    """
    events: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        role = obj.get("type") or obj.get("message", {}).get("role")
        msg = obj.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        ev = {"role": role, "texts": [], "tools": [], "errors": 0, "is_tool_result": False}
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            bt = block.get("type")
            if bt == "text" and block.get("text"):
                ev["texts"].append(block["text"])
            elif bt == "tool_use":
                ev["tools"].append({"name": block.get("name", ""), "input": block.get("input", {})})
            elif bt == "tool_result":
                ev["is_tool_result"] = True
                if block.get("is_error"):
                    ev["errors"] += 1
        events.append(ev)
    return events


# ── correction extraction (corrections-mode C1, zero-LLM) ────────────────────
def _strength(text: str) -> str:
    low = text.lower()
    if any(t in low for t in _STRONG):
        return "strong"
    if any(t in low for t in _MEDIUM):
        return "medium"
    return "weak"


def extract_corrections(events: list[dict]) -> list[dict]:
    """User negations after an assistant action; #f tags; retry runs; fail→user."""
    out: list[dict] = []
    for i, ev in enumerate(events):
        if ev["role"] != "user" or ev["is_tool_result"]:
            continue
        text = " ".join(ev["texts"]).strip()
        if not text:
            continue
        prev = events[i - 1] if i > 0 else None
        after_action = bool(prev and prev["role"] == "assistant" and prev["tools"])
        if "#f" in text.lower():
            out.append({"kind": "correction", "subtype": "f_tag",
                        "strength": "strong", "trigger": text[:280]})
        elif _NEG_RE.search(text) and (after_action or len(text) < 200):
            out.append({"kind": "correction", "subtype": "negation",
                        "strength": _strength(text), "trigger": text[:280]})

    # retry runs: >=3 same-tool calls with differing inputs, uninterrupted by a
    # user text message (FM24 — blind retry). A user message between calls means
    # the user diagnosed, so it is NOT a blind run and breaks it.
    run_name, run_inputs = None, []

    def _flush():
        if run_name and len(run_inputs) >= 3 and len(set(run_inputs)) >= 2:
            out.append({"kind": "correction", "subtype": "retry_run", "strength": "medium",
                        "trigger": f"{run_name} x{len(run_inputs)} varied-input run"})

    for ev in events:
        if ev["role"] == "user" and not ev["is_tool_result"] and ev["texts"]:
            _flush()
            run_name, run_inputs = None, []  # user diagnosis breaks the run
        for t in ev["tools"]:
            if t["name"] == run_name:
                run_inputs.append(json.dumps(t["input"], sort_keys=True, default=str))
            else:
                _flush()
                run_name = t["name"]
                run_inputs = [json.dumps(t["input"], sort_keys=True, default=str)]
    _flush()

    # failure→user: an errored tool_result directly followed by user text
    for i, ev in enumerate(events[:-1]):
        if ev["errors"] and events[i + 1]["role"] == "user" and \
                not events[i + 1]["is_tool_result"] and events[i + 1]["texts"]:
            out.append({"kind": "correction", "subtype": "fail_then_user",
                        "strength": "medium",
                        "trigger": " ".join(events[i + 1]["texts"])[:280]})
    return out


# ── omission-probes (SHADOW, project-scoped) ─────────────────────────────────
def read_central_rules(project: str) -> list[dict]:
    """Read probe rules for a project from the meta-side central config."""
    if not CENTRAL_RULES.exists():
        return []
    try:
        return json.loads(CENTRAL_RULES.read_text(encoding="utf-8")).get(project, [])
    except (json.JSONDecodeError, ValueError, OSError):
        return []


def read_omission_rules(project_dir: Path) -> list[dict]:
    """Parse an optional `<!-- omission-rules {json} -->` block from a project's
    CLAUDE.md. Kept so per-project declarations can extend the central config."""
    md = project_dir / "CLAUDE.md"
    if not md.exists():
        return []
    m = _OMISSION_BLOCK.search(md.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return []
    try:
        return json.loads(m.group(1)).get("rules", [])
    except (json.JSONDecodeError, ValueError):
        return []


def _wrote_trigger_file(events: list[dict], globs: list[str]) -> str | None:
    for ev in events:
        for t in ev["tools"]:
            if t["name"] not in ("Write", "Edit", "NotebookEdit"):
                continue
            fp = str(t["input"].get("file_path", ""))
            for g in globs:
                if g.strip("*/ ") and g.strip("*/ ") in fp:
                    return fp
    return None


def _any_required_seen(events: list[dict], required: list[str]) -> bool:
    """A required capability counts as seen if it appears as a tool name OR a
    substring of a Bash command OR a Read of a matching path."""
    for ev in events:
        for t in ev["tools"]:
            name = t["name"]
            blob = (name + " " + json.dumps(t["input"], default=str)).lower()
            for r in required:
                if r.lower() in blob:
                    return True
    return False


def extract_omissions(events: list[dict], rules: list[dict]) -> list[dict]:
    """For each declared rule: trigger-file touched AND no required capability
    seen → shadow omission signal. Heuristic; FP-tolerant because shadow."""
    out: list[dict] = []
    for rule in rules:
        globs = rule.get("trigger_files", [])
        required = rule.get("required_any", [])
        hit = _wrote_trigger_file(events, globs)
        if hit and not _any_required_seen(events, required):
            out.append({"kind": "omission", "subtype": rule.get("name", "unnamed"),
                        "strength": "shadow", "shadow": True,
                        "trigger": f"wrote {hit} without any of {required}"})
    return out


def extract_signals(events: list[dict], rules: list[dict]) -> list[dict]:
    return extract_corrections(events) + extract_omissions(events, rules)


# ── IO ───────────────────────────────────────────────────────────────────────
def _sig_hash(session: str, s: dict) -> str:
    return hashlib.sha1(
        f"{session}|{s.get('subtype')}|{s.get('trigger','')}".encode(), usedforsecurity=False
    ).hexdigest()[:16]


def _already_seen(session: str) -> set[str]:
    seen: set[str] = set()
    if not CAPTURE_LOG.exists():
        return seen
    for line in CAPTURE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if r.get("session") == session and r.get("hash"):
            seen.add(r["hash"])
    return seen


def append_signals(session: str, project: str, signals: list[dict], ts: str) -> int:
    if not signals:
        return 0
    seen = _already_seen(session)
    CAPTURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with CAPTURE_LOG.open("a", encoding="utf-8") as f:
        for s in signals:
            h = _sig_hash(session, s)
            if h in seen:
                continue
            seen.add(h)
            row = {"schema": "reflect.capture.v1", "session": session, "project": project,
                   "ts": ts, "hash": h, **s}
            f.write(json.dumps(row, default=str) + "\n")
            written += 1
    return written


def main() -> int:
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except (json.JSONDecodeError, ValueError):
        payload = {}
    transcript = payload.get("transcript_path", "")
    session = (payload.get("session_id") or "unknown")[:36]
    cwd = payload.get("cwd", "")
    project = Path(cwd).name if cwd else "unknown"
    ts = payload.get("timestamp") or _utc_now()

    if project not in TESTBED:
        return 0  # shadow scope: capture only on the test bed
    if not transcript or not Path(transcript).exists():
        return 0

    try:
        lines = Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines()
        events = parse_events(lines)
        rules = read_central_rules(project) + (read_omission_rules(Path(cwd)) if cwd else [])
        signals = extract_signals(events, rules)
        n = append_signals(session, project, signals, ts)
        if n:
            sys.stderr.write(f"[reflect-capture] {n} signal(s) from {project}/{session[:8]} (shadow)\n")
    except Exception as e:  # fail-open: never disrupt session end
        sys.stderr.write(f"[reflect-capture] skipped ({type(e).__name__})\n")
    return 0


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.exit(main())
