"""Tests for claim_bench.verifier — Verifier protocol + VerifierContext."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from claim_bench.ledger import Ledger, LedgerReader
from claim_bench.types import (
    AuthorityClass,
    ClaimRecord,
    EventType,
    EvidenceModality,
    VerificationEvent,
)
from claim_bench.verifier import Verifier, VerifierContext

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)


class TrivialVerifier:
    """Always returns VERIFIED — protocol satisfaction test."""

    name = "trivial"
    authority_class = AuthorityClass.TOOL
    supported_modalities = frozenset({EvidenceModality.DATABASE})

    def verify(self, claim: ClaimRecord, context: VerifierContext) -> VerificationEvent:
        return VerificationEvent.create(
            claim_id=claim.stable_id,
            event_type=EventType.VERIFIED,
            evidence_modality=EvidenceModality.DATABASE,
            verifier_name=self.name,
            authority_class=self.authority_class,
            observed_at=context.now,
        )


class TestVerifierProtocol:
    def test_trivial_satisfies_protocol(self):
        assert isinstance(TrivialVerifier(), Verifier)

    def test_trivial_returns_event(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "events.jsonl")
        ctx = VerifierContext(ledger=ledger, now=NOW, project="test")
        claim = ClaimRecord(
            stable_id="c1", content_version_hash="h1",
            content={"text": "test"}, created_at=NOW, project="test",
        )
        v = TrivialVerifier()
        evt = v.verify(claim, ctx)
        assert isinstance(evt, VerificationEvent)
        assert evt.event_type == EventType.VERIFIED
        assert evt.claim_id == "c1"
        assert evt.verifier_name == "trivial"

    def test_event_lands_in_ledger(self, tmp_path: Path):
        """Run a claim through verifier, write event to ledger, confirm it's there."""
        ledger = Ledger(tmp_path / "events.jsonl")
        ctx = VerifierContext(ledger=ledger, now=NOW, project="test")
        claim = ClaimRecord(
            stable_id="c1", content_version_hash="h1",
            content={"text": "test"}, created_at=NOW, project="test",
        )
        v = TrivialVerifier()
        evt = v.verify(claim, ctx)
        ledger.append_event(evt)
        events = ledger.read_events(claim_id="c1")
        assert len(events) == 1
        assert events[0].event_id == evt.event_id


class TestVerifierContext:
    def test_context_fields(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "events.jsonl")
        ctx = VerifierContext(ledger=ledger, now=NOW, project="genomics")
        assert ctx.project == "genomics"
        assert ctx.adapter_config == {}

    def test_context_with_config(self, tmp_path: Path):
        ledger = LedgerReader(tmp_path / "events.jsonl")
        ctx = VerifierContext(
            ledger=ledger, now=NOW, project="phenome",
            adapter_config={"self_reports_dir": "/tmp/sr"},
        )
        assert ctx.adapter_config["self_reports_dir"] == "/tmp/sr"
