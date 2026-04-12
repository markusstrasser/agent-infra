"""Tests for claim_bench.inspect_adapter — Score ↔ VerificationEvent bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from claim_bench.inspect_adapter import event_to_score, score_to_event
from claim_bench.types import AuthorityClass, EventType, EvidenceModality

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)


def _fake_score(value, explanation="", metadata=None):
    return SimpleNamespace(value=value, explanation=explanation, metadata=metadata or {})


class TestScoreToEvent:
    def test_correct_maps_to_verified(self):
        score = _fake_score("C")
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.event_type == EventType.VERIFIED
        assert evt.claim_id == "c1"

    def test_incorrect_maps_to_falsified(self):
        score = _fake_score("I")
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.event_type == EventType.FALSIFIED

    def test_numeric_one_maps_to_verified(self):
        score = _fake_score(1.0)
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.event_type == EventType.VERIFIED

    def test_numeric_zero_maps_to_falsified(self):
        score = _fake_score(0.0)
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.event_type == EventType.FALSIFIED

    def test_other_maps_to_inconclusive(self):
        score = _fake_score("partial")
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.event_type == EventType.INCONCLUSIVE

    def test_explanation_in_payload(self):
        score = _fake_score("C", explanation="Well supported by evidence")
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.payload["explanation"] == "Well supported by evidence"

    def test_metadata_in_payload(self):
        score = _fake_score("C", metadata={"model": "gemini-2.0-flash"})
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        assert evt.payload["score_metadata"]["model"] == "gemini-2.0-flash"


class TestEventToScore:
    def test_verified_roundtrip(self):
        from claim_bench.types import VerificationEvent
        evt = VerificationEvent.create(
            claim_id="c1", event_type=EventType.VERIFIED,
            evidence_modality=EvidenceModality.EMPIRICAL,
            verifier_name="judge_v", authority_class=AuthorityClass.LLM,
            observed_at=NOW, payload={"explanation": "solid"},
        )
        score_dict = event_to_score(evt)
        assert score_dict["value"] == "C"
        assert score_dict["explanation"] == "solid"

    def test_falsified_roundtrip(self):
        from claim_bench.types import VerificationEvent
        evt = VerificationEvent.create(
            claim_id="c1", event_type=EventType.FALSIFIED,
            evidence_modality=EvidenceModality.EMPIRICAL,
            verifier_name="judge_v", authority_class=AuthorityClass.LLM,
            observed_at=NOW,
        )
        score_dict = event_to_score(evt)
        assert score_dict["value"] == "I"

    def test_inconclusive_roundtrip(self):
        from claim_bench.types import VerificationEvent
        evt = VerificationEvent.create(
            claim_id="c1", event_type=EventType.INCONCLUSIVE,
            evidence_modality=EvidenceModality.EMPIRICAL,
            verifier_name="judge_v", authority_class=AuthorityClass.LLM,
            observed_at=NOW,
        )
        score_dict = event_to_score(evt)
        assert score_dict["value"] == "N"

    def test_score_event_content_preserved(self):
        """score → event → score preserves the semantic content."""
        score = _fake_score("C", explanation="good", metadata={"k": "v"})
        evt = score_to_event(
            score, "c1", "judge_v", EvidenceModality.EMPIRICAL,
            AuthorityClass.LLM, NOW,
        )
        score_dict = event_to_score(evt)
        assert score_dict["value"] == "C"
        assert score_dict["explanation"] == "good"
        assert score_dict["metadata"]["k"] == "v"
