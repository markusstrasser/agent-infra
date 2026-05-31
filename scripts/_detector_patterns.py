"""Vendored regex pattern banks for deterministic session-quality detectors.

Provenance (pattern strings reused under permissive licenses):
  - pisama-detectors (Apache-2.0): WRAPUP_PATTERNS, COMPLETION_CLAIM_PATTERNS,
    INCOMPLETE_PATTERNS, PLANNED_WORK_PATTERNS, BLOCKER_PATTERNS,
    HONEST_PARTIAL_PATTERNS, NUMERIC_RATIO_PATTERNS, EXPLICIT_FAILURE_PATTERNS.
    https://github.com/Pisama-AI/pisama-detectors  (detection/{context_pressure,completion}.py)
  - agent-xray (MIT): RATE_LIMIT_RE.
    https://github.com/GeeIHadAGoodTime/Agent-Xray  (root_cause.py)

Why vendored, not depended-on: pisama drags sentence-transformers/sklearn/tiktoken
for detectors we don't use; the patterns we want are pure-stdlib regex. See
.scratch/deepdive-taxonomies.md for the full port analysis. These banks are a
KNOWN maintenance surface — frontier-model vocabulary drifts, so they are gated
behind a golden-session regression test (tests/test_session_detectors.py) and the
detectors that use them emit ADVISORY features only (not folded into the quality
score until calibrated). TRAIL benchmark backing: deterministic detectors scored
precision=1.0 / lower recall on these categories (high-precision/low-recall).
"""
from __future__ import annotations

import re

# --- Context-pressure: premature wrap-up language (last 40% of turns) ---------
# 12 patterns, from pisama context_pressure.py:67-80 (Anthropic-blog-motivated).
WRAPUP_PATTERNS: list[tuple[str, str]] = [
    (r"\bI'?ll leave (?:that|this|the rest)\b", "premature_leave"),
    (r"\bthis should be sufficient\b", "sufficiency_claim"),
    (r"\bwrapping up\b", "explicit_wrapup"),
    (r"\bfor brevity\b", "brevity_excuse"),
    (r"\bI'?ll skip\b", "explicit_skip"),
    (r"\bleaving (?:that|this|the rest) for\b", "deferred_work"),
    (r"\bfor now\b.*\b(?:move on|proceed|continue)\b", "deferred_continuation"),
    (r"\blet me (?:quickly|briefly) (?:summarize|wrap|finish)\b", "rushed_conclusion"),
    (r"\bI'?ll (?:just )?note that\b.*\binstead of\b", "shortcut_acknowledgment"),
    (r"\bdue to (?:space|length|context) (?:constraints|limitations)\b", "explicit_constraint"),
    (r"\bI'?ve covered the (?:key|main|essential) (?:points|parts)\b", "selective_coverage"),
    (r"\bthe remaining (?:items|tasks|points) (?:are|can be) (?:similar|straightforward)\b", "assumed_trivial"),
]

# --- Completion claims (final assistant message) ------------------------------
COMPLETION_CLAIM_PATTERNS: list[str] = [
    r'\b(?:task|work|job)\s+(?:is\s+)?(?:complete|completed|done|finished)\b',
    r'\b(?:i have|i\'ve)\s+(?:completed|finished|done)\b',
    r'\bsuccessfully\s+(?:completed|finished|done)\b',
    r'\b(?:all\s+)?(?:tasks?|steps?|items?)\s+(?:are\s+)?(?:complete|done)\b',
    r'\b(?:mission\s+accomplished|job\s+done)\b',
    r'\bhere(?:\'s| is)\s+the\s+(?:final|completed|finished)\b',
    r'\b(?:that\'s|this\s+is)\s+everything\b',
    r'\bnothing\s+(?:else|more)\s+(?:to\s+do|needed|required)\b',
    r'\b(?:migration|implementation|setup|integration|feature|system|module|service|component|api|app|application|build|deployment|test|testing|code|refactor|fix|update|upgrade)\s+(?:is\s+)?(?:complete|completed|done|ready|finished|implemented|working|set up|configured|live)\b',
    r'\b(?:done|complete|completed|ready|finished|implemented)\s*[!.]',
]

# --- Incomplete-work markers --------------------------------------------------
INCOMPLETE_PATTERNS: list[tuple[str, str]] = [
    (r'\bTODO\b', "todo_marker"),
    (r'\bFIXME\b', "fixme_marker"),
    (r'\bHACK\b', "hack_marker"),
    (r'\bXXX\b', "xxx_marker"),
    (r'\b(?:not\s+yet|still\s+need|remaining|pending)\b', "pending_marker"),
    (r'\b(?:placeholder|stub|dummy|mock)\b', "placeholder"),
    (r'\b(?:will\s+be|to\s+be)\s+(?:implemented|added|done)\b', "future_work"),
    (r'\b(?:partial|incomplete|unfinished)\b', "explicit_incomplete"),
]

# --- Planned/deferred future work --------------------------------------------
PLANNED_WORK_PATTERNS: list[tuple[str, str]] = [
    (r'\b(?:coverage|tests?|testing)\s+planned\b', "planned_tests"),
    (r'\bwill\s+(?:be\s+)?(?:added|implemented|included|covered|optimized?|fixed|handled|addressed|resolved|completed|deployed|integrated|tested|updated|refactored)\b', "future_work"),
    (r"\b(?:i'll|we'll|i\s+will|we\s+will)\s+(?:add|implement|include|cover|optimize|fix|handle|address|resolve|complete|deploy|integrate|test|update|refactor)\b", "future_work"),
    (r'\b(?:next|later|future)\s+(?:phase|step|iteration|sprint|release|version)\b', "deferred_work"),
    (r'\b(?:backlog|follow[- ]up|roadmap|post[- ]launch|post[- ]release)\b', "deferred_work"),
]

# --- Blocker / external-dependency phrases ------------------------------------
BLOCKER_PATTERNS: list[tuple[str, str]] = [
    (r'\b(?:opened|filed|raised|created)\s+(?:a\s+)?(?:ticket|issue|request)\b', "blocker_ticket"),
    (r'\bneeds?\s+(?:IT|admin|ops|devops|manager|team|approval)\b', "blocker_approval"),
    (r'\b(?:waiting|blocked)\s+(?:for|on)\b', "blocker_waiting"),
    (r'\b(?:couldn\'t|could\s+not|unable\s+to)\s+(?:finish|complete)\b', "blocker_unable"),
]

# --- Honest-partial phrases (FALSE-POSITIVE SUPPRESSORS) ----------------------
# When present, the agent is honestly acknowledging incompleteness -> NOT a
# premature-completion misjudgment. These SUPPRESS the D2 flag.
HONEST_PARTIAL_PATTERNS: list[str] = [
    r'\bpartially done\b',
    r'\b\w+\s+complete,?\s+\w+\s+remaining\b',
    r'\bcompleted\s+\d+\s+of\s+\d+\b',
    r'\bstill working on\b',
    r'\bin progress\b',
    r'\bnot yet (?:complete|finished|done)\b',
    r'\bwork in progress\b',
    r'\bremaining tasks?\b',
    r'\b\d+\s+(?:tasks?|items?)\s+left\b',
]

# --- Explicit failure admissions (strong standalone signal) -------------------
EXPLICIT_FAILURE_PATTERNS: list[str] = [
    r'\bagent\s+failed\b',
    r'\b(?:did\s+not|didn\'t)\s+(?:complete|finish|succeed|manage)\b',
    r'\b(?:was\s+)?unable\s+to\s+(?:complete|finish|resolve)\b',
    r'\btask\s+(?:has\s+)?(?:failed|not\s+completed|incomplete|unfinished)\b',
    r'\bfailed\s+(?:repeatedly|multiple\s+times)\b',
]

# --- Numeric ratio (e.g. "8/10", "8 of 10") -----------------------------------
# OVERLOADED per critique ("7/10 files touched" != incompleteness). Used as
# evidence-only, never a standalone flag.
NUMERIC_RATIO_PATTERNS: list[tuple[str, str]] = [
    (r'(?<![\d,])(\d+)\s*/\s*(?<![\d,])(\d+)(?![\d,])', "explicit_ratio"),
    (r'(?<![\d,])(\d+)\s+(?:of|out of)\s+(?<![\d,])(\d+)(?![\d,])', "explicit_count"),
]

# --- Rate-limit cascade (agent-xray) ------------------------------------------
RATE_LIMIT_RE = re.compile(r"\b(?:429|rate limit|too many requests)\b", re.IGNORECASE)


# --- Context limits by model family (frontier, 2026-05) -----------------------
# Ordered longest-prefix-first; resolve_context_limit returns None on no match
# so callers can flag `missing_prerequisites` rather than silently defaulting
# (per cross-model critique: unmatched models must be REPORTED, not guessed).
DEFAULT_CONTEXT_LIMITS: list[tuple[str, int]] = [
    ("claude-opus-4-8[1m]", 1_000_000),
    ("claude-sonnet-4-6", 1_000_000),
    ("claude-opus-4-8", 200_000),
    ("claude-opus-4", 200_000),
    ("claude-sonnet-4", 1_000_000),
    ("claude-haiku-4", 200_000),
    ("claude-3", 200_000),
    ("gemini-3", 1_000_000),
    ("gemini-2", 1_000_000),
    ("gpt-5", 400_000),
    ("gpt-4", 128_000),
]


def resolve_context_limit(model: str | None) -> int | None:
    """Return the context window for a model string, or None if unknown.

    None is deliberate: the caller emits `missing_prerequisites` instead of a
    bogus utilization number (cross-model critique requirement).
    """
    if not model:
        return None
    m = model.lower()
    for prefix, limit in DEFAULT_CONTEXT_LIMITS:
        if m.startswith(prefix.lower()):
            return limit
    return None


def _compile(patterns):
    """Compile a bank of bare patterns or (pattern, label) tuples."""
    out = []
    for p in patterns:
        if isinstance(p, tuple):
            out.append((re.compile(p[0], re.IGNORECASE), p[1]))
        else:
            out.append((re.compile(p, re.IGNORECASE), None))
    return out


# Pre-compiled banks (compile once at import).
WRAPUP_COMPILED = _compile(WRAPUP_PATTERNS)
COMPLETION_CLAIM_COMPILED = _compile(COMPLETION_CLAIM_PATTERNS)
INCOMPLETE_COMPILED = _compile(INCOMPLETE_PATTERNS)
PLANNED_WORK_COMPILED = _compile(PLANNED_WORK_PATTERNS)
BLOCKER_COMPILED = _compile(BLOCKER_PATTERNS)
HONEST_PARTIAL_COMPILED = _compile(HONEST_PARTIAL_PATTERNS)
EXPLICIT_FAILURE_COMPILED = _compile(EXPLICIT_FAILURE_PATTERNS)
NUMERIC_RATIO_COMPILED = _compile(NUMERIC_RATIO_PATTERNS)
