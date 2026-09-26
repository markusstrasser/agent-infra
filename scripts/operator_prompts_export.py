#!/usr/bin/env python3
"""Export operator-typed prompts per project, each with the agent turn around it.

Primitive for steering/taste mining (first consumer: the 2026-09-26 operator
steering catalog, research/2026-09-26-operator-steering-moves.md). One JSONL per
project in --out: {project, vendor, session, ts, prompt, prompt_chars,
prev_agent (tail of the agent text since the previous operator prompt),
next_agent (head of the reply)} plus stats.json.

Raw sources, not agentlogs.db: the DB lacks Claude's origin/entrypoint stamps
(needed to drop `claude -p` dispatches and launchd ticks) and prunes at 30 days.

  Claude  ~/.claude/projects/-Users-alien-Projects-<p>*/*.jsonl  + SSD archive
  Codex   ~/.codex/sessions/**/rollout-*.jsonl                  + SSD archive
          (interactive originators only; codex_exec dispatches dropped)
  Cursor  agentlogs.db (cursor-agent <user_query> rows)

Authorship uses the shared predicates: scripts/common/transcript_text
.is_operator_authored for Claude, agentlogs.authorship.is_injected_user_text
plus the Codex `user.text` content kind for Codex and Cursor.

Usage: uv run python3 scripts/operator_prompts_export.py --projects arc-agi intel --out DIR
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

AI = Path.home() / "Projects" / "agent-infra"
sys.path.insert(0, str(AI / "scripts" / "common"))
sys.path.insert(0, str(AI / "src"))
from transcript_text import is_operator_authored, user_texts  # noqa: E402
from agentlogs.authorship import is_injected_user_text  # noqa: E402

HOME = Path.home()
ARCHIVE = Path("/Volumes/2TBPNY/agentlogs-archive")
CLAUDE_DIRS = [HOME / ".claude" / "projects", ARCHIVE / "claude"]
CODEX_DIRS = [HOME / ".codex" / "sessions", ARCHIVE / "codex"]
DB = HOME / ".claude" / "agentlogs.db"

PROMPT_CAP = 7000  # chars; pasted documents keep head + tail
PREV_TAIL = 1600
NEXT_HEAD = 500

CMD_RE = re.compile(
    r"<command-name>(?P<name>[^<]+)</command-name>.*?(?:<command-args>(?P<args>.*?)</command-args>)?",
    re.S,
)


def cap(text: str, n: int = PROMPT_CAP) -> str:
    text = text.strip()
    if len(text) <= n:
        return text
    head, tail = int(n * 0.6), int(n * 0.3)
    return f"{text[:head]}\n[... {len(text) - head - tail} chars omitted ...]\n{text[-tail:]}"


def squash_command(text: str) -> str:
    m = CMD_RE.search(text)
    if not m:
        return text
    args = (m.group("args") or "").strip()
    return f"{m.group('name').strip()} {args}".strip()


class Collector:
    def __init__(self) -> None:
        self.records: list[dict] = []
        self.seen: set[tuple] = set()

    def add(self, **rec) -> dict | None:
        key = (rec["project"], rec["prompt"][:400])
        if key in self.seen:  # resumed/forked sessions re-carry old prompts
            return None
        self.seen.add(key)
        self.records.append(rec)
        return rec


# ---------------------------------------------------------------- Claude
def claude_files(project: str) -> list[Path]:
    out: dict[str, Path] = {}
    for base in CLAUDE_DIRS:
        for d in glob.glob(str(base / f"-Users-alien-Projects-{project}")) + glob.glob(
            str(base / f"-Users-alien-Projects-{project}--*")
        ):
            for f in glob.glob(os.path.join(d, "*.jsonl")):
                p = Path(f)
                prev = out.get(p.name)
                if prev is None or p.stat().st_size > prev.stat().st_size:
                    out[p.name] = p  # live copy usually newer/larger than archive
    return sorted(out.values())


def assistant_text_claude(obj: dict) -> str:
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def scan_claude(project: str, col: Collector, stats: Counter) -> None:
    for f in claude_files(project):
        stats["claude_files"] += 1
        pending: dict | None = None
        agent_buf: list[str] = []
        try:
            lines = f.open(encoding="utf-8", errors="replace").readlines()
        except OSError:
            stats["claude_unreadable"] += 1
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            if t == "assistant":
                txt = assistant_text_claude(obj).strip()
                if txt:
                    agent_buf.append(txt)
                    if pending is not None and len(pending["next_agent"]) < NEXT_HEAD:
                        pending["next_agent"] = (pending["next_agent"] + "\n" + txt).strip()[:NEXT_HEAD]
                continue
            if t != "user":
                continue
            if not is_operator_authored(obj):
                continue
            text = "\n".join(x for x in user_texts(obj) if isinstance(x, str)).strip()
            if not text:
                continue
            text = squash_command(text)
            prev = "\n".join(agent_buf)[-PREV_TAIL:]
            agent_buf = []
            rec = dict(
                project=project,
                vendor="claude",
                session=str(obj.get("sessionId", f.stem))[:8],
                ts=obj.get("timestamp", ""),
                prompt=cap(text),
                prompt_chars=len(text),
                prev_agent=prev,
                next_agent="",
            )
            pending = col.add(**rec)
            stats["claude_prompts"] += 1


# ---------------------------------------------------------------- Codex
def codex_meta(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
        o = json.loads(first)
    except (OSError, json.JSONDecodeError):
        return None
    if o.get("type") != "session_meta":
        return None
    return o.get("payload") or {}


def codex_index(projects: list[str]) -> dict[str, list[str]]:
    roots = {p: str(HOME / "Projects" / p) for p in projects}
    by_project: dict[str, list[str]] = defaultdict(list)
    seen_ids: set[str] = set()
    for base in CODEX_DIRS:
        for path in glob.iglob(str(base / "**" / "rollout-*.jsonl"), recursive=True):
            meta = codex_meta(path)
            if not meta:
                continue
            cwd = meta.get("cwd") or ""
            src = meta.get("source")
            orig = meta.get("originator") or ""
            if orig == "codex_exec" or src == "exec" or isinstance(src, dict):
                continue  # headless dispatch or subagent thread
            sid = meta.get("id") or meta.get("session_id") or path
            if sid in seen_ids:
                continue
            for p, root in roots.items():
                if cwd == root or cwd.startswith(root + "/"):
                    by_project[p].append(path)
                    seen_ids.add(sid)
                    break
    return by_project


def codex_texts(payload: dict, kind: str) -> list[str]:
    out = []
    for c in payload.get("content") or []:
        if isinstance(c, dict) and c.get("type") == kind and c.get("text"):
            out.append(c["text"])
    return out


def scan_codex(project: str, paths: list[str], col: Collector, stats: Counter) -> None:
    for path in sorted(paths):
        stats["codex_files"] += 1
        meta = codex_meta(path) or {}
        sid = str(meta.get("id") or meta.get("session_id") or Path(path).stem)[:8]
        agent_buf: list[str] = []
        pending: dict | None = None
        seen_turn_texts: set[str] = set()
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("type") != "response_item":
                    # legacy rollouts carry the typed prompt as event_msg/user_message
                    p = o.get("payload") or {}
                    if o.get("type") == "event_msg" and p.get("type") == "user_message" and p.get("message"):
                        text = p["message"].strip()
                        if text and text not in seen_turn_texts and not is_injected_user_text(text):
                            seen_turn_texts.add(text)
                            prev = "\n".join(agent_buf)[-PREV_TAIL:]
                            agent_buf = []
                            pending = col.add(project=project, vendor="codex", session=sid, ts=o.get("timestamp", ""),
                                              prompt=cap(text), prompt_chars=len(text), prev_agent=prev, next_agent="")
                            stats["codex_prompts"] += 1
                    continue
                p = o.get("payload") or {}
                if p.get("type") != "message":
                    continue
                role = p.get("role")
                if role == "assistant":
                    txt = "\n".join(codex_texts(p, "output_text")).strip()
                    if txt:
                        agent_buf.append(txt)
                        if pending is not None and len(pending["next_agent"]) < NEXT_HEAD:
                            pending["next_agent"] = (pending["next_agent"] + "\n" + txt).strip()[:NEXT_HEAD]
                    continue
                if role != "user":
                    continue
                kinds = ((p.get("internal_chat_message_metadata_passthrough") or {}).get("content_item_kinds")) or []
                if kinds and "user.text" not in kinds:
                    continue
                text = "\n".join(codex_texts(p, "input_text")).strip()
                if not text or is_injected_user_text(text) or text in seen_turn_texts:
                    continue
                seen_turn_texts.add(text)
                prev = "\n".join(agent_buf)[-PREV_TAIL:]
                agent_buf = []
                pending = col.add(project=project, vendor="codex", session=sid, ts=o.get("timestamp", ""),
                                  prompt=cap(text), prompt_chars=len(text), prev_agent=prev, next_agent="")
                stats["codex_prompts"] += 1


# ---------------------------------------------------------------- Cursor
UQ_RE = re.compile(r"<user_query>(.*?)</user_query>", re.S)


def scan_cursor(project: str, col: Collector, stats: Counter) -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        """
        SELECT s.session_uuid, e.ts, e.kind, e.text FROM events e
        JOIN runs r ON r.run_id = e.run_id JOIN sessions s ON s.session_pk = r.session_pk
        WHERE s.vendor = 'cursor' AND s.project_slug = ? AND s.is_subagent = 0
          AND e.kind IN ('user_message', 'assistant_message') AND e.text IS NOT NULL
        ORDER BY s.session_uuid, r.run_id, e.seq
        """,
        (project,),
    ).fetchall()
    agent_buf: dict[str, list[str]] = defaultdict(list)
    for suuid, ts, kind, text in rows:
        if kind == "assistant_message":
            agent_buf[suuid].append(text.strip())
            continue
        if is_injected_user_text(text):
            continue
        m = UQ_RE.search(text)
        q = (m.group(1) if m else text).strip()
        if not q or re.fullmatch(r"<timestamp>[^<]*</timestamp>", q):
            continue  # timestamp-only frame: the query arrived as an image or attachment
        prev = "\n".join(agent_buf[suuid])[-PREV_TAIL:]
        agent_buf[suuid] = []
        col.add(project=project, vendor="cursor", session=str(suuid).split(":")[-1][:8], ts=ts or "",
                prompt=cap(q), prompt_chars=len(q), prev_agent=prev, next_agent="")
        stats["cursor_prompts"] += 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", nargs="+", required=True)
    ap.add_argument("--out", required=True, help="directory; writes <project>.jsonl + stats.json")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    codex_by_project = codex_index(args.projects)
    all_stats = {}
    for project in args.projects:
        col, stats = Collector(), Counter()
        scan_claude(project, col, stats)
        scan_codex(project, codex_by_project.get(project, []), col, stats)
        scan_cursor(project, col, stats)
        recs = sorted(col.records, key=lambda r: r["ts"] or "")
        with (out / f"{project}.jsonl").open("w") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats["kept"] = len(recs)
        stats["prompt_chars"] = sum(len(r["prompt"]) for r in recs)
        stats["context_chars"] = sum(len(r["prev_agent"]) + len(r["next_agent"]) for r in recs)
        stats["first_ts"] = recs[0]["ts"] if recs else ""
        stats["last_ts"] = recs[-1]["ts"] if recs else ""
        all_stats[project] = dict(stats)
        print(project, dict(stats), flush=True)
    (out / "stats.json").write_text(json.dumps(all_stats, indent=2))


if __name__ == "__main__":
    main()
