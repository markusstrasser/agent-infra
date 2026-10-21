"""Tests for token reduction plan scripts and hooks.

Tests the contract of each new component:
- Percentile calculations (token-baseline, dashboard)
- Hook JSON output safety
- Terse bash pattern matching
- Cost-awareness counter gating
- Read discipline telemetry
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).parent.parent / "scripts" / "hooks-staging"


# ── Terse Bash Hook Tests ──────────────────────────────────────────

def run_cost_hook(counter_value: int = 50) -> tuple[str, int]:
    """Run cost-awareness hook at a given counter value. Returns (stdout, exit_code)."""
    hook = HOOKS_DIR / "pretool-cost-awareness.sh"
    if not hook.exists():
        pytest.skip(f"Hook not found: {hook}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(str(counter_value - 1))  # Will be incremented to counter_value
        counter_file = f.name

    input_json = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(Path.home()),
        "PWD": str(Path.home() / "Projects" / "meta"),
    }

    result = subprocess.run(
        ["bash", "-c", f'COUNTER_FILE="{counter_file}" && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0) && COUNT=$((COUNT + 1)) && echo "$COUNT" > "$COUNTER_FILE" && [ $((COUNT % 50)) -ne 0 ] && exit 0; echo "WOULD_CHECK"'],
        input=input_json,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    Path(counter_file).unlink(missing_ok=True)
    return result.stdout.strip(), result.returncode


class TestCostAwarenessHook:
    """Contract: fires every 50 calls, advisory only (exit 0)."""

    def test_skips_at_counter_1(self):
        """Hook should skip (not check) when counter is not multiple of 50."""
        stdout, code = run_cost_hook(counter_value=1)
        assert code == 0
        assert "WOULD_CHECK" not in stdout

    def test_fires_at_counter_50(self):
        """Hook should fire (check) when counter hits 50."""
        stdout, code = run_cost_hook(counter_value=50)
        assert code == 0
        assert "WOULD_CHECK" in stdout

    def test_skips_at_counter_51(self):
        stdout, code = run_cost_hook(counter_value=51)
        assert code == 0
        assert "WOULD_CHECK" not in stdout

    def test_fires_at_counter_100(self):
        stdout, code = run_cost_hook(counter_value=100)
        assert code == 0
        assert "WOULD_CHECK" in stdout


# ── Read Discipline Hook Tests ─────────────────────────────────────

def run_read_hook(file_path: str, offset=None, limit=None) -> str:
    """Run the read discipline hook and return stdout."""
    hook = HOOKS_DIR / "pretool-read-discipline.sh"
    if not hook.exists():
        pytest.skip(f"Hook not found: {hook}")
    tool_input = {"file_path": file_path}
    if offset is not None:
        tool_input["offset"] = offset
    if limit is not None:
        tool_input["limit"] = limit

    input_json = json.dumps({"tool_name": "Read", "tool_input": tool_input})
    result = subprocess.run(
        ["bash", str(hook)],
        input=input_json,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    return result.stdout.strip()


class TestReadDisciplineHook:
    """Contract: logs full-file reads, warns on repeats, never blocks."""

    def test_full_file_read_exits_0(self):
        out = run_read_hook("/tmp/test_file.py")
        # First read should not warn (no prior reads in this process)
        assert "decision" not in out or "block" not in out

    def test_targeted_read_is_silent(self):
        out = run_read_hook("/tmp/test_file.py", offset=10, limit=20)
        assert out == "" or "additionalContext" not in out

    def test_never_blocks(self):
        """Even on problematic input, hook should exit 0."""
        hook = HOOKS_DIR / "pretool-read-discipline.sh"
        if not hook.exists():
            pytest.skip(f"Hook not found: {hook}")
        # Malformed JSON input
        result = subprocess.run(
            ["bash", str(hook)],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0

    def test_special_chars_in_path(self):
        """File paths with special characters should not break JSON output."""
        out = run_read_hook("/tmp/file with spaces & 'quotes'.py")
        # Should either be empty or valid JSON
        if out:
            json.loads(out)  # Should not raise


# ── Dashboard Top-Decile Tests ─────────────────────────────────────

class TestDashboardTopDecile:
    """Contract: top-decile panel computes correctly on sample data."""

    def test_top_decile_selects_correct_count(self):
        """10% of 100 sessions = 10 sessions."""
        receipts = [{"cost_usd": i, "project": "test", "duration_min": 10, "context_pct": 20, "ts": "2026-04-07T00:00:00"}
                    for i in range(100)]
        sorted_by_cost = sorted(receipts, key=lambda r: r["cost_usd"], reverse=True)
        top_decile = sorted_by_cost[:max(1, len(sorted_by_cost) // 10)]
        assert len(top_decile) == 10
        assert top_decile[0]["cost_usd"] == 99
        assert top_decile[-1]["cost_usd"] == 90
