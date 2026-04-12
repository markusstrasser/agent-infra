"""Verifier protocol + context for claim verification.

A Verifier reads a claim, does work, and returns a typed VerificationEvent.
Pure function — no mutation. Implementations live in project adapters, not here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from claim_bench.ledger import LedgerReader
from claim_bench.types import ClaimRecord, VerificationEvent


class VerifierContext(BaseModel):
    """Everything a verifier needs from outside the claim itself."""

    ledger: LedgerReader
    now: datetime
    project: str
    adapter_config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


@runtime_checkable
class Verifier(Protocol):
    name: str
    authority_class: str
    supported_modalities: frozenset[str]

    def verify(self, claim: ClaimRecord, context: VerifierContext) -> VerificationEvent: ...
