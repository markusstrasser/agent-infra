#!/usr/bin/env python3
"""Steering signal extraction from cross-vendor session data.

Mines corrections, feedback, topic drift, and permission signals from
runlogs.db (Claude, Codex, Gemini, Kimi), hook telemetry, and session
receipts. Designed to feed goals/constitution skill reconnaissance.

Usage:
    steering-signals.py [--days N] [--project P] [--json] [--verbose]

Output: structured report of steering intelligence grouped by signal type.
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common.paths import RUNLOGS_DB, TRIGGERS_FILE, RECEIPTS_PATH

# ---------------------------------------------------------------------------
# Signal patterns
# ---------------------------------------------------------------------------

# Explicit #f feedback tag
FEEDBACK_RE = re.compile(r"(?:^|\s)#f(?:\s|$)", re.MULTILINE)

# Correction patterns — short user messages that steer behavior
# Grouped by strength: strong corrections vs softer redirects
STRONG_CORRECTION_RES = [
    re.compile(r"\bno[,.]?\s", re.IGNORECASE),
    re.compile(r"\bdon'?t\b", re.IGNORECASE),
    re.compile(r"\bstop\b", re.IGNORECASE),
    re.compile(r"\bwrong\b", re.IGNORECASE),
    re.compile(r"\bnot that\b", re.IGNORECASE),
    re.compile(r"\bthat'?s not\b", re.IGNORECASE),
    re.compile(r"\bI said\b", re.IGNORECASE),
    re.compile(r"\bI meant\b", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
]

REDIRECT_RES = [
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\binstead\b", re.IGNORECASE),
    re.compile(r"\bforget that\b", re.IGNORECASE),
    re.compile(r"\blet'?s not\b", re.IGNORECASE),
    re.compile(r"\bchange of plan\b", re.IGNORECASE),
    re.compile(r"\brather\b", re.IGNORECASE),
    re.compile(r"\bshould be\b", re.IGNORECASE),
]

# Filter out automated/formulaic messages
NOISE_RES = [
    re.compile(r"^Stop hook feedback", re.IGNORECASE),
    re.compile(r"^<system-reminder>"),
    re.compile(r"^Uncommitted changes"),
    re.compile(r"^Session debrief"),
]

# Max message length to consider as a correction (long messages are instructions, not corrections)
CORRECTION_MAX_LEN = 300


def is_noise(text: str) -> bool:
    return any(r.search(text) for r in NOISE_RES)


def classify_correction(text: str) -> str | None:
    """Classify a user message as a correction type or None."""
    if len(text) > CORRECTION_MAX_LEN:
        return None
    if is_noise(text):
        return None
    for r in STRONG_CORRECTION_RES:
        if r.search(text):
            return "correction"
    for r in REDIRECT_RES:
        if r.search(text):
            return "redirect"
    return None


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    from common.db import open_db
    return open_db(RUNLOGS_DB, foreign_keys=True)


def query_user_messages(db: sqlite3.Connection, days: int, project: str | None) -> list[dict]:
    """Get user messages from runlogs.db across all vendors."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sql = """
        SELECT e.event_id, e.run_id, e.text, e.ts,
               r.vendor, r.cwd, r.model_resolved
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        WHERE e.kind = 'user_message'
          AND e.ts >= ?
          AND e.text IS NOT NULL
          AND length(e.text) > 2
          AND e.text NOT LIKE '<system-reminder>%'
          AND e.text NOT LIKE 'Stop hook feedback%'
          AND e.text NOT LIKE '<local-command-%'
          AND e.text NOT LIKE '<command-%'
          AND e.text NOT LIKE '[Request interrupted%'
          AND e.text NOT LIKE 'Base directory for this skill%'
    """
    params: list = [cutoff]
    if project:
        sql += " AND (r.cwd LIKE ? OR r.cwd LIKE ?)"
        params.extend([f"%/{project}", f"%/{project}/%"])
    sql += " ORDER BY e.ts"
    return [dict(row) for row in db.execute(sql, params).fetchall()]


def query_topic_distribution(db: sqlite3.Connection, days: int) -> list[dict]:
    """Session count and cost by project slug."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sql = """
        SELECT r.vendor,
               COALESCE(s.project_slug, 'unknown') as project,
               COUNT(DISTINCT r.run_id) as runs,
               COUNT(CASE WHEN e.kind = 'user_message'
                          AND e.text NOT LIKE '<system-reminder>%%'
                          AND e.text NOT LIKE 'Stop hook feedback%%'
                          AND e.text NOT LIKE '<local-command-%%'
                          AND e.text NOT LIKE '<command-%%'
                          AND e.text NOT LIKE '[Request interrupted%%'
                          AND e.text NOT LIKE 'Base directory for this skill%%'
                          AND length(e.text) > 2
                     THEN 1 END) as user_msgs
        FROM runs r
        JOIN sessions s ON r.session_pk = s.session_pk
        LEFT JOIN events e ON e.run_id = r.run_id
        WHERE r.started_at >= ?
        GROUP BY r.vendor, s.project_slug
        ORDER BY runs DESC
    """
    return [dict(row) for row in db.execute(sql, [cutoff]).fetchall()]


def query_abandoned_sessions(db: sqlite3.Connection, days: int, project: str | None) -> list[dict]:
    """Sessions with tool calls but no git commits (started work, didn't finish)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sql = """
        SELECT r.run_id, r.vendor, r.cwd, r.started_at, r.model_resolved,
               COUNT(tc.tool_call_id) as tool_calls,
               COALESCE(s.project_slug, 'unknown') as project
        FROM runs r
        JOIN sessions s ON r.session_pk = s.session_pk
        LEFT JOIN tool_calls tc ON tc.run_id = r.run_id
        WHERE r.started_at >= ?
          AND r.status IN ('completed', 'error')
          AND tc.tool_call_id IS NOT NULL
          AND r.run_id NOT IN (
              SELECT DISTINCT e2.run_id FROM events e2
              WHERE e2.run_id = r.run_id
                AND e2.kind = 'tool_call'
                AND e2.text = 'Bash'
                AND EXISTS (
                    SELECT 1 FROM events e3
                    WHERE e3.run_id = e2.run_id
                      AND e3.correlation_id = e2.correlation_id
                      AND e3.kind = 'tool_result'
                      AND e3.text LIKE '%git commit%'
                )
          )
    """
    params: list = [cutoff]
    if project:
        sql += " AND (r.cwd LIKE ? OR r.cwd LIKE ?)"
        params.extend([f"%/{project}", f"%/{project}/%"])
    sql += " GROUP BY r.run_id HAVING tool_calls >= 5 ORDER BY r.started_at DESC LIMIT 20"
    return [dict(row) for row in db.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Hook telemetry
# ---------------------------------------------------------------------------

def load_hook_signals(days: int, project: str | None) -> list[dict]:
    """Load hook blocks/warnings from telemetry."""
    if not TRIGGERS_FILE.exists():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    signals = []
    with open(TRIGGERS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts", "")
            if ts < cutoff:
                continue
            if project and entry.get("project") != project:
                continue
            if entry.get("action") in ("block", "warn"):
                signals.append(entry)
    return signals


# ---------------------------------------------------------------------------
# Receipt analysis
# ---------------------------------------------------------------------------

def load_receipts(days: int, project: str | None) -> list[dict]:
    """Load session receipts for cost/commit analysis."""
    if not RECEIPTS_PATH.exists():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    receipts = []
    with open(RECEIPTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = r.get("timestamp", r.get("ts", ""))
            if ts < cutoff:
                continue
            if project and project not in (r.get("project", "") or ""):
                continue
            receipts.append(r)
    return receipts


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def extract_signals(messages: list[dict]) -> dict:
    """Extract all steering signals from user messages."""
    feedback = []       # #f tagged
    corrections = []    # strong corrections
    redirects = []      # softer redirects

    for msg in messages:
        text = msg["text"]

        # Explicit feedback
        if FEEDBACK_RE.search(text) and len(text) < 500:
            cleaned = FEEDBACK_RE.sub(" ", text).strip()
            if cleaned and not is_noise(cleaned):
                feedback.append({
                    "text": cleaned[:300],
                    "vendor": msg["vendor"],
                    "ts": msg["ts"],
                    "project": _project_from_cwd(msg.get("cwd")),
                })

        # Corrections and redirects
        ctype = classify_correction(text)
        if ctype == "correction":
            corrections.append({
                "text": text[:300],
                "vendor": msg["vendor"],
                "ts": msg["ts"],
                "project": _project_from_cwd(msg.get("cwd")),
            })
        elif ctype == "redirect":
            redirects.append({
                "text": text[:300],
                "vendor": msg["vendor"],
                "ts": msg["ts"],
                "project": _project_from_cwd(msg.get("cwd")),
            })

    return {
        "feedback": feedback,
        "corrections": corrections,
        "redirects": redirects,
    }


def _project_from_cwd(cwd: str | None) -> str:
    if not cwd:
        return "unknown"
    return Path(cwd).name


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

def synthesize_themes(signals: dict) -> list[dict]:
    """Group correction signals into themes by recurring words/phrases."""
    all_texts = []
    for key in ("feedback", "corrections", "redirects"):
        for entry in signals[key]:
            all_texts.append(entry["text"].lower())

    if not all_texts:
        return []

    # Simple word frequency (skip common words)
    stop = {"the", "a", "an", "is", "it", "to", "in", "for", "of", "and",
            "that", "this", "not", "don't", "no", "i", "you", "we", "they",
            "be", "do", "have", "with", "on", "at", "but", "or", "from",
            "my", "me", "your", "are", "was", "were", "been", "just", "so",
            "if", "when", "what", "how", "can", "should", "would", "could",
            "will", "about", "like", "then", "than", "also", "here", "there",
            "all", "up", "out", "some", "them", "these", "those", "which",
            "its", "has", "had", "did", "does", "get", "got", "let", "use",
            "make", "need", "want", "try", "see", "one", "two", "new", "now",
            "yeah", "yes", "okay", "etc", "via", "maybe", "right", "well",
            "still", "think", "good", "thing", "really", "sure", "much",
            "way", "very", "too", "already", "check", "look", "run",
            "ultrathink", "mean", "stuff", "probably", "know", "going",
            "work", "file", "something", "anything"}
    words = Counter()
    for text in all_texts:
        for word in re.findall(r"\b[a-z]{3,}\b", text):
            if word not in stop:
                words[word] += 1

    return [{"word": w, "count": c} for w, c in words.most_common(20) if c >= 2]


def format_report(signals: dict, topics: list[dict], hooks: list[dict],
                  themes: list[dict], receipts: list[dict], days: int) -> str:
    """Format human-readable steering intelligence report."""
    lines = [f"# Steering Intelligence Report ({days} days)\n"]

    # 1. Explicit feedback
    fb = signals["feedback"]
    lines.append(f"## Explicit Feedback (#f tags): {len(fb)} entries\n")
    if fb:
        by_project = defaultdict(list)
        for entry in fb:
            by_project[entry["project"]].append(entry)
        for proj in sorted(by_project):
            lines.append(f"### {proj}")
            for e in by_project[proj][-10:]:  # last 10 per project
                lines.append(f"- [{e['vendor']}] {e['text']}")
            lines.append("")
    else:
        lines.append("No #f feedback found.\n")

    # 2. Corrections
    corr = signals["corrections"]
    lines.append(f"## Corrections: {len(corr)} entries\n")
    if corr:
        by_project = defaultdict(list)
        for entry in corr:
            by_project[entry["project"]].append(entry)
        for proj in sorted(by_project):
            entries = by_project[proj]
            lines.append(f"### {proj} ({len(entries)} corrections)")
            for e in entries[-10:]:
                lines.append(f"- [{e['vendor']}] {e['text'][:120]}")
            lines.append("")
    else:
        lines.append("No corrections detected.\n")

    # 3. Redirects
    redir = signals["redirects"]
    lines.append(f"## Redirects: {len(redir)} entries\n")
    if redir:
        by_project = defaultdict(list)
        for entry in redir:
            by_project[entry["project"]].append(entry)
        for proj in sorted(by_project):
            entries = by_project[proj]
            lines.append(f"### {proj} ({len(entries)} redirects)")
            for e in entries[-10:]:
                lines.append(f"- [{e['vendor']}] {e['text'][:120]}")
            lines.append("")
    else:
        lines.append("No redirects detected.\n")

    # 4. Themes
    lines.append("## Recurring Themes in Corrections\n")
    if themes:
        for t in themes[:15]:
            lines.append(f"- **{t['word']}** ({t['count']}x)")
        lines.append("")
    else:
        lines.append("No recurring themes found.\n")

    # 5. Topic distribution (time allocation)
    lines.append("## Topic Distribution (time allocation)\n")
    if topics:
        lines.append("| Vendor | Project | Runs | User Messages |")
        lines.append("|--------|---------|------|---------------|")
        for t in topics[:20]:
            lines.append(f"| {t['vendor']} | {t['project']} | {t['runs']} | {t['user_msgs']} |")
        lines.append("")

    # 6. Hook signals (systematic steering)
    lines.append(f"## Hook Signals: {len(hooks)} triggers\n")
    if hooks:
        hook_counts = Counter(h.get("hook", "unknown") for h in hooks)
        action_counts = Counter(h.get("action", "unknown") for h in hooks)
        lines.append("By hook:")
        for hook, count in hook_counts.most_common(10):
            lines.append(f"- {hook}: {count}")
        lines.append("\nBy action:")
        for action, count in action_counts.most_common():
            lines.append(f"- {action}: {count}")
        lines.append("")

    # 7. Receipt summary (cost allocation)
    if receipts:
        cost_by_project = defaultdict(float)
        commits_by_project = defaultdict(int)
        for r in receipts:
            proj = r.get("project", "unknown") or "unknown"
            cost_by_project[proj] += r.get("cost_usd", r.get("cost", 0))
            commits_by_project[proj] += len(r.get("commits", []))

        lines.append("## Cost Allocation\n")
        lines.append("| Project | Cost | Commits |")
        lines.append("|---------|------|---------|")
        for proj in sorted(cost_by_project, key=lambda p: cost_by_project[p], reverse=True):
            lines.append(f"| {proj} | ${cost_by_project[proj]:.2f} | {commits_by_project[proj]} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract steering signals from cross-vendor session data")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default: 30)")
    parser.add_argument("--project", type=str, help="Filter to specific project")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("--verbose", action="store_true", help="Show debug info")
    args = parser.parse_args()

    if not RUNLOGS_DB.exists():
        print("runlogs.db not found. Run: uv run python3 scripts/runlog.py import", file=sys.stderr)
        sys.exit(1)

    db = get_db()

    if args.verbose:
        print(f"Querying {args.days} days of data...", file=sys.stderr)

    # Gather raw data
    messages = query_user_messages(db, args.days, args.project)
    topics = query_topic_distribution(db, args.days)
    hooks = load_hook_signals(args.days, args.project)
    receipts = load_receipts(args.days, args.project)

    if args.verbose:
        print(f"  {len(messages)} user messages, {len(hooks)} hook triggers, {len(receipts)} receipts", file=sys.stderr)

    # Extract signals
    signals = extract_signals(messages)
    themes = synthesize_themes(signals)

    if args.verbose:
        print(f"  {len(signals['feedback'])} feedback, {len(signals['corrections'])} corrections, {len(signals['redirects'])} redirects", file=sys.stderr)

    if args.json:
        output = {
            "days": args.days,
            "project": args.project,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "signals": signals,
            "themes": themes,
            "topics": topics,
            "hooks_summary": {
                "total": len(hooks),
                "by_hook": dict(Counter(h.get("hook", "unknown") for h in hooks)),
                "by_action": dict(Counter(h.get("action", "unknown") for h in hooks)),
            },
            "receipts_summary": _receipts_summary(receipts),
        }
        json.dump(output, sys.stdout, indent=2)
    else:
        print(format_report(signals, topics, hooks, themes, receipts, args.days))


def _receipts_summary(receipts: list[dict]) -> dict:
    cost_by_project = defaultdict(float)
    commits_by_project = defaultdict(int)
    sessions_by_project = defaultdict(int)
    for r in receipts:
        proj = r.get("project", "unknown") or "unknown"
        cost_by_project[proj] += r.get("cost_usd", r.get("cost", 0))
        commits_by_project[proj] += len(r.get("commits", []))
        sessions_by_project[proj] += 1
    return {
        "cost_by_project": dict(cost_by_project),
        "commits_by_project": dict(commits_by_project),
        "sessions_by_project": dict(sessions_by_project),
    }


if __name__ == "__main__":
    main()
