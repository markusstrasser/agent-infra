"""Tests for claim_bench.types — ClaimRecord, VerificationEvent, EventType."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from claim_bench.types import (
    AuthorityClass,
    ClaimRecord,
    EventType,
    EvidenceModality,
    VerificationEvent,
    _compute_event_id,
)

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 4, 11, 13, 0, 0, tzinfo=timezone.utc)


def _make_claim(**overrides) -> ClaimRecord:
    defaults = dict(
        stable_id="claim-001",
        content_version_hash="abc123",
        content={"text": "CRISPR edits DNA"},
        created_at=NOW,
        project="test",
    )
    defaults.update(overrides)
    return ClaimRecord(**defaults)


def _make_event(**overrides) -> VerificationEvent:
    defaults = dict(
        claim_id="claim-001",
        event_type=EventType.VERIFIED,
        evidence_modality=EvidenceModality.DATABASE,
        verifier_name="test_verifier",
        authority_class=AuthorityClass.TOOL,
        observed_at=NOW,
    )
    defaults.update(overrides)
    return VerificationEvent.create(**defaults)


# ─── ClaimRecord ────────────────────────────────────────────────────────────


class TestClaimRecord:
    def test_frozen(self):
        cr = _make_claim()
        with pytest.raises(ValidationError):
            cr.stable_id = "changed"

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            _make_claim(bogus_field="oops")

    def test_roundtrip_dict(self):
        cr = _make_claim()
        d = cr.to_dict()
        cr2 = ClaimRecord.from_dict(d)
        assert cr == cr2

    def test_epistemic_class_default(self):
        cr = _make_claim()
        assert cr.epistemic_class == ""

    def test_epistemic_class_custom(self):
        cr = _make_claim(epistemic_class="pathogenic_variant")
        assert cr.epistemic_class == "pathogenic_variant"


# ─── EventType ──────────────────────────────────────────────────────────────


class TestEventType:
    def test_values(self):
        expected = {"verified", "falsified", "decayed", "superseded", "retracted", "inconclusive"}
        assert {e.value for e in EventType} == expected

    def test_string_enum(self):
        assert EventType.VERIFIED == "verified"
        assert isinstance(EventType.VERIFIED, str)


# ─── EvidenceModality + AuthorityClass ──────────────────────────────────────


class TestExtensibleStrings:
    def test_modality_constants(self):
        assert EvidenceModality.DATABASE == "database"
        assert EvidenceModality.OBSERVATIONAL == "observational"

    def test_authority_constants(self):
        assert AuthorityClass.EXPERT_PANEL == "expert_panel"
        assert AuthorityClass.LLM == "llm"

    def test_extensible_via_plain_string(self):
        """Adapters extend modality/authority via plain strings, no subclassing."""
        evt = _make_event(evidence_modality="financial", authority_class="sec_filing")
        assert evt.evidence_modality == "financial"
        assert evt.authority_class == "sec_filing"


# ─── VerificationEvent ──────────────────────────────────────────────────────


class TestVerificationEvent:
    def test_frozen(self):
        evt = _make_event()
        with pytest.raises(ValidationError):
            evt.claim_id = "changed"

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            VerificationEvent(
                event_id="x", claim_id="c", event_type=EventType.VERIFIED,
                evidence_modality="db", verifier_name="v", authority_class="t",
                observed_at=NOW, unknown_field="oops",
            )

    def test_event_id_determinism_same_day(self):
        """Same semantic event at different times SAME DAY produces same event_id (retry-safe)."""
        evt1 = _make_event(observed_at=NOW)
        evt2 = _make_event(observed_at=LATER)  # same day, different hour
        assert evt1.event_id == evt2.event_id

    def test_event_id_differs_on_different_day(self):
        """Same semantic event on DIFFERENT DAYS produces different event_ids (renewal tracking)."""
        evt1 = _make_event(observed_at=NOW)
        next_day = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)
        evt2 = _make_event(observed_at=next_day)
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_content(self):
        evt1 = _make_event(claim_id="a")
        evt2 = _make_event(claim_id="b")
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_event_type(self):
        evt1 = _make_event(event_type=EventType.VERIFIED)
        evt2 = _make_event(event_type=EventType.FALSIFIED)
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_verifier(self):
        evt1 = _make_event(verifier_name="a")
        evt2 = _make_event(verifier_name="b")
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_modality(self):
        evt1 = _make_event(evidence_modality="database")
        evt2 = _make_event(evidence_modality="empirical")
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_authority(self):
        evt1 = _make_event(authority_class="tool")
        evt2 = _make_event(authority_class="llm")
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_level(self):
        evt1 = _make_event(level=1)
        evt2 = _make_event(level=2)
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_source_refs(self):
        evt1 = _make_event(source_refs=("a",))
        evt2 = _make_event(source_refs=("b",))
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_parent_event_ids(self):
        evt1 = _make_event(parent_event_ids=("p1",))
        evt2 = _make_event(parent_event_ids=("p2",))
        assert evt1.event_id != evt2.event_id

    def test_event_id_differs_on_payload(self):
        evt1 = _make_event(payload={"k": "v1"})
        evt2 = _make_event(payload={"k": "v2"})
        assert evt1.event_id != evt2.event_id

    def test_roundtrip_dict(self):
        evt = _make_event(
            source_refs=("doi:10/xxx",),
            payload={"confidence": 0.95},
            ttl_days=365,
        )
        d = evt.to_dict()
        evt2 = VerificationEvent.from_dict(d)
        assert evt == evt2

    def test_level_default(self):
        evt = _make_event()
        assert evt.level == 1

    def test_level_valid_values(self):
        for lvl in (0, 1, 2):
            evt = _make_event(level=lvl)
            assert evt.level == lvl

    def test_level_3_rejected(self):
        with pytest.raises(ValidationError):
            _make_event(level=3)

    def test_level_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make_event(level=-1)

    def test_ttl_days_optional(self):
        evt = _make_event()
        assert evt.ttl_days is None

    def test_ttl_days_set(self):
        evt = _make_event(ttl_days=365)
        assert evt.ttl_days == 365


# ─── _compute_event_id ──────────────────────────────────────────────────────


class TestComputeEventId:
    def test_deterministic(self):
        args = dict(
            claim_id="c", verifier_name="v", event_type=EventType.VERIFIED,
            evidence_modality="db", authority_class="tool", level=1,
            source_refs=(), parent_event_ids=(), payload={},
        )
        assert _compute_event_id(**args) == _compute_event_id(**args)

    def test_sorted_source_refs(self):
        """Order of source_refs doesn't affect event_id."""
        args = dict(
            claim_id="c", verifier_name="v", event_type=EventType.VERIFIED,
            evidence_modality="db", authority_class="tool", level=1,
            parent_event_ids=(), payload={},
        )
        id1 = _compute_event_id(source_refs=("a", "b"), **args)
        id2 = _compute_event_id(source_refs=("b", "a"), **args)
        assert id1 == id2

    def test_sorted_payload(self):
        """Order of payload keys doesn't affect event_id."""
        args = dict(
            claim_id="c", verifier_name="v", event_type=EventType.VERIFIED,
            evidence_modality="db", authority_class="tool", level=1,
            source_refs=(), parent_event_ids=(),
        )
        id1 = _compute_event_id(payload={"a": 1, "b": 2}, **args)
        id2 = _compute_event_id(payload={"b": 2, "a": 1}, **args)
        assert id1 == id2

    def test_sorted_nested_payload(self):
        """Nested dict key order doesn't affect event_id (Gemini review finding)."""
        args = dict(
            claim_id="c", verifier_name="v", event_type=EventType.VERIFIED,
            evidence_modality="db", authority_class="tool", level=1,
            source_refs=(), parent_event_ids=(),
        )
        id1 = _compute_event_id(payload={"outer": {"z": 1, "a": 2}, "top": "v"}, **args)
        id2 = _compute_event_id(payload={"top": "v", "outer": {"a": 2, "z": 1}}, **args)
        assert id1 == id2
