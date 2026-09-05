"""Exercise reporting consumers against request-level Astra billing fixtures."""

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def ledger(tmp_path, **overrides):
    row = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "openai",
        "transport": "openai-api",
        "model": "gpt-6-astra",
        "prompt_tokens": 1_000_000,
        "completion_tokens": 80_000,
        "reasoning_tokens": 50_000,
        "completion_includes_reasoning": True,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "caller": "fixture",
        "cwd": "/fixture/project",
        **overrides,
    }
    path = tmp_path / "usage.jsonl"
    path.write_text(json.dumps(row) + "\n")
    return path


def report(path, *args, as_json=True):
    command = [sys.executable, str(ROOT / "scripts/usage-check.py"), "--log", str(path), *args]
    if as_json:
        command.append("--json")
    result = subprocess.run(
        command,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode in (0, 1, 2), result.stderr
    return result.returncode, json.loads(result.stdout) if as_json else result.stdout


def test_reports_match_guard_when_astra_cache_writes_are_unreported(tmp_path):
    import spend_forensics
    from llmx.spend_guard import metered_spend_today

    path = ledger(tmp_path, prompt_tokens=300_000, completion_tokens=10_000,
                  reasoning_tokens=0, cache_write_tokens=None)
    assert metered_spend_today(path) == (8.25, True)
    for args in ((), ("--metered-today",)):
        status, data = report(path, *args)
        assert status == 0
        cost = data["metered_total_usd"] if args else data["total"]["cost"]
        assert cost == 8.25
        assert "conservative estimate" in data["note"].lower()
        assert "cache-write rate" in data["note"]
        _, text = report(path, *args, as_json=False)
        assert "8.25" in text
        assert "conservative estimate" in text
        assert "cache-write rate" in text
    forensic = spend_forensics.rollup(path, dt.datetime.now(dt.timezone.utc).strftime("%Y-%m"))
    assert forensic["metered_usd"] == 8.25
    assert "conservative estimate" in forensic["note"]
    assert "cache-write rate" in forensic["note"]


def test_harness_request_estimate_keeps_session_shadow_at_base_rates(tmp_path, monkeypatch, capsys):
    import harness_cost_meter as meter

    path = ledger(tmp_path, prompt_tokens=300_000, completion_tokens=10_000,
                  reasoning_tokens=0, cache_write_tokens=None, caller="harness-cost-meter")
    usage_dir = tmp_path / ".claude"
    usage_dir.mkdir()
    (usage_dir / "llmx-usage.jsonl").write_bytes(path.read_bytes())
    monkeypatch.setattr(meter.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(meter.shutil, "which", lambda _: "/mock/llmx")
    monkeypatch.setattr(meter.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout="offline fixture", stderr="",
    ))
    data = meter.probe_llmx(prompt="offline fixture", timeout=1, model="gpt-6-astra")
    assert data["est_usd"] == 8.25
    assert "conservative estimate" in data["pricing_note"].lower()
    assert "cache-write rate" in data["pricing_note"]
    meter._print_probe([data])
    assert "cache-write rate" in capsys.readouterr().out
    assert meter._est_session_usd("gpt-6-astra", 300_000, 10_000) == 3.5


def test_long_request_triggers_25_dollar_alarm(tmp_path):
    status, data = report(ledger(tmp_path), "--metered-today", "--alarm", "25")
    assert status == 1
    assert data["alarm"] is True
    assert data["metered_total_usd"] == 26.0
    assert data["by_spender"][0]["out_tok"] == 80_000


def test_cached_long_request_and_reasoning_count_once(tmp_path):
    path = ledger(tmp_path, prompt_tokens=300_000, completion_tokens=1_000,
                  reasoning_tokens=600, cached_tokens=200_000, cache_write_tokens=50_000)
    status, data = report(path)
    assert status == 0
    assert data["total"]["cost"] == pytest.approx(2.725)
    assert data["total"]["output_tok"] == 1_000


def test_subscription_usage_is_excluded_from_metered_alarm(tmp_path):
    status, data = report(ledger(tmp_path, transport="codex-cli"), "--metered-today", "--alarm", "25")
    assert status == 0
    assert data["metered_calls"] == 0
    assert data["metered_total_usd"] == 0


def test_forensics_uses_request_categories(tmp_path):
    spec = importlib.util.spec_from_file_location("spend_forensics", ROOT / "scripts/spend_forensics.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    data = module.rollup(ledger(tmp_path), dt.datetime.now(dt.timezone.utc).strftime("%Y-%m"))
    assert data["metered_usd"] == 26.0
    assert data["by_model"][0]["out_tok"] == 80_000


def test_empty_report_has_zero_output(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    status, data = report(path)
    assert status == 0
    assert data["total"]["output_tok"] == 0


def test_interrupted_usage_is_incomplete_for_alarm(tmp_path):
    status, data = report(ledger(tmp_path, prompt_tokens=None, completion_tokens=None),
                          "--metered-today", "--alarm", "25")
    assert status == 2
    assert data["cost_complete"] is False
    assert data["unknown_cost_calls"] == 1


def test_unknown_row_cannot_hide_known_cap_breach(tmp_path):
    path = ledger(tmp_path)
    known = path.read_text()
    ledger(tmp_path, prompt_tokens=None, completion_tokens=None)
    path.write_text(path.read_text() + known)
    status, data = report(path, "--metered-today", "--alarm", "25")
    assert status == 1
    assert data["metered_total_usd"] == 26.0
    assert data["cost_complete"] is False


@pytest.mark.parametrize("subtotal, expected", [(0, "warn"), (26, "fail")])
def test_doctor_surfaces_incomplete_accounting(monkeypatch, subtotal, expected):
    import doctor

    monkeypatch.setattr(doctor, "run", lambda *args, **kwargs: json.dumps({
        "metered_total_usd": subtotal, "metered_calls": 2,
        "cost_complete": False, "unknown_cost_calls": 1,
    }))
    assert doctor.check_metered_spend()[0].status == expected
