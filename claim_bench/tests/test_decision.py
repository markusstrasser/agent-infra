"""Tests for claim_bench.decision — DecisionGate protocol + Decision model."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from claim_bench.decision import Decision, DecisionGate
from claim_bench.ledger import Ledger, LedgerReader
from claim_bench.types import AuthorityClass, EventType, EvidenceModality, VerificationEvent

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)


class TrivialGate:
    """Promotes if any VERIFIED event exists, blocks otherwise."""

    name = "trivial_gate"
    surface = "test_surface"

    def decide(self, claim_id: str, ledger: LedgerReader, now: datetime) -> Decision:
        events = ledger.read_events(claim_id=claim_id)
        verified = [e for e in events if e.event_type == EventType.VERIFIED]
        if verified:
            return Decision(
                verdict="promote",
                rationale="At least one VERIFIED event exists",
                triggering_events=tuple(e.event_id for e in verified),
            )
        return Decision(verdict="block", rationale="No VERIFIED events found")


def _evt(claim_id: str = "c1", event_type: EventType = EventType.VERIFIED) -> VerificationEvent:
    return VerificationEvent.create(
        claim_id=claim_id,
        event_type=event_type,
        evidence_modality=EvidenceModality.DATABASE,
        verifier_name="test_v",
        authority_class=AuthorityClass.TOOL,
        observed_at=NOW,
    )


class TestDecisionGateProtocol:
    def test_trivial_satisfies_protocol(self):
        assert isinstance(TrivialGate(), DecisionGate)

    def test_promote_on_verified(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt("c1", EventType.VERIFIED))
        gate = TrivialGate()
        d = gate.decide("c1", ledger, NOW)
        assert d.verdict == "promote"
        assert len(d.triggering_events) == 1

    def test_block_on_empty(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        gate = TrivialGate()
        d = gate.decide("c1", ledger, NOW)
        assert d.verdict == "block"

    def test_block_on_falsified_only(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt("c1", EventType.FALSIFIED))
        gate = TrivialGate()
        d = gate.decide("c1", ledger, NOW)
        assert d.verdict == "block"


class TestDecision:
    def test_verdict_values(self):
        for v in ("promote", "block", "needs_review"):
            d = Decision(verdict=v, rationale="test")
            assert d.verdict == v

    def test_review_priority_optional(self):
        d = Decision(verdict="promote", rationale="test")
        assert d.review_priority_score is None

    def test_review_priority_set(self):
        d = Decision(verdict="needs_review", rationale="test", review_priority_score=0.8)
        assert d.review_priority_score == 0.8
