"""posttool-paper-quality: unknown retraction status and failed checks must reach the agent."""

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "posttool-paper-quality.py"
_spec = importlib.util.spec_from_file_location("posttool_paper_quality", _PATH)
ppq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ppq)


def test_failed_retraction_lookup_is_rendered_unknown():
    out = ppq._render_quality_context({
        "quality_status": "degraded",
        "quality": {"retracted": None, "retraction_check": "failed: crossref HTTP 503",
                    "check_failures": ["funding: timeout"], "feature_source": "heuristic"},
    })
    assert "Retraction status UNKNOWN (failed: crossref HTTP 503)" in out
    assert "Check failed: funding: timeout" in out
    assert "keyword heuristics" in out
    assert "Quality status is degraded." in out


def test_complete_clean_card_has_no_unknown_line():
    out = ppq._render_quality_context({
        "quality_status": "assessed",
        "quality": {"retracted": False, "retraction_check": "complete", "feature_source": "heuristic+gemini"},
    })
    assert "UNKNOWN" not in out and "Quality status" not in out
