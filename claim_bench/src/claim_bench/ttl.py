"""TTL invalidation — per-modality decay policy + DECAYED event writer.

TTL is discrete integer days. No continuous decay in this plan.
Grounded authorities (e.g. EXPERT_PANEL, HUMAN_EXPERT) never decay.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_bench.ledger import Ledger
from claim_bench.types import EventType, VerificationEvent


class TTLPolicy(BaseModel):
    """Per-modality TTL defaults + per-verifier overrides + grounded authorities."""

    model_config = ConfigDict(extra="forbid")

    defaults: dict[str, int]  # modality → days
    by_verifier_name: dict[str, int] = {}  # verifier_name → days (overrides modality)
    grounded_authorities: frozenset[str] = frozenset()  # never decay


def _effective_ttl(event: VerificationEvent, policy: TTLPolicy) -> int | None:
    """Resolve the TTL for an event: event.ttl_days > by_verifier_name > defaults."""
    if event.ttl_days is not None:
        return event.ttl_days
    if event.verifier_name in policy.by_verifier_name:
        return policy.by_verifier_name[event.verifier_name]
    return policy.defaults.get(event.evidence_modality)


_TERMINAL_TYPES = frozenset({
    EventType.VERIFIED,
    EventType.FALSIFIED,
    EventType.DECAYED,
    EventType.SUPERSEDED,
    EventType.RETRACTED,
})


def scan_and_decay(ledger: Ledger, policy: TTLPolicy, now: datetime) -> list[VerificationEvent]:
    """Scan ledger and append DECAYED events for expired VERIFIED events.

    Rules:
    - Only VERIFIED events can decay.
    - Grounded authorities never decay.
    - A VERIFIED event is expired if now > observed_at + ttl_days.
    - A VERIFIED event is guarded if a later VERIFIED/FALSIFIED/DECAYED/
      SUPERSEDED/RETRACTED event exists for the same claim.
    - Dedup is automatic via event_id content hash — re-runs are idempotent.

    Returns the list of newly appended DECAYED events.
    """
    all_events = ledger.read_events()
    decayed: list[VerificationEvent] = []

    # Group events by claim_id
    by_claim: dict[str, list[VerificationEvent]] = {}
    for evt in all_events:
        by_claim.setdefault(evt.claim_id, []).append(evt)

    for claim_id, events in by_claim.items():
        # Sort by observed_at for temporal ordering
        events.sort(key=lambda e: e.observed_at)

        for evt in events:
            if evt.event_type != EventType.VERIFIED:
                continue

            # Grounded authorities never decay
            if evt.authority_class in policy.grounded_authorities:
                continue

            ttl = _effective_ttl(evt, policy)
            if ttl is None:
                continue

            expiry = evt.observed_at + timedelta(days=ttl)
            if now <= expiry:
                continue

            # Check for a guarding event after this one
            has_guard = any(
                later.event_type in _TERMINAL_TYPES
                and later.observed_at > evt.observed_at
                and later.event_id != evt.event_id
                for later in events
            )
            if has_guard:
                continue

            # Create DECAYED event
            decay_evt = VerificationEvent.create(
                claim_id=claim_id,
                event_type=EventType.DECAYED,
                evidence_modality=evt.evidence_modality,
                verifier_name=evt.verifier_name,
                authority_class=evt.authority_class,
                observed_at=now,
                level=evt.level,
                parent_event_ids=(evt.event_id,),
                payload={"decayed_event_id": evt.event_id, "ttl_days": ttl},
            )
            if ledger.append_event(decay_evt):
                decayed.append(decay_evt)

    return decayed
