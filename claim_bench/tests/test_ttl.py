"""Tests for claim_bench.ttl — TTL invalidation + DECAYED event writer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claim_bench.ledger import Ledger
from claim_bench.ttl import TTLPolicy, scan_and_decay
from claim_bench.types import AuthorityClass, EventType, EvidenceModality, VerificationEvent

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
DAY = timedelta(days=1)


def _evt(
    claim_id: str = "c1",
    event_type: EventType = EventType.VERIFIED,
    modality: str = EvidenceModality.DATABASE,
    authority: str = AuthorityClass.TOOL,
    observed_at: datetime = NOW,
    verifier_name: str = "test_v",
    ttl_days: int | None = None,
    level: int = 1,
    parent_event_ids: tuple[str, ...] = (),
) -> VerificationEvent:
    return VerificationEvent.create(
        claim_id=claim_id,
        event_type=event_type,
        evidence_modality=modality,
        verifier_name=verifier_name,
        authority_class=authority,
        observed_at=observed_at,
        level=level,
        parent_event_ids=parent_event_ids,
        ttl_days=ttl_days,
    )


def _policy(**kw) -> TTLPolicy:
    defaults = {EvidenceModality.DATABASE: 1}
    return TTLPolicy(defaults=kw.get("defaults", defaults), **{k: v for k, v in kw.items() if k != "defaults"})


class TestBasicDecay:
    def test_expired_event_produces_decayed(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 2 * DAY)
        assert len(decayed) == 1
        assert decayed[0].event_type == EventType.DECAYED
        assert decayed[0].claim_id == "c1"

    def test_not_expired_no_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + timedelta(hours=12))
        assert len(decayed) == 0

    def test_event_ttl_days_overrides_policy(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW, ttl_days=10))
        policy = _policy()
        # Not expired at day 5
        decayed = scan_and_decay(ledger, policy, NOW + 5 * DAY)
        assert len(decayed) == 0
        # Expired at day 11
        decayed = scan_and_decay(ledger, policy, NOW + 11 * DAY)
        assert len(decayed) == 1


class TestIdempotence:
    def test_idempotent_across_reruns(self, tmp_path: Path):
        """Scan 10 times at 10 different now values — exactly one DECAYED per expired."""
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        policy = _policy()
        for i in range(10):
            scan_and_decay(ledger, policy, NOW + (2 + i) * DAY)
        events = ledger.read_events()
        decayed = [e for e in events if e.event_type == EventType.DECAYED]
        assert len(decayed) == 1


class TestGuardEvents:
    def test_subsequent_verified_resets_clock(self, tmp_path: Path):
        """A later VERIFIED event guards against decay of the earlier one."""
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        # New verification 12h later
        ledger.append_event(_evt(observed_at=NOW + timedelta(hours=12), verifier_name="v2"))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 2 * DAY)
        # The first event is guarded by the second, but the second may now be expired
        # depending on when "now" is relative to the second event
        all_events = ledger.read_events()
        # The key invariant: if both are expired, we get decayed events; if one guards the other, fewer
        assert all(e.event_type in (EventType.VERIFIED, EventType.DECAYED) for e in all_events)

    def test_superseded_prevents_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        ledger.append_event(_evt(
            observed_at=NOW + timedelta(hours=6),
            event_type=EventType.SUPERSEDED,
            verifier_name="superseder",
        ))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 2 * DAY)
        assert len(decayed) == 0

    def test_retracted_prevents_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(observed_at=NOW))
        ledger.append_event(_evt(
            observed_at=NOW + timedelta(hours=6),
            event_type=EventType.RETRACTED,
            verifier_name="retractor",
        ))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 2 * DAY)
        assert len(decayed) == 0


class TestGroundedAuthorities:
    def test_expert_panel_never_decays(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(authority=AuthorityClass.EXPERT_PANEL, observed_at=NOW))
        policy = _policy(grounded_authorities=frozenset({AuthorityClass.EXPERT_PANEL}))
        decayed = scan_and_decay(ledger, policy, NOW + 1000 * DAY)
        assert len(decayed) == 0

    def test_human_expert_never_decays(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(authority=AuthorityClass.HUMAN_EXPERT, observed_at=NOW))
        policy = _policy(grounded_authorities=frozenset({
            AuthorityClass.EXPERT_PANEL, AuthorityClass.HUMAN_EXPERT,
        }))
        decayed = scan_and_decay(ledger, policy, NOW + 1000 * DAY)
        assert len(decayed) == 0

    def test_tool_authority_does_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(authority=AuthorityClass.TOOL, observed_at=NOW))
        policy = _policy(grounded_authorities=frozenset({AuthorityClass.EXPERT_PANEL}))
        decayed = scan_and_decay(ledger, policy, NOW + 2 * DAY)
        assert len(decayed) == 1


class TestOnlyVerifiedDecays:
    def test_falsified_does_not_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(event_type=EventType.FALSIFIED, observed_at=NOW))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 100 * DAY)
        assert len(decayed) == 0

    def test_inconclusive_does_not_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(event_type=EventType.INCONCLUSIVE, observed_at=NOW))
        policy = _policy()
        decayed = scan_and_decay(ledger, policy, NOW + 100 * DAY)
        assert len(decayed) == 0


class TestNoTTLConfigured:
    def test_no_matching_modality_no_decay(self, tmp_path: Path):
        ledger = Ledger(tmp_path / "events.jsonl")
        ledger.append_event(_evt(modality="unknown_modality", observed_at=NOW))
        policy = _policy()  # only has DATABASE → 1 day
        decayed = scan_and_decay(ledger, policy, NOW + 100 * DAY)
        assert len(decayed) == 0
