"""Tests for claim_bench.meta_claim — level invariant + grounding rule."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from claim_bench.meta_claim import ground_out_rule, validate_level
from claim_bench.ttl import TTLPolicy
from claim_bench.types import AuthorityClass, EventType, EvidenceModality, VerificationEvent

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)


def _evt(level: int = 1, event_id_seed: str = "a", **kw) -> VerificationEvent:
    defaults = dict(
        claim_id="c1",
        event_type=EventType.VERIFIED,
        evidence_modality=EvidenceModality.DATABASE,
        verifier_name=f"v_{event_id_seed}",
        authority_class=AuthorityClass.TOOL,
        observed_at=NOW,
        level=level,
    )
    defaults.update(kw)
    return VerificationEvent.create(**defaults)


class TestValidateLevel:
    def test_l2_with_l1_parent_accepted(self):
        parent = _evt(level=1, event_id_seed="parent")
        event = _evt(level=2, event_id_seed="child", parent_event_ids=(parent.event_id,))
        assert validate_level(event, [parent]) is True

    def test_l1_with_l0_parent_accepted(self):
        parent = _evt(level=0, event_id_seed="parent")
        event = _evt(level=1, event_id_seed="child", parent_event_ids=(parent.event_id,))
        assert validate_level(event, [parent]) is True

    def test_l1_with_l1_parent_rejected(self):
        parent = _evt(level=1, event_id_seed="parent")
        event = _evt(level=1, event_id_seed="child", parent_event_ids=(parent.event_id,))
        with pytest.raises(ValueError, match="Level invariant violated"):
            validate_level(event, [parent])

    def test_l2_with_l2_parent_rejected(self):
        parent = _evt(level=2, event_id_seed="parent")
        event = _evt(level=2, event_id_seed="child", parent_event_ids=(parent.event_id,))
        with pytest.raises(ValueError, match="Level invariant violated"):
            validate_level(event, [parent])

    def test_l0_with_any_parent_rejected(self):
        parent = _evt(level=0, event_id_seed="parent")
        event = _evt(level=0, event_id_seed="child", parent_event_ids=(parent.event_id,))
        with pytest.raises(ValueError, match="Level invariant violated"):
            validate_level(event, [parent])

    def test_no_parents_accepted(self):
        event = _evt(level=1)
        assert validate_level(event, []) is True

    def test_multiple_parents_all_lower(self):
        p0 = _evt(level=0, event_id_seed="p0")
        p1 = _evt(level=1, event_id_seed="p1")
        event = _evt(level=2, event_id_seed="child", parent_event_ids=(p0.event_id, p1.event_id))
        assert validate_level(event, [p0, p1]) is True

    def test_multiple_parents_one_same_level(self):
        p1a = _evt(level=1, event_id_seed="p1a")
        p1b = _evt(level=1, event_id_seed="p1b")
        event = _evt(level=1, event_id_seed="child", parent_event_ids=(p1a.event_id, p1b.event_id))
        with pytest.raises(ValueError):
            validate_level(event, [p1a, p1b])


class TestGroundOutRule:
    def test_expert_panel_grounded(self):
        policy = TTLPolicy(
            defaults={}, grounded_authorities=frozenset({AuthorityClass.EXPERT_PANEL}),
        )
        assert ground_out_rule(AuthorityClass.EXPERT_PANEL, policy) is True

    def test_human_expert_grounded(self):
        policy = TTLPolicy(
            defaults={},
            grounded_authorities=frozenset({AuthorityClass.EXPERT_PANEL, AuthorityClass.HUMAN_EXPERT}),
        )
        assert ground_out_rule(AuthorityClass.HUMAN_EXPERT, policy) is True

    def test_tool_not_grounded(self):
        policy = TTLPolicy(
            defaults={}, grounded_authorities=frozenset({AuthorityClass.EXPERT_PANEL}),
        )
        assert ground_out_rule(AuthorityClass.TOOL, policy) is False

    def test_llm_not_grounded(self):
        policy = TTLPolicy(defaults={}, grounded_authorities=frozenset())
        assert ground_out_rule(AuthorityClass.LLM, policy) is False

    def test_l0_priors_grounding(self):
        """L0 external priors are grounded when HUMAN_EXPERT is in grounded set."""
        policy = TTLPolicy(
            defaults={},
            grounded_authorities=frozenset({AuthorityClass.HUMAN_EXPERT}),
        )
        assert ground_out_rule(AuthorityClass.HUMAN_EXPERT, policy) is True
