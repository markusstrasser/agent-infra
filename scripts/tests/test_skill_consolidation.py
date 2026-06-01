"""Skill mode-telemetry contract (the pretool-skill-log hook).

The structural-snapshot tests that used to live here (exact skill count, the
42→19 consolidation's specific dir names, review/observe lens counts) were
RETIRED 2026-06-01: they froze a one-time migration's end-state and broke as the
skill set evolved (35 skills now, `review`→`critique`, etc.). Hard-coding skill
names/counts in a test is inherently brittle. Ongoing skill structure is
validated dynamically by `scripts/skill-validator.py` (`just skill-health`) —
that is the live gate; this file keeps only the durable, non-snapshot check.
"""
import subprocess


def test_mode_extraction_from_args():
    """The pretool-skill-log hook extracts the first word of args as the mode:
    MODE=$(echo "$ARGS" | awk '{print $1}')."""
    test_cases = [
        ("sessions agent-infra 5", "sessions"),
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
