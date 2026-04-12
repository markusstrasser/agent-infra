"""Bridge between inspect_ai Score objects and VerificationEvents.

score_to_event: convert an inspect_ai Score into a VerificationEvent
event_to_score: convert a VerificationEvent back into an inspect_ai Score
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from claim_bench.types import EventType, VerificationEvent


def score_to_event(
    score: Any,
    claim_id: str,
    verifier_name: str,
    evidence_modality: str,
    authority_class: str,
    observed_at: datetime,
    level: int = 1,
) -> VerificationEvent:
    """Convert an inspect_ai Score to a VerificationEvent.

    Maps Score.value to EventType:
    - "C" or 1.0 → VERIFIED
    - "I" or 0.0 → FALSIFIED
    - anything else → INCONCLUSIVE
    """
    val = score.value
    if val in ("C", 1, 1.0, True):
        event_type = EventType.VERIFIED
    elif val in ("I", 0, 0.0, False):
        event_type = EventType.FALSIFIED
    else:
        event_type = EventType.INCONCLUSIVE

    payload: dict[str, Any] = {}
    if hasattr(score, "explanation") and score.explanation:
        payload["explanation"] = score.explanation
    if hasattr(score, "metadata") and score.metadata:
        payload["score_metadata"] = score.metadata

    return VerificationEvent.create(
        claim_id=claim_id,
        event_type=event_type,
        evidence_modality=evidence_modality,
        verifier_name=verifier_name,
        authority_class=authority_class,
        observed_at=observed_at,
        level=level,
        payload=payload,
    )


def event_to_score(event: VerificationEvent) -> Any:
    """Convert a VerificationEvent back to an inspect_ai-compatible Score.

    Returns a dict with value, explanation, metadata — not an actual Score
    object to avoid requiring inspect_ai as an import at call time.
    """
    if event.event_type == EventType.VERIFIED:
        value = "C"
    elif event.event_type == EventType.FALSIFIED:
        value = "I"
    else:
        value = "N"

    return {
        "value": value,
        "explanation": event.payload.get("explanation", ""),
        "metadata": event.payload.get("score_metadata", {}),
    }
