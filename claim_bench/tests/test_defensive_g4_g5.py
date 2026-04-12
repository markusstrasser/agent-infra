"""Defensive tests G.4 (SAE/SRE alignment) and G.5 (holistic rubric probe).

These tests require LLM judge calls (Gemini Flash) and are informational,
not gating. Run manually with:
    GEMINI_API_KEY=... uv run python3 -m pytest claim_bench/tests/test_defensive_g4_g5.py -v -k "not skip"

G.4: SAE vs SRE decomposition alignment regression (arXiv:2602.10380, Akhter et al. 2026)
G.5: Holistic rubric vs atomic scorer token cost probe (arXiv:2603.28005, Zhang 2026)
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Requires LLM judge calls (Gemini API). Run manually.")
class TestSAEvsSREDecomposition:
    """G.4: Defensive regression test against the Alignment Bottleneck failure mode.

    Setup: pick 3 gold cases with decomposable evidence. For each, author TWO
    evidence configurations:
    - SAE: each sub-claim paired with sub-claim-specific evidence
    - SRE: each sub-claim paired with full claim-level evidence

    Assertion: F1_SAE >= F1_SRE + 0.10 on at least 2 of 3 cases.
    If this fails, the scorer is not sensitive to evidence alignment quality.

    References: arXiv:2602.10380, Akhter et al. 2026, Table 3.
    """

    def test_sae_outperforms_sre(self):
        # This test requires:
        # 1. Hand-authored SAE/SRE evidence configs for 3 gold cases
        # 2. Running atomic_claim_scorer over both configs
        # 3. Comparing F1 scores
        # Deferred to manual execution with Gemini API access.
        pass


@pytest.mark.skip(reason="Requires LLM judge calls (Gemini API). Run manually.")
class TestHolisticRubricBaseline:
    """G.5: Probe test against Rethinking Atomic Decomposition.

    Setup: pick 1 gold case. Run 3 configurations:
    1. Atomic (as-shipped): atomic_claim.py decompose-then-verify pipeline
    2. Matched holistic: single-prompt rubric scoring
    3. Schema-matched ablation: atomic JSON fields but no decomposition

    Assertion (informational): if tokens_atomic < 1.4x tokens_holistic,
    the externally-decomposed pipeline is meaningfully different from the
    single-prompt pattern Zhang critiqued.

    References: arXiv:2603.28005, Zhang 2026, §4.4.
    """

    def test_token_cost_comparison(self):
        # This test requires:
        # 1. Running atomic_claim_scorer on 1 gold case
        # 2. Running a matched holistic prompt on the same case
        # 3. Comparing total tokens
        # Deferred to manual execution with Gemini API access.
        pass
