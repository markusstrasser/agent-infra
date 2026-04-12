"""DecisionGate protocol for surface-level promotion/blocking decisions.

A DecisionGate reads the event log for a claim and applies a policy predicate
to decide whether the claim should be promoted, blocked, or flagged for review.
Each project implements its own gate with its own policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from claim_bench.ledger import LedgerReader


class Decision(BaseModel):
    """Result of a DecisionGate evaluation."""

    verdict: Literal["promote", "block", "needs_review"]
    rationale: str
    triggering_events: tuple[str, ...] = ()
    review_priority_score: float | None = None


@runtime_checkable
class DecisionGate(Protocol):
    name: str
    surface: str

    def decide(self, claim_id: str, ledger: LedgerReader, now: datetime) -> Decision: ...
