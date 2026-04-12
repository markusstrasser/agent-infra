"""Meta-claim level rule — acyclic L0/L1/L2 enforcement.

L0 = external priors (frozen, never evaluated by verifiers)
L1 = object-level claim
L2 = meta-claim about a claim

Invariant: parent_event_ids must all have strictly smaller level.
"""

from __future__ import annotations

from claim_bench.ttl import TTLPolicy
from claim_bench.types import VerificationEvent


def validate_level(event: VerificationEvent, parent_events: list[VerificationEvent]) -> bool:
    """Return True if the event's level is strictly greater than all parents'.

    Raises ValueError if the invariant is violated.
    """
    for parent in parent_events:
        if event.level <= parent.level:
            raise ValueError(
                f"Level invariant violated: event level {event.level} "
                f"<= parent level {parent.level} (parent event_id={parent.event_id})"
            )
    return True


def ground_out_rule(authority_class: str, policy: TTLPolicy) -> bool:
    """Return True if this authority class is grounded (never decays).

    Domain-agnostic — each adapter supplies the grounded_authorities set
    via the TTLPolicy.
    """
    return authority_class in policy.grounded_authorities
