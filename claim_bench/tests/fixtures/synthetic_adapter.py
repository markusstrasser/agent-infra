"""Synthetic third adapter — fictional finance domain.

Purpose: if the core has to change to accommodate this adapter,
the core is leaking genomics/phenome assumptions.
"""

from __future__ import annotations

from datetime import datetime

from claim_bench.decision import Decision
from claim_bench.ledger import LedgerReader
from claim_bench.types import ClaimRecord, EventType, EvidenceModality, VerificationEvent
from claim_bench.verifier import VerifierContext

# Domain-specific authority classes (plain strings)
INSIDER_REPORT = "insider_report"
SEC_FILING = "sec_filing"
ANALYST_CONSENSUS = "analyst_consensus"

# Domain-specific evidence modalities
FINANCIAL = "financial"
LEGAL_FILING = "legal_filing"

# Synthetic corpus
SYNTHETIC_CORPUS = [
    {"ticker": "ACME", "metric": "revenue_growth", "value": 0.12, "period": "Q1-2026"},
    {"ticker": "ACME", "metric": "eps", "value": 2.45, "period": "Q1-2026"},
    {"ticker": "GLOB", "metric": "debt_ratio", "value": 0.65, "period": "FY-2025"},
    {"ticker": "GLOB", "metric": "market_cap_b", "value": 150.3, "period": "2026-04"},
    {"ticker": "TINY", "metric": "burn_rate_months", "value": 8.0, "period": "Q1-2026"},
]


class SyntheticFinanceVerifier:
    """Matches claims against the synthetic corpus by ticker+metric."""

    name = "synthetic_finance_verifier"
    authority_class = SEC_FILING
    supported_modalities = frozenset({FINANCIAL})

    def verify(self, claim: ClaimRecord, context: VerifierContext) -> VerificationEvent:
        corpus = SYNTHETIC_CORPUS
        ticker = claim.content.get("ticker")
        metric = claim.content.get("metric")

        for entry in corpus:
            if entry["ticker"] == ticker and entry["metric"] == metric:
                return VerificationEvent.create(
                    claim_id=claim.stable_id,
                    event_type=EventType.VERIFIED,
                    evidence_modality=FINANCIAL,
                    verifier_name=self.name,
                    authority_class=self.authority_class,
                    observed_at=context.now,
                    payload={"matched_entry": entry},
                )

        return VerificationEvent.create(
            claim_id=claim.stable_id,
            event_type=EventType.INCONCLUSIVE,
            evidence_modality=FINANCIAL,
            verifier_name=self.name,
            authority_class=self.authority_class,
            observed_at=context.now,
        )


class SyntheticFinanceDecisionGate:
    """Promotes if SEC_FILING or ANALYST_CONSENSUS VERIFIED event exists."""

    name = "synthetic_finance_gate"
    surface = "finance_report"

    _REQUIRED_AUTHORITIES = frozenset({SEC_FILING, ANALYST_CONSENSUS})

    def decide(self, claim_id: str, ledger: LedgerReader, now: datetime) -> Decision:
        events = ledger.read_events(claim_id=claim_id)
        verified = [
            e for e in events
            if e.event_type == EventType.VERIFIED
            and e.authority_class in self._REQUIRED_AUTHORITIES
        ]
        if verified:
            return Decision(
                verdict="promote",
                rationale=f"Verified by {verified[0].authority_class}",
                triggering_events=(verified[0].event_id,),
            )
        return Decision(verdict="block", rationale="No SEC_FILING/ANALYST_CONSENSUS verification")
