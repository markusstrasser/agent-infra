#!/usr/bin/env python3
"""Thesis Challenge Metric — measures whether agents push back on investment theses.

Scans intel project session transcripts for user investment theses and checks
whether the assistant response includes counterarguments, risk mentions, or
disconfirming evidence.

v1: keyword matching. LLM classification (e.g. Haiku) would be more accurate
but costs money per evaluation. This is directional — "does the agent ever
push back?" not "how good is the pushback?"

Usage:
    uv run python3 scripts/thesis-challenge.py --days 30
    uv run python3 scripts/thesis-challenge.py --session UUID
    uv run python3 scripts/thesis-challenge.py --days 7 --verbose
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import METRICS_FILE, log_metric

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"

# --- Thesis detection ---
# User messages containing these in an intel session are likely investment theses.
THESIS_PATTERNS = [
    r"\bbullish\b",
    r"\bbearish\b",
    r"\bshould buy\b",
    r"\bshould sell\b",
    r"\bgoing long\b",
    r"\bgoing short\b",
    r"\blong on\b",
    r"\bshort on\b",
    r"\bthe thesis is\b",
    r"\bmy thesis\b",
    r"\bmy position\b",
    r"\bi think .{0,40}(?:will|should|going to)\b",
    r"\bi believe .{0,40}(?:will|should|going to)\b",
    r"\bi'm betting\b",
    r"\bundervalued\b",
    r"\bovervalued\b",
    r"\bbuy (?:the|more|some)\b",
    r"\bsell (?:the|my|some)\b",
    r"\baccumulate\b",
    r"\bconviction\b",
    r"\bupside\b",
    r"\bcatalyst\b",
]
THESIS_RE = re.compile("|".join(THESIS_PATTERNS), re.IGNORECASE)

# Ticker symbols: $XXX or standalone 1-5 letter all-caps words
TICKER_RE = re.compile(r"\$[A-Z]{1,5}\b|(?<!\w)[A-Z]{1,5}(?!\w)")

# Common all-caps words that are NOT tickers
NOT_TICKERS = {
    "I", "A", "AN", "THE", "AND", "OR", "BUT", "NOT", "FOR", "IS", "IT",
    "IN", "ON", "AT", "TO", "OF", "BY", "AS", "IF", "SO", "DO", "NO",
    "UP", "BE", "HE", "WE", "MY", "AM", "US", "OK", "AI", "API", "URL",
    "CLI", "SQL", "SSH", "CPU", "GPU", "RAM", "SSD", "HDD", "USB", "PDF",
    "CSV", "JSON", "HTML", "CSS", "HTTP", "MCP", "LLM", "COT", "DAG",
    "ROI", "ETA", "TBD", "WIP", "FYI", "ASAP", "TLDR", "LGTM", "IMO",
    "CEO", "CTO", "CFO", "COO", "VP", "SEC", "IPO", "EDIT", "NOTE",
    "TODO", "DONE", "FAIL", "PASS", "TRUE", "READ", "GREP", "BASH",
    "NULL", "NONE", "TYPE", "TEXT", "FILE", "PATH",
}


# --- Challenge detection ---
# Counterargument indicators in assistant response
COUNTER_PATTERNS = [
    r"\bhowever\b",
    r"\bon the other hand\b",
    r"\brisk(?:s|y)?\b",
    r"\bdownside\b",
    r"\bbear case\b",
    r"\bcontrarian\b",
    r"\bcounterargument\b",
    r"\bagainst this\b",
    r"\bchallenge\b",
    r"\bconcern(?:s)?\b",
    r"\bcaveat(?:s)?\b",
    r"\bbut\b",
    r"\bpush\s*back\b",
    r"\bdevil'?s advocate\b",
]
COUNTER_RE = re.compile("|".join(COUNTER_PATTERNS), re.IGNORECASE)

# Disconfirming evidence
DISCONFIRM_PATTERNS = [
    r"\bcontradicts?\b",
    r"\brefutes?\b",
    r"\bnegative\b",
    r"\bdecline(?:d|s)?\b",
    r"\bloss(?:es)?\b",
    r"\bfailed\b",
    r"\bmissed\b",
    r"\bdisappointing\b",
    r"\bweakness(?:es)?\b",
    r"\bheadwind(?:s)?\b",
    r"\bshortfall\b",
    r"\boverstat(?:e|ed|ing)\b",
]
DISCONFIRM_RE = re.compile("|".join(DISCONFIRM_PATTERNS), re.IGNORECASE)

# Risk mentions
RISK_PATTERNS = [
    r"\brisk(?:s)?\b",
    r"\bvolatility\b",
    r"\bdownside\b",
    r"\bexposure\b",
    r"\bconcentration\b",
    r"\bliquidity\b",
    r"\bleverage\b",
    r"\bdebt\b",
    r"\bdilution\b",
    r"\bregulatory\b",
    r"\blitigation\b",
    r"\bcompetition\b",
    r"\bvaluation\b.*\bstretch",
    r"\bexpensive\b",
    r"\boverpriced\b",
]
RISK_RE = re.compile("|".join(RISK_PATTERNS), re.IGNORECASE)


def extract_text(message: dict) -> str:
    """Extract text content from a message."""
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    texts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block.get("text", ""))
    return "\n".join(texts)


def is_system_injected(text: str) -> bool:
    """Check if text is system-injected content (not genuine user input)."""
    t = text.strip()
    # XML-wrapped system content
    if t.startswith("<"):
        for prefix in (
            "<local-command-caveat>", "<local-command-stdout>",
            "<system-reminder>", "<task-notification>",
            "<available-deferred-tools>", "<command-name>",
            "<role>", "<instructions>",
        ):
            if t.startswith(prefix):
                return True
    # Skill loaders
    if t.startswith("Base directory for this skill:"):
        return True
    # Compaction continuation summaries
    if "This session is being continued from a previous conversation" in t:
        return True
    # Don't-accumulate instructions (system-injected rule reminders)
    if t.startswith("**Don't accumulate"):
        return True
    # Plan implementation instructions
    if t.startswith("Implement the following plan:"):
        return True
    # Pasted content: API keys, file listings, compaction output
    if re.search(r"(?:API.?KEY|api.?key)\s*[=:]", t):
        return True
    if "Compacting conversation" in t:
        return True
    # "You are" role instructions pasted by user
    if t.startswith("You are"):
        return True
    # File listings (ls output — with or without emoji/icon prefixes)
    if re.search(r"r[w-]{2}-r[w-]{2}-r[w-]{2}", t[:100]):
        return True
    # Terms & conditions / cookie banners (pasted web content)
    if "Terms & conditions" in t or "Privacy policy" in t or "Cookie" in t:
        return True
    return False


def is_user_prompt(entry: dict) -> bool:
    """Check if entry is a real user prompt."""
    if entry.get("type") != "user":
        return False
    msg = entry.get("message", {})
    if msg.get("role") != "user":
        return False
    text = extract_text(msg)
    if is_system_injected(text):
        return False
    if len(text.strip()) < 5:
        return False
    return True


def is_assistant_response(entry: dict) -> bool:
    """Check if entry is an assistant text response."""
    if entry.get("type") != "assistant":
        return False
    msg = entry.get("message", {})
    if msg.get("role") != "assistant":
        return False
    text = extract_text(msg)
    return len(text.strip()) > 20


def has_thesis(text: str) -> bool:
    """Check if user message contains an investment thesis.

    Filters out meta/technical messages that happen to contain thesis
    keywords (e.g., "conviction journal", "accumulate totals").
    """
    # Skip messages that are clearly technical/implementation instructions
    if re.search(r"\b(?:event_msg|type=|frontmatter|schema|token_count)\b", text):
        return False
    # Skip messages referencing code constructs
    if re.search(r"`[a-z_]+`.*(?:type|field|column)", text, re.IGNORECASE):
        return False
    # Skip very short messages that can't meaningfully contain a thesis
    if len(text.strip()) < 15:
        return False

    if THESIS_RE.search(text):
        return True
    # Check for ticker symbols (at least one non-common all-caps word)
    caps_words = TICKER_RE.findall(text)
    tickers = [w.lstrip("$") for w in caps_words if w.lstrip("$") not in NOT_TICKERS]
    if tickers and len(text) > 20:
        # Ticker alone isn't a thesis — need some directional language too
        directional = re.search(
            r"\b(?:buy|sell|long|short|up|down|grow|drop|rally|crash|target|worth|fair value)\b",
            text, re.IGNORECASE,
        )
        if directional:
            return True
    return False


def extract_thesis_summary(text: str) -> str:
    """Extract a short summary of the thesis from user text."""
    # Try to find the most thesis-like sentence
    sentences = re.split(r"[.!?\n]", text)
    for s in sentences:
        s = s.strip()
        if THESIS_RE.search(s):
            return s[:120]
    # Fallback: first 120 chars
    return text.strip()[:120]


def has_challenge(text: str) -> dict:
    """Check if assistant response challenges a thesis. Returns detail dict."""
    has_counter = bool(COUNTER_RE.search(text))
    has_disconfirm = bool(DISCONFIRM_RE.search(text))
    has_risk = bool(RISK_RE.search(text))
    challenged = has_counter or has_disconfirm or has_risk
    return {
        "challenged": challenged,
        "has_counterargument": has_counter,
        "has_disconfirming_evidence": has_disconfirm,
        "has_risk_mention": has_risk,
    }


def find_intel_dirs() -> list[Path]:
    """Find project directories that correspond to intel."""
    dirs = []
    if not PROJECTS_DIR.exists():
        return dirs
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir() and d.name.endswith("-intel"):
            dirs.append(d)
    return dirs


def analyze_session(path: Path) -> dict | None:
    """Analyze a single session transcript for thesis challenge rate."""
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (OSError, PermissionError):
        return None

    if not entries:
        return None

    # Verify this is an intel session
    project = None
    session_id = None
    ts = None
    for e in entries:
        if not session_id:
            session_id = e.get("sessionId")
        if not project:
            cwd = e.get("cwd", "")
            if "/Projects/" in cwd:
                project = cwd.split("/Projects/")[-1].split("/")[0]
        if not ts:
            if "timestamp" in e:
                ts = e["timestamp"]

    if project != "intel":
        return None

    # Find thesis→response pairs
    theses = []
    challenged_theses = []
    unchallenged = []

    last_user_thesis = None
    last_user_thesis_text = None

    for entry in entries:
        if is_user_prompt(entry):
            text = extract_text(entry.get("message", {}))
            if has_thesis(text):
                last_user_thesis = extract_thesis_summary(text)
                last_user_thesis_text = text
            else:
                last_user_thesis = None
                last_user_thesis_text = None
            continue

        if last_user_thesis and is_assistant_response(entry):
            text = extract_text(entry.get("message", {}))
            challenge = has_challenge(text)
            theses.append(last_user_thesis)
            if challenge["challenged"]:
                challenged_theses.append(last_user_thesis)
            else:
                unchallenged.append(last_user_thesis)
            last_user_thesis = None
            last_user_thesis_text = None
            continue

        # Don't reset on tool_use-only assistant or tool_result entries
        if entry.get("type") == "user":
            msg = entry.get("message", {})
            if msg.get("role") == "user":
                text = extract_text(msg)
                if not text.startswith("<") and len(text.strip()) >= 5:
                    last_user_thesis = None
                    last_user_thesis_text = None

    if not theses:
        return None

    date_str = None
    if ts:
        try:
            date_str = ts[:10]
        except (TypeError, IndexError):
            pass

    return {
        "session_id": session_id or path.stem,
        "project": "intel",
        "date": date_str,
        "thesis_count": len(theses),
        "challenged_count": len(challenged_theses),
        "challenge_rate": round(len(challenged_theses) / len(theses), 2),
        "unchallenged_theses": unchallenged,
        "file": str(path),
    }


def main():
    days = 30
    session_filter = None
    verbose = False

    args = sys.argv[1:]
    if "--days" in args:
        idx = args.index("--days")
        if idx + 1 < len(args):
            days = int(args[idx + 1])
    if "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            session_filter = args[idx + 1]
    if "--verbose" in args:
        verbose = True

    cutoff = datetime.now() - timedelta(days=days)

    intel_dirs = find_intel_dirs()
    if not intel_dirs:
        print("No intel project directories found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for project_dir in intel_dirs:
        for transcript in project_dir.glob("*.jsonl"):
            mtime = datetime.fromtimestamp(transcript.stat().st_mtime)
            if mtime < cutoff and not session_filter:
                continue

            if session_filter and session_filter not in transcript.stem:
                continue

            result = analyze_session(transcript)
            if result is None:
                continue

            results.append(result)

    # Also scan all project dirs if we have a specific session filter
    if session_filter and not results:
        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            for transcript in project_dir.glob("*.jsonl"):
                if session_filter not in transcript.stem:
                    continue
                result = analyze_session(transcript)
                if result:
                    results.append(result)

    if not results:
        if session_filter:
            print(f"Session {session_filter} not found or not an intel session.", file=sys.stderr)
        else:
            print(f"No intel sessions with theses found in the last {days} days.", file=sys.stderr)
        sys.exit(0)

    # Print per-session JSON to stdout
    results.sort(key=lambda r: r.get("date") or "", reverse=True)
    for r in results:
        print(json.dumps(r))

    # Summary to stderr
    total_sessions = len(results)
    total_theses = sum(r["thesis_count"] for r in results)
    total_challenged = sum(r["challenged_count"] for r in results)
    total_unchallenged = sum(len(r["unchallenged_theses"]) for r in results)
    overall_rate = total_challenged / total_theses if total_theses else 0

    print(file=sys.stderr)
    print(f"{days}-day thesis challenge: {total_sessions} sessions with theses, "
          f"{overall_rate:.0%} challenge rate", file=sys.stderr)
    print(f"Unchallenged theses: {total_unchallenged} "
          f"(review these for bias echo risk)", file=sys.stderr)

    if verbose and total_unchallenged > 0:
        print(file=sys.stderr)
        print("Unchallenged theses (sample):", file=sys.stderr)
        all_unchallenged = [
            (r["session_id"][:8], t)
            for r in results
            for t in r["unchallenged_theses"]
        ]
        for sid, thesis in all_unchallenged[:15]:
            print(f"  [{sid}] {thesis}", file=sys.stderr)
        if len(all_unchallenged) > 15:
            print(f"  ... and {len(all_unchallenged) - 15} more", file=sys.stderr)

    # Log metric
    log_metric(
        "thesis_challenge",
        days=days,
        sessions=total_sessions,
        total_theses=total_theses,
        challenged=total_challenged,
        unchallenged=total_unchallenged,
        challenge_rate=round(overall_rate, 4),
    )
    print(f"\nLogged to {METRICS_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
