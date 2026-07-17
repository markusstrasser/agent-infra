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
_LLMX_MODEL_IDS = pathlib.Path.home() / "Projects" / "llmx" / "llmx" / "model_ids.py"


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


def _extract_literal(path: pathlib.Path, name: str):
    """Return a top-level name's literal value from a module source, via AST."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        targets = getattr(node, "targets", None)
        if isinstance(node, ast.Assign) and targets:
            for t in targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name and node.value is not None:
            return ast.literal_eval(node.value)
    raise AssertionError(f"no {name} literal found in {path}")


def _apply_programmatic_pricing(path: pathlib.Path, pricing: dict) -> dict:
    """Replicate llmx's runtime Cursor-Grok pricing loop:

        for cursor_model in CURSOR_GROK45_MODELS:
            PRICING[cursor_model] = (4.0, 18.0) if cursor_model.endswith("-fast") else (2.0, 6.0)

    The AST literal can't see runtime-added keys — without this, the vendored copy
    would be barred from pricing Cursor-Grok variants at all (they'd surface as $0).
    Rates are parsed from the loop's IfExp branches and slugs from model_ids.py,
    so changes on the llmx side are still caught rather than hardcoded here.
    """
    tree = ast.parse(path.read_text())
    fast_rate = base_rate = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not (isinstance(node.iter, ast.Name) and node.iter.id == "CURSOR_GROK45_MODELS"):
            continue
        for stmt in node.body:
            value = getattr(stmt, "value", None)
            if isinstance(stmt, ast.Assign) and isinstance(value, ast.IfExp):
                fast_rate = ast.literal_eval(value.body)
                base_rate = ast.literal_eval(value.orelse)
    if fast_rate is None:
        return pricing  # loop removed upstream — literal dict is the whole truth
    out = dict(pricing)
    for model in _extract_literal(_LLMX_MODEL_IDS, "CURSOR_GROK45_MODELS"):
        out[model] = fast_rate if model.endswith("-fast") else base_rate
    return out


def test_vendored_pricing_matches_llmx():
    vendored = _extract_pricing(_USAGE_CHECK)
    if not _LLMX_USAGE_REPORT.exists():
        pytest.skip(f"llmx checkout absent at {_LLMX_USAGE_REPORT}; can't drift-test")
    canonical = _apply_programmatic_pricing(_LLMX_USAGE_REPORT, _extract_pricing(_LLMX_USAGE_REPORT))
    # Normalize tuples (literal_eval yields tuples both sides) and compare.
    assert vendored == canonical, (
        "usage-check.py PRICING has drifted from llmx usage_report.PRICING.\n"
        f"only in usage-check: {set(vendored) - set(canonical)}\n"
        f"only in llmx:        {set(canonical) - set(vendored)}\n"
        f"value mismatches:    "
        f"{ {k: (vendored.get(k), canonical.get(k)) for k in set(vendored) & set(canonical) if vendored[k] != canonical[k]} }\n"
        "llmx is the single source — sync scripts/usage-check.py to it."
    )
