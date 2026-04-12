"""Core types for cross-project claim verification.

ClaimRecord, VerificationEvent, EventType, EvidenceModality, AuthorityClass.
All types are Pydantic v2 with extra="forbid" and frozen where applicable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    VERIFIED = "verified"
    FALSIFIED = "falsified"
    DECAYED = "decayed"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    INCONCLUSIVE = "inconclusive"


class EvidenceModality:
    """Extensible string constants — adapters may add domain-specific modalities.

    Modality describes HOW a claim was verified, not WHAT KIND of claim it is.
    A single claim may have many verification events with different modality tags.
    """

    DATABASE = "database"
    METHODOLOGICAL = "methodological"
    EMPIRICAL = "empirical"
    COMPUTATIONAL = "computational"
    ASSAY = "assay"
    OBSERVATIONAL = "observational"
    POLICY = "policy"
    EXPERT_CURATED = "expert_curated"


class AuthorityClass:
    """Extensible string constants — projects define their own authority levels.

    Core reserved constants below; adapters add e.g. SELF_REPORTED, MEDICAL_RECORD,
    WEARABLE (phenome), CLINGEN_VCEP (genomics). Adapters MUST supply their own
    authority_rank map to decision gates; core does NOT define ordering.
    """

    EXPERT_PANEL = "expert_panel"
    HUMAN_EXPERT = "human_expert"
    AGGREGATOR = "aggregator"
    TOOL = "tool"
    LLM = "llm"


def _compute_event_id(
    claim_id: str,
    verifier_name: str,
    event_type: EventType,
    evidence_modality: str,
    authority_class: str,
    level: int,
    source_refs: tuple[str, ...],
    parent_event_ids: tuple[str, ...],
    payload: dict[str, Any],
) -> str:
    """Content-hash event identity — NO timestamp, retry-safe."""
    parts = [
        claim_id,
        verifier_name,
        event_type.value if isinstance(event_type, EventType) else event_type,
        evidence_modality,
        authority_class,
        str(level),
        json.dumps(sorted(source_refs), separators=(",", ":")),
        json.dumps(sorted(parent_event_ids), separators=(",", ":")),
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stable_id: str
    content_version_hash: str
    content: dict[str, Any]
    epistemic_class: str = ""
    created_at: datetime
    project: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ClaimRecord:
        return cls.model_validate(d)


class VerificationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    claim_id: str
    event_type: EventType
    evidence_modality: str
    verifier_name: str
    authority_class: str
    observed_at: datetime
    # NB: Gilda & Gilda (arXiv:2601.21116) use L0/L1/L2 for ADI verification
    # stages (different axis); see plan §3 collision note.
    level: Literal[0, 1, 2] = 1
    source_refs: tuple[str, ...] = ()
    parent_event_ids: tuple[str, ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)
    ttl_days: int | None = None

    @classmethod
    def create(
        cls,
        *,
        claim_id: str,
        event_type: EventType,
        evidence_modality: str,
        verifier_name: str,
        authority_class: str,
        observed_at: datetime,
        level: Literal[0, 1, 2] = 1,
        source_refs: tuple[str, ...] = (),
        parent_event_ids: tuple[str, ...] = (),
        payload: dict[str, Any] | None = None,
        ttl_days: int | None = None,
    ) -> VerificationEvent:
        """Factory that computes event_id from content hash."""
        _payload = payload or {}
        eid = _compute_event_id(
            claim_id, verifier_name, event_type, evidence_modality,
            authority_class, level, source_refs, parent_event_ids, _payload,
        )
        return cls(
            event_id=eid,
            claim_id=claim_id,
            event_type=event_type,
            evidence_modality=evidence_modality,
            verifier_name=verifier_name,
            authority_class=authority_class,
            observed_at=observed_at,
            level=level,
            source_refs=source_refs,
            parent_event_ids=parent_event_ids,
            payload=_payload,
            ttl_days=ttl_days,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VerificationEvent:
        return cls.model_validate(d)
