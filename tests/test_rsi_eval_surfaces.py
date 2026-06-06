"""Smoke tests for small RSI eval surfaces."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


EXPERIMENTS = [
    ROOT / "experiments" / "claim-bench-rsi",
    ROOT / "experiments" / "hook-tuning",
    ROOT / "experiments" / "context-packing",
]


def _run_eval(path: Path) -> str:
    command = ["python3", "eval.py", "--locked"]
    if path.name == "claim-bench-rsi":
        command = ["uv", "run", "python3", "eval.py", "--locked"]
    result = subprocess.run(
        command,
        cwd=path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _headline_accuracy(output: str) -> float:
    for line in output.splitlines():
        if line.startswith("accuracy: "):
            return float(line.split(":", 1)[1].strip())
    raise AssertionError(f"missing headline accuracy in output:\n{output}")


def test_rsi_eval_surfaces_are_locked_and_runnable():
    for path in EXPERIMENTS:
        out = _run_eval(path)
        assert "split: locked" in out
        threshold = 0.90 if path.name == "claim-bench-rsi" else 1.0
        assert _headline_accuracy(out) >= threshold


def test_rsi_configs_have_holdout_gates():
    for path in EXPERIMENTS:
        cfg = json.loads((path / "config.json").read_text(encoding="utf-8"))
        if path.name == "claim-bench-rsi":
            assert cfg["eval_command"] == "uv run python3 eval.py --locked"
            assert cfg["holdout_eval_command"] == "uv run python3 eval.py --holdout"
        else:
            assert cfg["eval_command"] == "python3 eval.py --locked"
            assert cfg["holdout_eval_command"] == "python3 eval.py --holdout"
        assert cfg["holdout_every_k_keeps"] == 1
        assert cfg["editable_files"]
        assert "cases.json" in cfg.get("readonly_context", []) or path.name == "claim-bench-rsi"
