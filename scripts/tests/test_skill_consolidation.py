"""Tests for skill consolidation: mode telemetry, directory structure, call site migration."""
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / "Projects" / "skills"


def test_mode_extraction_from_args():
    """The pretool-skill-log hook extracts first word of args as mode."""
    # Simulate what the hook does: MODE=$(echo "$ARGS" | awk '{print $1}')
    test_cases = [
        ("sessions meta 5", "sessions"),
        ("model target.md", "model"),
        ("", ""),
        ("maintain", "maintain"),
        ("cycle --days 7", "cycle"),
    ]
    for args, expected_mode in test_cases:
        result = subprocess.run(
            ["awk", "{print $1}"],
            input=args, capture_output=True, text=True,
        )
        assert result.stdout.strip() == expected_mode, (
            f"args={args!r}: expected {expected_mode!r}, got {result.stdout.strip()!r}"
        )


def test_all_workflow_skills_exist():
    """All 6 workflow skills have SKILL.md."""
    workflows = ["observe", "improve", "review", "research", "analyze", "upgrade"]
    for w in workflows:
        skill_path = SKILLS_DIR / w / "SKILL.md"
        assert skill_path.exists(), f"Missing {skill_path}"


def test_standalone_skills_exist():
    """All 8 standalone + 2 invocable ref + 3 runtime skills have SKILL.md."""
    standalones = [
        "brainstorm", "negative-space-sweep", "de-slop", "entity-management",
        "constitution", "trending-scout", "bio-verify", "goals",
        "model-guide", "llmx-guide",
        "modal", "google-workspace", "browse",
    ]
    for s in standalones:
        skill_path = SKILLS_DIR / s / "SKILL.md"
        assert skill_path.exists(), f"Missing {skill_path}"


def test_absorbed_skills_deleted():
    """All 25 absorbed skills are gone."""
    absorbed = [
        "session-analyst", "design-review", "retro", "supervision-audit",
        "harvest", "suggest-skill", "maintain", "tick",
        "model-review", "verify-findings", "plan-close",
        "researcher", "research-cycle", "knowledge-compile", "knowledge-diff",
        "dispatch-research",
        "causal-check", "causal-dag", "causal-robustness", "competing-hypotheses",
        "investigate",
        "project-upgrade", "novel-expansion", "agent-pliability", "evolution-forensics",
    ]
    for s in absorbed:
        skill_dir = SKILLS_DIR / s
        assert not skill_dir.exists(), f"Should be deleted: {skill_dir}"


def test_reference_docs_migrated():
    """5 reference-only skills moved to references/."""
    refs = ["claude-api", "epistemics", "source-grading", "debug-mcp", "data-acquisition"]
    for r in refs:
        ref_dir = SKILLS_DIR / "references" / r
        assert ref_dir.exists(), f"Missing reference: {ref_dir}"
        # Old location should be gone
        if r != "debug-mcp":  # debug-mcp was debug-mcp-servers
            old_dir = SKILLS_DIR / r
            assert not old_dir.exists(), f"Old dir should be deleted: {old_dir}"


def test_total_skill_count():
    """Post-consolidation: exactly 19 invocable skills."""
    count = len(list(SKILLS_DIR.glob("*/SKILL.md")))
    assert count == 19, f"Expected 19 skills, found {count}"


def test_observe_has_lenses():
    """observe workflow has 4 lens files."""
    lenses = list((SKILLS_DIR / "observe" / "lenses").glob("*.md"))
    assert len(lenses) == 4, f"Expected 4 lenses, found {len(lenses)}: {[l.name for l in lenses]}"


def test_review_has_lenses():
    """review workflow has 3 lens files."""
    lenses = list((SKILLS_DIR / "review" / "lenses").glob("*.md"))
    assert len(lenses) == 3, f"Expected 3 lenses, found {len(lenses)}: {[l.name for l in lenses]}"


def test_scripts_copied_to_workflows():
    """Key scripts exist in new workflow directories."""
    checks = [
        ("observe/scripts/extract_transcript.py", True),
        ("observe/scripts/extract_supervision.py", True),
        ("observe/scripts/session-shape.py", True),
        ("review/scripts/model-review.py", True),
        ("review/scripts/build_plan_close_context.py", True),
        ("improve/scripts/extract_user_tags.py", True),
        ("upgrade/scripts/dump_codebase.py", True),
        ("research/scripts/gather-cycle-state.sh", True),
    ]
    for path, should_exist in checks:
        full = SKILLS_DIR / path
        assert full.exists() == should_exist, (
            f"{'Missing' if should_exist else 'Should not exist'}: {full}"
        )


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
