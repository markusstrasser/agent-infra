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
part of the vendored/drift-pinned pair above; its rule is
src/agentlogs/authorship.py, loaded by path only when it is called.
"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

# The operator-authorship rule lives in agentlogs, where the Claude adapter labels
# events with it. Loaded by path (it is stdlib-only with no package imports), so
# this module keeps working in any venv and never reads a stale installed copy.
_AUTHORSHIP = Path(__file__).resolve().parents[2] / "src" / "agentlogs" / "authorship.py"


@lru_cache(maxsize=1)
def _authorship():
    spec = importlib.util.spec_from_file_location("agentlogs_authorship", _AUTHORSHIP)
    if spec is None or spec.loader is None:
        raise ImportError(f"agentlogs authorship rule not found at {_AUTHORSHIP}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    Harness flags (isMeta / isCompactSummary) screen first, via user_texts; the
    rest is agentlogs.authorship.claude_line_author: the origin stamp, then
    dispatch stamps (entrypoint sdk-*, promptSource sdk/system), then harness
    frames such as task notifications, peer relays and local-command echoes.
    """
    texts = [t for t in user_texts(obj) if isinstance(t, str) and t.strip()]
    if not texts:
        return False
    return _authorship().claude_line_author(obj, " ".join(texts)) == "operator"
