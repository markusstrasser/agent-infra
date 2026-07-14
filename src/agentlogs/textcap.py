"""Single definition of the whole-context text cap.

Codex/llmx dispatches paste entire files into the prompt (`llmx -f doc.md …`),
and the codex adapter stored each prompt verbatim as event `text`. Measured
2026-07-14: 53,771 `message` rows averaging 50KB = 2.6GB — a third copy of
files that already exist on disk AND in the raw JSONL (archived to
/Volumes/2TBPNY, which stays source of truth per the state-externalization
lens). Genuine typed `user` text across the same DB is 39MB.

We keep the HEAD (system prompt / leading file) and the TAIL — llmx passes the
real instruction as the trailing positional arg, so the tail is the part a
forensic read actually wants — and elide the middle.

INGEST AND BACKFILL MUST CAP IDENTICALLY. If they diverged, a backfilled row
would differ from a freshly-ingested one and the same prompt would render two
ways depending on when it was indexed. Hence one definition, two loaders
(epistemic principle: a shared invariant has ONE definition; consumers load it,
never re-state it).

Reversible: re-index from the raw JSONL restores full text.
"""
from __future__ import annotations

HEAD_CHARS = 4096
TAIL_CHARS = 3072

# WHAT MAY BE CAPPED: only INJECTED CONTEXT — the pasted files and system
# boilerplate that codex echoes back into every dispatch. Assistant messages are
# the model's own OUTPUT, the work product agentlogs exists to search, and are
# never capped: they are 5,442 over-cap rows worth 266MB against 3,101MB for the
# injected kinds (2026-07-14), so exempting them costs 8% of the reclaim and
# keeps 100% of the authored content.
#
# The role form (ingest, pre-DB) and kind form (backfill, post-DB) name the same
# set — kept adjacent so they cannot drift apart.
CAPPED_ROLES = frozenset({"user", "developer"})
CAPPED_KINDS = frozenset({"user_message", "developer_message"})

# Stable substring marking an already-capped row. Load-bearing: it is the
# idempotency sentinel, so a re-run of the backfill cannot double-cap. Never
# reword without a migration.
SENTINEL = "elided by agentlogs text cap"

# Rows at or below this stay verbatim. Head+tail+marker, so capping never
# *grows* a row.
CAP_CHARS = HEAD_CHARS + TAIL_CHARS + 128


def cap_text(text: str | None) -> str | None:
    """Cap a whole-context row to head + marker + tail. Idempotent."""
    if not text or len(text) <= CAP_CHARS:
        return text
    if SENTINEL in text:
        return text
    elided = len(text) - HEAD_CHARS - TAIL_CHARS
    return (
        f"{text[:HEAD_CHARS]}"
        f"\n\n[… {elided:,} chars {SENTINEL}; full text in raw JSONL …]\n\n"
        f"{text[-TAIL_CHARS:]}"
    )
