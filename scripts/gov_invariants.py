"""Curated contradiction-invariant registry.

Each invariant couples a governance CLAUSE to a TELEMETRY metric with a
threshold, so "the system contradicts its own stated principle" becomes a
checkable predicate instead of a vibe. This is deliberately NOT a generic
SQL view over prose (that can't join text clauses to telemetry) — it is a
small, hand-curated set of Python assertions. Coverage is intentionally
partial; clauses with no clean telemetry shadow are `not-machine-testable`
and stay human-audited.

Each invariant returns a dict consumed by gov.py's report:
  {id, clause, claim, passed, value, threshold, evidence,
   confidence, blast_radius, detail}

A FAILING invariant => a contradiction proposal (routed by blast_radius).
Run standalone: uv run python3 scripts/gov_invariants.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "improvement-log.md"
RULES_DIR = REPO / ".claude" / "rules"
BTU_ENFORCER = REPO / "scripts" / "buildthenundo.py"


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def inv_rule_hook_balance(artifacts: list | None = None) -> dict:
    """Constitution P1: 'if it matters, enforce with hooks/tests, not instructions.'
    Telemetry shadow: the remedy mix in improvement-log. If we propose far more
    [rule]s than [hook]s, our own behavior contradicts P1."""
    txt = _read(LOG)
    rules = txt.count("[rule]")
    hooks = txt.count("[hook]")
    ratio = (rules / hooks) if hooks else float("inf")
    threshold = 2.0
    return {
        "id": "P1-rule-hook-balance",
        "clause": "Constitution P1 (architecture over instructions)",
        "claim": "if it matters, enforce with hooks/tests/scaffolding, not instructions",
        "passed": ratio <= threshold,
        "value": round(ratio, 2),
        "threshold": threshold,
        "evidence": f"{rules} [rule] proposals vs {hooks} [hook] proposals in improvement-log.md",
        "confidence": "medium",  # counts proposals, not deployed/impact-weighted artifacts
        "blast_radius": "constitution",
        "detail": "Imbalance requiring review, not proven contradiction — proposals are not "
                  "impact-weighted. A sustained high ratio means the system documents "
                  "architecture-over-instructions and then prescribes instructions.",
    }


def inv_recurrence_architecture(artifacts: list | None = None) -> dict:
    """Constitution P11: a pattern recurring 10+ times must become architecture.
    Telemetry shadow: BUILD-THEN-UNDO mentions in improvement-log vs whether an
    enforcing artifact exists."""
    txt = _read(LOG)
    n = len(re.findall(r"BUILD[-_ ]THEN[-_ ]UNDO", txt, re.IGNORECASE))
    enforced = BTU_ENFORCER.exists()
    passed = (n < 10) or enforced
    return {
        "id": "P11-recurrence-architecture",
        "clause": "Constitution P11 (recurring patterns become architecture)",
        "claim": "used/encountered 10+ times -> hook, skill, or scaffolding",
        "passed": passed,
        "value": n,
        "threshold": 10,
        "evidence": f"{n} BUILD-THEN-UNDO mentions; enforcer "
                    f"{'present' if enforced else 'ABSENT'} (scripts/buildthenundo.py)",
        "confidence": "high",
        "blast_radius": "local",
        "detail": "BUILD-THEN-UNDO is the top recurrence. P11 requires it become "
                  "architecture once past 10 occurrences; satisfied by a report-only "
                  "detector (not a blocking hook).",
    }


def inv_verifier_coverage(artifacts: list | None = None) -> dict:
    """Telos: governance shrinks as capability rises, driven by verifiers.
    A scaffold can only auto-retire if its goal has a verifier. This tracks the
    flywheel: % of load-bearing (non-style) artifacts that carry a verifier ref.
    Informational baseline on first runs; the trend is what matters."""
    load_bearing = [a for a in (artifacts or []) if a.get("blast_radius") != "style"]
    with_verifier = [a for a in load_bearing if a.get("verifier") and a["verifier"] != "null"]
    n = len(load_bearing)
    cov = (len(with_verifier) / n) if n else 0.0
    threshold = 0.0  # baseline run: any coverage is progress; trend tracked over time
    return {
        "id": "verifier-coverage",
        "clause": "Telos (governance shrinks with capability; goals+verifiers is the loop)",
        "claim": "every load-bearing scaffold should declare a verifier so it can be "
                 "capability-tested for removal",
        "passed": cov >= threshold,  # informational; never fails on a baseline run
        "value": f"{len(with_verifier)}/{n} ({cov:.0%})",
        "threshold": "rising",
        "evidence": f"{len(with_verifier)} of {n} load-bearing artifacts carry a verifier ref",
        "confidence": "high",
        "blast_radius": "local",
        "detail": "Coverage starts near zero — that IS the generative backlog. Each model "
                  "cycle, scaffolds with verifiers get shrink-tested; the rest need verifiers "
                  "written before they can auto-retire.",
    }


REGISTRY = [inv_rule_hook_balance, inv_recurrence_architecture, inv_verifier_coverage]


def run_all(artifacts: list | None = None) -> list[dict]:
    return [fn(artifacts) for fn in REGISTRY]


def coverage_note() -> str:
    """Honest coverage statement (research B4/#15: publish coverage %)."""
    # 3 machine-testable invariants; the rest of the corpus is human-audited.
    n_rules = len(list(RULES_DIR.glob("*.md"))) if RULES_DIR.exists() else 0
    return (f"{len(REGISTRY)} machine-testable invariants registered; "
            f"~{n_rules} rule files + constitution clauses remain human-audited "
            f"(not-machine-testable).")


if __name__ == "__main__":
    for r in run_all():
        mark = "✓" if r["passed"] else "✗ CONTRADICTION"
        print(f"{mark}  {r['id']}  value={r['value']} (thr {r['threshold']})")
        print(f"     {r['evidence']}")
    print("\n" + coverage_note())
