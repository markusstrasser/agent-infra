#!/usr/bin/env python3
"""Consolidate audit findings from debug scouts, fix-backlog, code-review.

llm: none

Usage:
  audit_findings_consolidation.py docs/audit --repo ~/Projects/genomics --date 2026-06-19
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from findings_parse import parse_findings, sev_rank  # noqa: E402
from tool_contract import LlmClass, print_llm_header  # noqa: E402

TOOL = "audit-findings-consolidation"
BACKLOG_ROW = re.compile(r"^\|\s*(P[0-3]|P\?)\s*\|\s*\*\*([^*|]+)\*\*\s*\|\s*(.+?)\s*\|\s*$")


def parse_fix_backlog(text: str, source: str) -> tuple[list[dict], list[str]]:
    out: list[dict] = []
    errors: list[str] = []
    for line in text.splitlines():
        m = BACKLOG_ROW.match(line.strip())
        if not m:
            continue
        sev, fid, claim = m.group(1), m.group(2).strip(), m.group(3).strip()
        out.append(
            {
                "id": fid,
                "severity": sev,
                "verdict": "SUSPECT",
                "domain": "fix-backlog",
                "claim": claim,
                "evidence": fid,
                "source": source,
                "dedupe": hashlib.sha256(f"{fid}:{claim}".lower().encode()).hexdigest()[:12],
            }
        )
    if "Priority queue" in text and not out:
        errors.append(f"{source}: priority table present but 0 rows parsed")
    return out, errors


def load_code_review(repo: Path, day: str) -> list[dict]:
    base = repo / "artifacts" / "code-review"
    if not base.is_dir():
        return []
    out: list[dict] = []
    sev_map = {"HIGH": "P0", "MEDIUM": "P1", "LOW": "P2"}
    for jsonl in sorted(base.rglob(f"{day}.jsonl")):
        for line in jsonl.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            sev = sev_map.get(str(row.get("severity", "")).upper(), "P2")
            out.append(
                {
                    "id": f"cr-{row.get('file', '?')}:{row.get('line', 0)}",
                    "severity": sev,
                    "verdict": "SUSPECT",
                    "domain": row.get("category", "code-review"),
                    "claim": row.get("description", ""),
                    "evidence": f"{row.get('file')}:{row.get('line')}",
                    "source": jsonl.name,
                    "dedupe": hashlib.sha256(
                        f"{row.get('file')}:{row.get('line')}:{row.get('description', '')[:80]}".encode()
                    ).hexdigest()[:12],
                }
            )
    return out


def dedupe(items: list[dict]) -> tuple[list[dict], int]:
    seen: set[str] = set()
    out: list[dict] = []
    dupes = 0
    for it in items:
        key = it.get("dedupe") or it.get("id", "")
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        out.append(it)
    out.sort(key=lambda x: (sev_rank(x.get("severity", "P9")), x.get("id", "")))
    return out, dupes


FILE_LINE_RE = re.compile(r"(?P<path>[\w./-]+\.[A-Za-z0-9_]+):(?P<line>\d+)")


def extract_file_line(finding: dict) -> tuple[str, int] | None:
    """First repo-relative file:line in a finding's evidence/claim, or None.

    Rejects URL ``host:port`` matches (a ``://`` just before the token) so a
    finding that merely cites a URL is never mistaken for a dangling file
    pointer and wrongly dropped.
    """
    for field in ("evidence", "claim"):
        val = str(finding.get(field, ""))
        for m in FILE_LINE_RE.finditer(val):
            path = m.group("path")
            # repo-relative paths never start with "/" or contain "//"; both
            # signal a URL authority (e.g. "//example.com" from "http://…:8080").
            if path.startswith("/") or "//" in path:
                continue
            line = int(m.group("line"))
            if line > 0:
                return path, line
    return None


def _blame_epoch(repo: Path, rel: str, line: int) -> int | None:
    """committer-time of the commit that last touched repo/rel at `line`, or None."""
    try:
        res = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "--no-pager",
                "blame",
                "-L",
                f"{line},{line}",
                "--porcelain",
                "--",
                rel,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    for out_line in res.stdout.splitlines():
        if out_line.startswith("committer-time "):
            try:
                return int(out_line.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def head_recheck(
    findings: list[dict], repo: Path, audit_dir: Path
) -> tuple[list[dict], list[dict]]:
    """Re-check each finding's cited file:line against the CURRENT tree.

    Conservative noise reduction (the steward-proposal contract): only DROPS a
    finding when its cited location is *gone* — file deleted, or line past EOF,
    an unusable pointer. A finding whose line merely *changed* since the scout
    ran is KEPT and flagged for re-verify. Any uncertainty (no locator,
    unreadable file, git error) → KEEP. Never drops on uncertainty; dropped
    findings are surfaced in the handoff, never silently hidden.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    for it in findings:
        loc = extract_file_line(it)
        if loc is None:
            kept.append(it)
            continue
        rel, line = loc
        target = repo / rel
        try:
            is_file = target.is_file()
        except OSError:
            kept.append(it)
            continue
        if not is_file:
            it["_drop_reason"] = f"cited file gone: {rel}"
            dropped.append(it)
            continue
        try:
            nlines = len(target.read_bytes().splitlines())
        except OSError:
            kept.append(it)
            continue
        if line > nlines:
            it["_drop_reason"] = f"cited line {line} past EOF ({rel} now {nlines} lines)"
            dropped.append(it)
            continue
        src = audit_dir / str(it.get("source", ""))
        try:
            scout_mtime = src.stat().st_mtime if src.is_file() else None
        except OSError:
            scout_mtime = None
        if scout_mtime is not None:
            epoch = _blame_epoch(repo, rel, line)
            if epoch is not None and epoch > scout_mtime + 60:
                it["stale_flag"] = (
                    f"{rel}:{line} changed after scout ran — re-verify (may already be fixed)"
                )
        kept.append(it)
    return kept, dropped


def write_handoff(
    path: Path,
    day: str,
    stats: dict,
    findings: list[dict],
    parse_errors: list[str],
    dropped: list[dict],
) -> None:
    by_sev: dict[str, list[dict]] = defaultdict(list)
    for item in findings:
        by_sev[item.get("severity", "P?")].append(item)

    lines = [
        f"# Findings consolidation handoff — {day}",
        "",
        f"**Tool:** `{TOOL}` · **llm:** none",
        f"**Sources:** debug={stats.get('debug', 0)} · fix-backlog={stats.get('backlog', 0)} · "
        f"code-review={stats.get('code_review', 0)}",
        f"**Findings:** {len(findings)} surviving "
        f"(dupes dropped: {stats.get('dupes', 0)} · stale dropped: {stats.get('stale_dropped', 0)})",
        f"**Parse errors:** {len(parse_errors)}",
        "",
        "**Orchestrator model:** validate, propose fixes. **Operator:** approves apply.",
        "",
    ]
    if parse_errors:
        lines.extend(["## Parse errors", ""] + [f"- {e}" for e in parse_errors[:30]] + [""])
    for sev in ("P0", "P1", "P2", "P3", "P?"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev} ({len(items)})")
        lines.append("")
        for it in items:
            lines.append(
                f"### {it.get('id', '?')} [{it.get('verdict', '?')}] — {it.get('domain', '?')}"
            )
            lines.append(f"- **Claim:** {it.get('claim', '')}")
            lines.append(f"- **Evidence:** {it.get('evidence', '')}")
            if it.get("stale_flag"):
                lines.append(f"- **⚠ Stale?:** {it['stale_flag']}")
            lines.append(f"- **Source:** `{it.get('source', '')}`")
            lines.append("")
    if dropped:
        lines.append(f"## Dropped — cited location gone since scout ({len(dropped)})")
        lines.append("")
        lines.append(
            "_Re-checked vs current HEAD: the cited file:line no longer exists (file "
            "deleted or line past EOF). Listed not hidden — re-open if the concern moved "
            "rather than was fixed._"
        )
        lines.append("")
        for it in dropped:
            lines.append(
                f"- `{it.get('id', '?')}` [{it.get('evidence', '')}] — "
                f"{it.get('_drop_reason', 'location gone')}"
            )
        lines.append("")
    if not findings:
        lines.append("_No findings parsed._")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audit_dir", type=Path, nargs="?", default=Path("docs/audit"))
    ap.add_argument("--date", default=str(date.today()))
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--kind", choices=("debug", "backlog", "code-review", "all"), default="all")
    ap.add_argument(
        "--no-head-recheck",
        action="store_true",
        help="skip re-checking each finding's cited file:line against current HEAD",
    )
    args = ap.parse_args()

    print_llm_header(LlmClass.NONE)
    audit_dir = args.audit_dir.resolve()
    repo = (args.repo or audit_dir.parent.parent).resolve()
    findings: list[dict] = []
    parse_errors: list[str] = []
    stats = {"debug": 0, "backlog": 0, "code_review": 0, "dupes": 0, "stale_dropped": 0}

    if args.kind in ("debug", "all") and audit_dir.is_dir():
        pattern = f"{args.date}-debug-*.md"
        files = sorted(
            f
            for f in audit_dir.glob(pattern)
            if "-handoff" not in f.name
            and "-manifest" not in f.name
            and "-consolidation" not in f.name
        )
        stats["debug"] = len(files)
        for f in files:
            found, bad = parse_findings(f.read_text(errors="replace"), f)
            parse_errors.extend(bad)
            findings.extend(found)

    if args.kind in ("backlog", "all"):
        for name in (f"{args.date}-fix-backlog.md", "fix-backlog.md"):
            fb = audit_dir / name
            if fb.is_file():
                rows, errs = parse_fix_backlog(fb.read_text(errors="replace"), fb.name)
                stats["backlog"] += len(rows)
                parse_errors.extend(errs)
                findings.extend(rows)
                break

    if args.kind in ("code-review", "all"):
        cr = load_code_review(repo, args.date)
        stats["code_review"] = len(cr)
        findings.extend(cr)

    findings, stats["dupes"] = dedupe(findings)
    dropped: list[dict] = []
    if not args.no_head_recheck:
        findings, dropped = head_recheck(findings, repo, audit_dir)
    stats["stale_dropped"] = len(dropped)
    out = audit_dir / f"{args.date}-findings-consolidation-handoff.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_handoff(out, args.date, stats, findings, parse_errors, dropped)
    print(out)
    return 1 if parse_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
