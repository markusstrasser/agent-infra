"""Single definition of "user-authored text" for raw Claude Code transcripts.

Any miner that parses ~/.claude/projects/*/UUID.jsonl directly (instead of
querying agentlogs.db, where the claude adapter labels these lines as
vendor_kind compact_summary/meta_injected) MUST load this module — never
re-implement the predicate. Re-stated copies diverged 3 ways on 2026-07-05:
extract_user_tags (total false-zero), reflect_capture and blindspot_miner
(compaction re-quotes double-counted). Epistemic principle #9: an invariant
whose inconsistency is a correctness bug gets ONE definition.

Cross-repo consumer: skills/observe/scripts/extract_user_tags.py vendors the
same semantics (different repo, can't import this); the equality is pinned by
scripts/tests/test_transcript_text_drift.py.

Stdlib-only on purpose: blindspot_miner runs inside emb's venv.

is_operator_authored() is the stricter question an instrument asks before it
attributes text to the OPERATOR (corrections, rescues, operator_dx). It is not
part of the vendored/drift-pinned pair above.
"""

from __future__ import annotations

# User-role frames Claude Code writes WITHOUT a harness flag (isMeta /
# isCompactSummary) and without an origin stamp. Measured 2026-09-23 over 489
# transcripts: peer/teammate relays (395 lines), interrupt markers (70),
# local-command stdout (60). Transcripts older than the stamps carry none of
# them, so this screen is also the legacy path.
NON_OPERATOR_PREFIXES = (
    "Another Claude session sent a message",  # peer / teammate relay wrapper
    "<teammate-message",
    "<cross-session-message",
    "<agent-message",
    "<local-command-",  # -stdout / -stderr / -caveat
    "[Request interrupted by user",
    "<task-notification>",
    "<system-reminder>",
    "[SYSTEM NOTIFICATION",
)


def is_harness_injected(obj: dict) -> bool:
    """True for user-typed transcript lines the HARNESS injected.

    Compaction summaries (isCompactSummary) and meta expansions such as skill
    bodies (isMeta) re-quote old user text — #f tags, corrections — and must
    never be mined as fresh user signal.
    """
    return bool(obj.get("isCompactSummary") or obj.get("isMeta"))


def user_texts(obj: dict) -> list[str]:
    """User-authored text blocks of one transcript line, any format; else [].

    Handles the flat legacy shape ({"role":"user","content":...}) and the
    Claude Code envelope ({"type":"user","message":{"role":"user",...}}).
    Content may be a string or a block list; only text blocks count
    (tool_result blocks carry no user-authored feedback).
    """
    if is_harness_injected(obj):
        return []

    inner = obj.get("message")
    if isinstance(inner, dict):
        role = inner.get("role", obj.get("type"))
        content = inner.get("content", "")
    else:
        role = obj.get("role", obj.get("type"))
        content = obj.get("content", "")

    if role != "user":
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
    return []


def is_operator_authored(obj: dict) -> bool:
    """True only when the operator typed this user-role transcript line.

    Evidence, strongest first:
      1. harness flags (isMeta / isCompactSummary) → not operator (via user_texts);
      2. Claude Code's own stamp decides when present: origin.kind == "human"
         (task-notification, peer, auto-continuation → not operator);
      3. headless dispatch → not operator: entrypoint "sdk-*" (`claude -p`) or
         promptSource "sdk"/"system" — the dispatcher wrote that prompt;
      4. harness frames (NON_OPERATOR_PREFIXES) → not operator, stamped or not:
         Claude Code stamps local-command stdout echoes ("Goal set: …",
         "Compacted …") origin.kind == "human" (measured 2026-09-26, arc-agi
         c0549792 and 3 more sessions).
    """
    texts = [t for t in user_texts(obj) if isinstance(t, str) and t.strip()]
    if not texts:
        return False
    origin = obj.get("origin")
    if isinstance(origin, dict) and origin.get("kind"):
        if origin["kind"] != "human":
            return False
    elif str(obj.get("entrypoint") or "").startswith("sdk"):
        return False
    elif obj.get("promptSource") in ("sdk", "system"):
        return False
    head = " ".join(texts).lstrip()
    return not (head.startswith(NON_OPERATOR_PREFIXES) or "<task-notification>" in head[:200])
