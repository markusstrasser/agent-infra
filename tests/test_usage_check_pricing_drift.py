"""Drift-test: the vendored PRICING in scripts/usage-check.py must equal the
canonical llmx/llmx/usage_report.py:PRICING (epistemic-discipline invariant #9).

agent-infra can't import llmx (separate env), so usage-check.py vendors a copy.
This test AST-parses BOTH source files (no import of either) and asserts the maps
are identical — so the metered-spend alarm (usage-check --metered-today) and the
in-llmx dispatch guard price spend the same way. If they diverge, sync usage-check
to llmx (llmx is the single source of truth for rates).

Skips (not fails) when the llmx checkout is absent — the test is about drift
between two present sources, not a hard dependency on the sibling repo.
"""

import ast
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parent.parent
_USAGE_CHECK = _REPO / "scripts" / "usage-check.py"
_LLMX_USAGE_REPORT = pathlib.Path.home() / "Projects" / "llmx" / "llmx" / "usage_report.py"


def _extract_pricing(path: pathlib.Path) -> dict:
    """Return the PRICING dict literal from a module source, via AST (no import)."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        targets = getattr(node, "targets", None)
        if isinstance(node, ast.Assign) and targets:
            for t in targets:
                if isinstance(t, ast.Name) and t.id == "PRICING":
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "PRICING" and node.value is not None:
            return ast.literal_eval(node.value)
    raise AssertionError(f"no PRICING literal found in {path}")


def test_vendored_pricing_matches_llmx():
    vendored = _extract_pricing(_USAGE_CHECK)
    if not _LLMX_USAGE_REPORT.exists():
        pytest.skip(f"llmx checkout absent at {_LLMX_USAGE_REPORT}; can't drift-test")
    canonical = _extract_pricing(_LLMX_USAGE_REPORT)
    # Normalize tuples (literal_eval yields tuples both sides) and compare.
    assert vendored == canonical, (
        "usage-check.py PRICING has drifted from llmx usage_report.PRICING.\n"
        f"only in usage-check: {set(vendored) - set(canonical)}\n"
        f"only in llmx:        {set(canonical) - set(vendored)}\n"
        f"value mismatches:    "
        f"{ {k: (vendored.get(k), canonical.get(k)) for k in set(vendored) & set(canonical) if vendored[k] != canonical[k]} }\n"
        "llmx is the single source — sync scripts/usage-check.py to it."
    )
