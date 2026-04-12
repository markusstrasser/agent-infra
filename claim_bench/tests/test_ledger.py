"""Tests for claim_bench.ledger — append-only JSONL event ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claim_bench.ledger import Ledger, LedgerReader
from claim_bench.types import AuthorityClass, EventType, EvidenceModality, VerificationEvent

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=1)
MUCH_LATER = NOW + timedelta(days=1)


def _evt(
    claim_id: str = "c1",
    event_type: EventType = EventType.VERIFIED,
    verifier_name: str = "test_v",
    observed_at: datetime = NOW,
    **kw,
) -> VerificationEvent:
    defaults = dict(
        claim_id=claim_id,
        event_type=event_type,
        evidence_modality=EvidenceModality.DATABASE,
        verifier_name=verifier_name,
        authority_class=AuthorityClass.TOOL,
        observed_at=observed_at,
    )
    defaults.update(kw)
    return VerificationEvent.create(**defaults)


# ─── Append + Read ──────────────────────────────────────────────────────────


class TestAppendAndRead:
    def test_append_and_read_roundtrip(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        evt = _evt()
        assert ledger.append_event(evt) is True
        events = ledger.read_events()
        assert len(events) == 1
        assert events[0] == evt

    def test_ordering_preserved(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        e1 = _evt(claim_id="c1", observed_at=NOW)
        e2 = _evt(claim_id="c2", observed_at=LATER)
        ledger.append_event(e1)
        ledger.append_event(e2)
        events = ledger.read_events()
        assert events[0].claim_id == "c1"
        assert events[1].claim_id == "c2"

    def test_empty_ledger_returns_empty(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "nonexistent.jsonl")
        assert ledger.read_events() == []

    def test_dedup_same_event(self, tmp_path: Path):
        """Appending the same semantic event twice produces exactly one row."""
        ledger = Ledger(tmp_path / "events.jsonl")
        evt = _evt()
        assert ledger.append_event(evt) is True
        assert ledger.append_event(evt) is False
        assert len(ledger.read_events()) == 1

    def test_dedup_same_event_different_observed_at(self, tmp_path: Path):
        """Same semantic content at different times dedup'd (retry-safety)."""
        ledger = Ledger(tmp_path / "events.jsonl")
        e1 = _evt(observed_at=NOW)
        e2 = _evt(observed_at=LATER)
        assert e1.event_id == e2.event_id
        assert ledger.append_event(e1) is True
        assert ledger.append_event(e2) is False
        assert len(ledger.read_events()) == 1

    def test_different_events_both_stored(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        e1 = _evt(claim_id="a")
        e2 = _evt(claim_id="b")
        ledger.append_event(e1)
        ledger.append_event(e2)
        assert len(ledger.read_events()) == 2


# ─── Filtering ──────────────────────────────────────────────────────────────


class TestFiltering:
    def test_filter_by_claim_id(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(claim_id="a"))
        ledger.append_event(_evt(claim_id="b"))
        events = ledger.read_events(claim_id="a")
        assert len(events) == 1
        assert events[0].claim_id == "a"

    def test_filter_by_since(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        e1 = _evt(claim_id="a", observed_at=NOW)
        e2 = _evt(claim_id="b", observed_at=MUCH_LATER)
        ledger.append_event(e1)
        ledger.append_event(e2)
        events = ledger.read_events(since=LATER)
        assert len(events) == 1
        assert events[0].claim_id == "b"

    def test_filter_combined(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(claim_id="a", observed_at=NOW))
        ledger.append_event(_evt(claim_id="a", observed_at=MUCH_LATER, verifier_name="v2"))
        ledger.append_event(_evt(claim_id="b", observed_at=MUCH_LATER))
        events = ledger.read_events(claim_id="a", since=LATER)
        assert len(events) == 1


# ─── event_exists / all_event_ids ───────────────────────────────────────────


class TestEventExists:
    def test_exists(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        evt = _evt()
        ledger.append_event(evt)
        assert ledger.event_exists(evt.event_id) is True

    def test_not_exists(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        assert ledger.event_exists("nonexistent") is False

    def test_not_exists_no_file(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "nope.jsonl")
        assert ledger.event_exists("x") is False

    def test_all_event_ids(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        e1 = _evt(claim_id="a")
        e2 = _evt(claim_id="b")
        ledger.append_event(e1)
        ledger.append_event(e2)
        assert ledger.all_event_ids() == {e1.event_id, e2.event_id}

    def test_all_event_ids_empty(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "nonexistent.jsonl")
        assert ledger.all_event_ids() == set()


# ─── File creation ──────────────────────────────────────────────────────────


class TestFileCreation:
    def test_creates_parent_dirs(self, tmp_path: Path):
        p = tmp_path / "sub" / "dir" / "events.jsonl"
        ledger = Ledger(p)
        ledger.append_event(_evt())
        assert p.exists()
