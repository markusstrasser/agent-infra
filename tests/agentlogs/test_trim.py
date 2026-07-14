"""Whole-context text cap: ingest, backfill, and their equivalence."""
from __future__ import annotations

import sqlite3

from agentlogs import trim as tr
from agentlogs.textcap import CAP_CHARS, SENTINEL, cap_text

# Single-token markers, no hyphens: FTS5 reads '-' as an operator, and a long
# run of one char tokenizes as ONE token — either would make the FTS assertions
# pass/fail for reasons unrelated to the cap.
HEAD_MARK = "leadingsystemprompt"
MID_MARK = "middleofthepastedfile"   # sits past HEAD_CHARS, before the kept tail
TAIL_MARK = "trailinginstruction"    # llmx's real instruction lives here
_PAD = "pad " * 3_000                # ~12KB each side

BIG = f"{HEAD_MARK} {_PAD}{MID_MARK} {_PAD}{TAIL_MARK}"


# ---------------------------------------------------------------- cap_text

def test_short_text_is_untouched():
    assert cap_text("hello") == "hello"
    exact = "y" * CAP_CHARS
    assert cap_text(exact) == exact


def test_none_and_empty_survive():
    assert cap_text(None) is None
    assert cap_text("") == ""


def test_cap_keeps_head_and_tail_and_drops_the_middle():
    out = cap_text(BIG)
    assert out.startswith(HEAD_MARK)
    # llmx passes the real instruction as the trailing positional arg — the
    # tail is the forensically load-bearing end.
    assert out.endswith(TAIL_MARK)
    assert MID_MARK not in out, "the pasted-file middle is what we are reclaiming"
    assert SENTINEL in out


def test_cap_never_grows_a_row():
    just_over = "z" * (CAP_CHARS + 1)
    assert len(cap_text(just_over)) <= CAP_CHARS + 1


def test_cap_is_idempotent():
    """A re-run of the backfill must not double-cap. The sentinel is the guard."""
    once = cap_text(BIG)
    assert cap_text(once) == once
    assert once.count(SENTINEL) == 1


# ---------------------------------------------------------------- backfill

def _db() -> sqlite3.Connection:
    """Mirrors the live schema: an EXTERNAL-CONTENT fts5 table (content='events')
    plus all three sync triggers. A contentless table here would corrupt on the
    au-trigger's 'delete' and would be testing a schema we do not run."""
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            kind TEXT,
            vendor_kind TEXT,
            text TEXT
        );
        CREATE VIRTUAL TABLE events_fts USING fts5(
            text, content='events', content_rowid='rowid',
            tokenize='porter unicode61'
        );
        CREATE TRIGGER events_ai AFTER INSERT ON events BEGIN
            INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
        END;
        CREATE TRIGGER events_ad AFTER DELETE ON events BEGIN
            INSERT INTO events_fts(events_fts, rowid, text)
                VALUES('delete', old.rowid, old.text);
        END;
        CREATE TRIGGER events_au AFTER UPDATE ON events BEGIN
            INSERT INTO events_fts(events_fts, rowid, text)
                VALUES('delete', old.rowid, old.text);
            INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
        END;
        """
    )
    return db


def test_backfill_caps_oversized_message_rows():
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'message', ?)", (BIG,))
    db.commit()

    plan = tr.apply_trim(db)

    assert plan.rows == 1
    assert plan.bytes_before == len(BIG)
    assert plan.bytes_after == len(cap_text(BIG))
    assert plan.bytes_saved == len(BIG) - len(cap_text(BIG)) > 0
    got = db.execute("SELECT text FROM events WHERE event_id='e1'").fetchone()[0]
    assert got == cap_text(BIG)


def test_backfill_leaves_genuine_user_text_alone():
    """Real typed text (claude adapter, vendor_kind 'user') is never capped —
    it is 39MB across the whole DB and is the content we actually want."""
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'user', ?)", (BIG,))
    db.commit()

    plan = tr.apply_trim(db)

    assert plan.rows == 0
    assert db.execute("SELECT LENGTH(text) FROM events").fetchone()[0] == len(BIG)


def test_assistant_output_is_never_capped():
    """Model OUTPUT is the work product agentlogs exists to search. Capping it
    would buy 266MB of a 3,367MB reclaim (2026-07-14) and cost the authored
    content — so it is exempt in BOTH paths."""
    from agentlogs.adapters.codex import _parse_response_item
    from agentlogs.adapters.common import ParsedSource

    # backfill path
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'assistant_message', 'message', ?)", (BIG,))
    db.commit()
    plan = tr.apply_trim(db)
    assert plan.rows == 0
    assert db.execute("SELECT LENGTH(text) FROM events").fetchone()[0] == len(BIG)

    # ingest path
    parsed = ParsedSource()
    _parse_response_item(
        parsed,
        {"type": "message", "role": "assistant",
         "content": [{"type": "output_text", "text": BIG}]},
        raw_key="codex:line:1",
        timestamp=None,
        tool_calls={},
        run_id="run-1",
    )
    assert parsed.events[0].text == BIG, "assistant output must reach the DB verbatim"


def test_backfill_is_idempotent():
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'message', ?)", (BIG,))
    db.commit()

    first = tr.apply_trim(db)
    after_first = db.execute("SELECT text FROM events").fetchone()[0]
    second = tr.apply_trim(db)

    assert first.rows == 1
    assert second.rows == 0, "second pass must find no candidates"
    assert db.execute("SELECT text FROM events").fetchone()[0] == after_first


def test_fts_stays_searchable_on_the_kept_tail():
    """The events_au trigger must keep FTS in sync, so the surviving head/tail
    remain searchable — that is what makes the index shrink safely."""
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'message', ?)", (BIG,))  # events_ai fills FTS
    db.commit()

    def hits(token: str) -> int:
        return db.execute(
            "SELECT COUNT(*) FROM events_fts WHERE events_fts MATCH ?", (token,)
        ).fetchone()[0]

    # Guard the guard: all three must be findable BEFORE, or the after-assertions
    # would pass vacuously.
    assert (hits(HEAD_MARK), hits(MID_MARK), hits(TAIL_MARK)) == (1, 1, 1)

    tr.apply_trim(db)

    assert hits(HEAD_MARK) == 1, "head must stay searchable"
    assert hits(TAIL_MARK) == 1, "the surviving tail must stay searchable"
    assert hits(MID_MARK) == 0, "the elided middle must leave the index — that IS the reclaim"


def test_plan_does_not_mutate():
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'message', ?)", (BIG,))
    db.commit()

    plan = tr.plan_trim(db)

    assert plan.rows == 1
    assert db.execute("SELECT LENGTH(text) FROM events").fetchone()[0] == len(BIG)


# ------------------------------------------------- ingest ≡ backfill (crux)

def test_ingest_and_backfill_agree():
    """The load-bearing invariant: a row capped at INGEST and the same row
    capped by the BACKFILL must be byte-identical, or the same prompt renders
    two ways depending on when it was indexed. Both load textcap.cap_text —
    this test is what keeps that true."""
    from agentlogs.adapters.codex import _parse_response_item
    from agentlogs.adapters.common import ParsedSource

    # Through the real adapter code path.
    parsed = ParsedSource()
    _parse_response_item(
        parsed,
        {"type": "message", "role": "user",
         "content": [{"type": "input_text", "text": BIG}]},
        raw_key="codex:line:1",
        timestamp=None,
        tool_calls={},
        run_id="run-1",
    )
    ingested_text = parsed.events[0].text
    assert ingested_text is not None

    # Through the backfill.
    db = _db()
    db.execute("INSERT INTO events VALUES ('e1', 'user_message', 'message', ?)", (BIG,))
    db.commit()
    tr.apply_trim(db)
    backfilled_text = db.execute("SELECT text FROM events").fetchone()[0]

    assert ingested_text == backfilled_text
    assert len(ingested_text) < len(BIG)
