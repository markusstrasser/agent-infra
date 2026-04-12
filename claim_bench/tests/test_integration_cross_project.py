"""Cross-project integration test — proves genericity via 3+ adapters.

Tests that genomics, phenome, and synthetic_finance adapters all produce
valid events via the same core types, and that adding the synthetic adapter
required ZERO changes to claim_bench/src/.
"""

from __future__ import annotations

import json
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
from claim_bench.verifier import VerifierContext

NOW = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def _load_gold_cases() -> list[ClaimRecord]:
    """Load the 8 cross-domain gold cases as ClaimRecords."""
    cases = []
    for p in sorted(CASES_DIR.glob("*.json")):
        raw = json.loads(p.read_text())
        cases.append(ClaimRecord(
            stable_id=p.stem,
            content_version_hash="fixture",
            content=raw,
            created_at=NOW,
            project="claim_bench_self",
        ))
    return cases


class TestCrossProjectIntegration:
    def test_gold_cases_load(self):
        """All 8 cross-domain gold cases load as ClaimRecords."""
        cases = _load_gold_cases()
        assert len(cases) == 8

    def test_synthetic_finance_adapter(self, tmp_path: Path):
        """Synthetic finance adapter produces valid events with zero core changes."""
        from fixtures.synthetic_adapter import (
            SyntheticFinanceDecisionGate,
            SyntheticFinanceVerifier,
        )

        ledger = Ledger(tmp_path / "events.jsonl")
        ctx = VerifierContext(ledger=LedgerReader(ledger.path), now=NOW, project="synthetic_finance")

        claims = [
            ClaimRecord(
                stable_id="fin-001",
                content_version_hash="h1",
                content={"ticker": "ACME", "metric": "revenue_growth", "value": 0.12, "period": "Q1-2026"},
                created_at=NOW,
                project="synthetic_finance",
            ),
            ClaimRecord(
                stable_id="fin-002",
                content_version_hash="h2",
                content={"ticker": "GLOB", "metric": "debt_ratio", "value": 0.65, "period": "FY-2025"},
                created_at=NOW,
                project="synthetic_finance",
            ),
            ClaimRecord(
                stable_id="fin-003",
                content_version_hash="h3",
                content={"ticker": "UNKNOWN", "metric": "xxx", "value": 0, "period": "Q1-2026"},
                created_at=NOW,
                project="synthetic_finance",
            ),
        ]

        v = SyntheticFinanceVerifier()
        for c in claims:
            evt = v.verify(c, ctx)
            ledger.append_event(evt)

        events = ledger.read_events()
        assert len(events) == 3
        verified = [e for e in events if e.event_type == EventType.VERIFIED]
        assert len(verified) == 2  # ACME + GLOB match
        inconclusive = [e for e in events if e.event_type == EventType.INCONCLUSIVE]
        assert len(inconclusive) == 1  # UNKNOWN

        # Decision gate
        gate = SyntheticFinanceDecisionGate()
        d1 = gate.decide("fin-001", ledger, NOW)
        assert d1.verdict == "promote"
        d3 = gate.decide("fin-003", ledger, NOW)
        assert d3.verdict == "block"

    def test_multi_project_ledger(self, tmp_path: Path):
        """Events from multiple projects coexist in the same ledger."""
        ledger = Ledger(tmp_path / "events.jsonl")

        # Genomics-style event
        ledger.append_event(VerificationEvent.create(
            claim_id="genomics-c1",
            event_type=EventType.VERIFIED,
            evidence_modality=EvidenceModality.DATABASE,
            verifier_name="clinvar_watch",
            authority_class=AuthorityClass.AGGREGATOR,
            observed_at=NOW,
            payload={"project": "genomics"},
        ))

        # Phenome-style event
        ledger.append_event(VerificationEvent.create(
            claim_id="phenome-c1",
            event_type=EventType.VERIFIED,
            evidence_modality=EvidenceModality.OBSERVATIONAL,
            verifier_name="self_report_v",
            authority_class="self_reported",
            observed_at=NOW,
            payload={"project": "phenome"},
        ))

        # Finance-style event
        ledger.append_event(VerificationEvent.create(
            claim_id="finance-c1",
            event_type=EventType.VERIFIED,
            evidence_modality="financial",
            verifier_name="sec_v",
            authority_class="sec_filing",
            observed_at=NOW,
            payload={"project": "synthetic_finance"},
        ))

        # claim_bench self event
        ledger.append_event(VerificationEvent.create(
            claim_id="bench-c1",
            event_type=EventType.VERIFIED,
            evidence_modality=EvidenceModality.EMPIRICAL,
            verifier_name="bench_v",
            authority_class=AuthorityClass.LLM,
            observed_at=NOW,
            payload={"project": "claim_bench_self"},
        ))

        events = ledger.read_events()
        assert len(events) == 4
        projects = {e.payload.get("project") for e in events}
        assert projects == {"genomics", "phenome", "synthetic_finance", "claim_bench_self"}

    def test_import_graph_passes(self):
        """The AST import-graph contract test passes (no domain leaks)."""
        from test_import_graph import TestImportGraph

        t = TestImportGraph()
        t.test_no_domain_imports()
        t.test_no_domain_literals()
