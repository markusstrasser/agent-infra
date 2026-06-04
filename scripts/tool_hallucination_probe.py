#!/usr/bin/env python3
"""One-time characterization of tool-hallucination events in agentlogs.db.

Arena-learning probe (research/2026-06-04-arena-agent-eval-transfer.md):
surfaces which tools get hallucinated against so we can fix tool affordances
(missing alias, misleading description, missing param) — NOT to rank models.

Deterministic, read-only. Two detectable classes (Amazon taxonomy arXiv:2601.05214):
  - invented-tool : "No such tool available: X" / "No tool named X"   (class a)
  - malformed-arg : "InputValidationError: <Tool> failed ... `param`"  (class b)
Class (c) tool-bypass (model fabricates a result, no call) is NOT detectable here.

Probe-before-build finding (2026-06-04): this signal is Claude-only-measurable.
Codex errors are shell/CLI failures (no named-tool schema to violate); Gemini
surfaces ~0; Kimi <system> lines are normal results. We report that explicitly
rather than emit a misleading cross-vendor rate.

Usage:
    uv run python3 scripts/tool_hallucination_probe.py
    uv run python3 scripts/tool_hallucination_probe.py --db /path/to/agentlogs.db
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter

DB_DEFAULT = os.path.expanduser("~/.claude/agentlogs.db")

# Tight signatures — MUST run against kind='tool_result' to avoid ~3x
# research-memo false positives (memo claim 5).
INVENTED_RE = re.compile(r"No (?:such tool available|tool named):?\s*([^\s<>\n]+)", re.I)
MALFORMED_RE = re.compile(r"InputValidationError:\s*(\w+)\s+failed", re.I)
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _ok(m): print(f"  ✓ {m}")
def _warn(m): print(f"  ! {m}")
def _header(s): print(f"\n[{s}]")


def fetch_claude_signatures(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        """
        SELECT e.text
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        JOIN sessions s ON r.session_pk = s.session_pk
        WHERE s.vendor = 'claude'
          AND e.kind = 'tool_result'
          AND (e.text LIKE '%InputValidationError%'
               OR e.text LIKE '%No such tool available%'
               OR e.text LIKE '%No tool named%')
        """
    ).fetchall()
    return [r[0] for r in rows if r[0]]


def cross_vendor_measurability(con: sqlite3.Connection) -> dict[str, dict]:
    """Confirm the signal is Claude-only. For each vendor, count the tight
    named-tool-schema signatures vs total tool_result errors."""
    out = {}
    for (vendor,) in con.execute("SELECT DISTINCT vendor FROM sessions ORDER BY vendor"):
        sig = con.execute(
            """
            SELECT COUNT(*) FROM events e
            JOIN runs r ON e.run_id=r.run_id JOIN sessions s ON r.session_pk=s.session_pk
            WHERE s.vendor=? AND e.kind='tool_result'
              AND (e.text LIKE '%InputValidationError%'
                   OR e.text LIKE '%No such tool available%'
                   OR e.text LIKE '%No tool named%')
            """,
            (vendor,),
        ).fetchone()[0]
        total_calls = con.execute(
            """
            SELECT COUNT(*) FROM tool_calls tc
            JOIN runs r ON tc.run_id=r.run_id JOIN sessions s ON r.session_pk=s.session_pk
            WHERE s.vendor=?
            """,
            (vendor,),
        ).fetchone()[0]
        out[vendor] = {"named_tool_signatures": sig, "total_tool_calls": total_calls}
    return out


def classify(texts: list[str]):
    invented = Counter()       # hallucinated tool name -> count
    malformed_tool = Counter() # real tool -> count of malformed-arg calls
    malformed_param = Counter()  # (tool, param) -> count
    n_invented = n_malformed = n_unclassified = 0

    for t in texts:
        m = INVENTED_RE.search(t)
        if m:
            name = m.group(1).strip().rstrip(".:,")
            invented[name] += 1
            n_invented += 1
            continue
        m = MALFORMED_RE.search(t)
        if m:
            tool = m.group(1)
            malformed_tool[tool] += 1
            n_malformed += 1
            # first backtick token after the tool name is the offending param
            params = BACKTICK_RE.findall(t)
            if params:
                malformed_param[(tool, params[0])] += 1
            continue
        n_unclassified += 1

    return {
        "invented": invented,
        "malformed_tool": malformed_tool,
        "malformed_param": malformed_param,
        "n_invented": n_invented,
        "n_malformed": n_malformed,
        "n_unclassified": n_unclassified,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"agentlogs DB not found: {args.db}", file=sys.stderr)
        return 1

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)

    _header("Cross-vendor measurability (named-tool-schema signatures)")
    cv = cross_vendor_measurability(con)
    print(f"  {'vendor':<8} {'signatures':>11} {'tool_calls':>11}  note")
    for vendor, d in cv.items():
        note = "deterministically measurable" if d["named_tool_signatures"] > 20 \
            else "not measurable from logs (no strict named-tool schema / shell-centric)"
        print(f"  {vendor:<8} {d['named_tool_signatures']:>11} {d['total_tool_calls']:>11}  {note}")
    _warn("Codex/Gemini/Kimi errors are shell/CLI failures, not tool hallucinations — excluded.")

    texts = fetch_claude_signatures(con)
    _header(f"Claude tool-hallucination events (n={len(texts)} genuine signatures)")
    c = classify(texts)
    print(f"  invented-tool : {c['n_invented']}")
    print(f"  malformed-arg : {c['n_malformed']}")
    print(f"  unclassified  : {c['n_unclassified']}")

    _header(f"Top invented (nonexistent) tool names — TODO: alias or remove the temptation")
    for name, n in c["invented"].most_common(args.top):
        print(f"  {n:>4}  {name}")

    _header(f"Top tools called with malformed args — TODO: fix description / params")
    for tool, n in c["malformed_tool"].most_common(args.top):
        print(f"  {n:>4}  {tool}")

    _header(f"Top (tool, offending-param) pairs")
    for (tool, param), n in c["malformed_param"].most_common(args.top):
        print(f"  {n:>4}  {tool:<22} {param}")

    con.close()
    _header("Done")
    _ok("Read-only characterization complete. Fix the top affordances, then re-run to confirm decay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
