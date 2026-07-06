"""Verifier-lane regression guards for debug_until_dry.

Covers the 2026-07-03 silent-swallow bug: `if ok:` with no else discarded the
verifier body, so a broken output contract read as "nothing to refute". Two guards:
(a) round-trip — verbatim REFUTED blocks still land verdicts through the harness;
(b) the swallow-guard emits an observable diagnostic on an empty/prose body.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from debug_until_dry import (  # noqa: E402
    Finding,
    apply_verdicts,
    claim_hash,
    parse_wave_output,
    verifier_diagnostic,
)


def _memo(*claims: str) -> dict[str, Finding]:
    return {
        claim_hash(c): Finding(dedupe=claim_hash(c), claim=c, status="unverified") for c in claims
    }


def test_verbatim_refuted_blocks_round_trip():
    claim_a = "The `foo()` guard at bar.py:42 double-frees the buffer."
    claim_b = "Wave counter off-by-one in loop.py:88 skips the last item."
    memo = _memo(claim_a, claim_b)
    body = (
        "## FINDING\n"
        f"- **Claim:** {claim_a}\n"
        "- **Evidence:** bar.py:42 — reproduced, no double free\n"
        "- **Verdict:** REFUTED\n\n"
        "## FINDING\n"
        f"- **Claim:** {claim_b}\n"
        "- **Evidence:** loop.py:88 — range is correct\n"
        "- **Verdict:** REFUTED\n"
    )
    findings = parse_wave_output(body)
    assert len(findings) == 2, findings
    changes, refutes = apply_verdicts(memo, findings)
    assert refutes == 2, (changes, refutes)
    assert changes == 2
    assert all(f.status == "refuted" for f in memo.values())


def test_swallow_guard_signals_on_empty_body():
    # ok but empty over a non-empty challenge set → output-contract miss, loud.
    diag = verifier_diagnostic(True, [], n_unverified=3, n_challenged=1, body_head="")
    assert diag is not None and "0 parseable verdicts" in diag


def test_swallow_guard_signals_on_prose_body():
    prose = "I reviewed everything and all three findings look correct to me overall."
    assert parse_wave_output(prose) == []  # the exact trigger condition
    diag = verifier_diagnostic(
        True, parse_wave_output(prose), n_unverified=3, n_challenged=0, body_head=prose
    )
    assert diag is not None and "output-contract miss" in diag


def test_swallow_guard_signals_on_not_ok():
    diag = verifier_diagnostic(False, [], n_unverified=2, n_challenged=0, body_head="(timeout)")
    assert diag is not None and "ok=False" in diag


def test_swallow_guard_silent_on_clean_pass():
    # genuine "nothing to challenge" → no diagnostic
    assert verifier_diagnostic(True, [], n_unverified=0, n_challenged=0, body_head="") is None
