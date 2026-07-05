"""Single definition of "user-authored text" for raw Claude Code transcripts.

Any miner that parses ~/.claude/projects/*/UUID.jsonl directly (instead of
querying agentlogs.db, where the claude adapter labels these lines as
vendor_kind compact_summary/meta_injected) MUST load this module — never
re-implement the predicate. Re-stated copies diverged 3 ways on 2026-07-05:
extract_user_tags (total false-zero), reflect_capture and blindspot_miner
(compaction re-quotes double-counted). Epistemic principle #9: an invariant
whose inconsistency is a correctness bug gets ONE definition.

Cross-repo consumer: skills/improve/scripts/extract_user_tags.py vendors the
same semantics (different repo, can't import this); the equality is pinned by
scripts/tests/test_transcript_text_drift.py.

Stdlib-only on purpose: blindspot_miner runs inside emb's venv.
"""

from __future__ import annotations


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
