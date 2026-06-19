"""Tests for predictions.cmd_auto_resolve — the proxy-free accept-gate half.

Guards the two invariants that make auto-resolution SAFE:
  1. it REFUTES a DUE+OPEN prediction whose bare-SHA commit is unreachable from HEAD;
  2. it NEVER resolves anything else (non-SHA/cross-repo commit, still-reachable SHA,
     not-yet-DUE, or already-resolved) — a false resolution is the worse error.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


def _load_predictions(ledger: Path):
    spec = importlib.util.spec_from_file_location("predictions_t", SCRIPTS / "predictions.py")
    assert spec and spec.loader  # narrow Optional for the type-checker; a missing spec is a real failure
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    setattr(mod, "LEDGER", ledger)  # redirect the module-level ledger at the seam
    return mod


def _write(ledger: Path, rows: list[dict]) -> None:
    ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _resolutions(ledger: Path) -> list[dict]:
    return [json.loads(l) for l in ledger.read_text().splitlines()
            if l.strip() and json.loads(l).get("kind") == "resolution"]


def test_refutes_unreachable_sha(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    _write(ledger, [{"id": "p1", "kind": "prediction", "change": "x", "commit": "deadbeefdead",
                     "prediction": "y", "metric": "z", "check_date": "2020-01-01"}])
    mod = _load_predictions(ledger)
    acted = mod.cmd_auto_resolve()
    assert acted == 1
    res = _resolutions(ledger)
    assert len(res) == 1 and res[0]["id"] == "p1" and res[0]["status"] == "refuted"
    assert res[0]["auto"] is True


def test_skips_non_sha_commit(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    _write(ledger, [{"id": "p1", "kind": "prediction", "change": "x", "commit": "skills@a174cf0",
                     "prediction": "y", "metric": "z", "check_date": "2020-01-01"}])
    mod = _load_predictions(ledger)
    assert mod.cmd_auto_resolve() == 0
    assert _resolutions(ledger) == []


def test_skips_reachable_sha(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=SCRIPTS,
                          capture_output=True, text=True).stdout.strip()
    _write(ledger, [{"id": "p1", "kind": "prediction", "change": "x", "commit": head,
                     "prediction": "y", "metric": "z", "check_date": "2020-01-01"}])
    mod = _load_predictions(ledger)
    assert mod.cmd_auto_resolve() == 0  # still in history → can't auto-confirm
    assert _resolutions(ledger) == []


def test_skips_not_due(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    _write(ledger, [{"id": "p1", "kind": "prediction", "change": "x", "commit": "deadbeefdead",
                     "prediction": "y", "metric": "z", "check_date": "2999-01-01"}])
    mod = _load_predictions(ledger)
    assert mod.cmd_auto_resolve() == 0
    assert _resolutions(ledger) == []


def test_skips_already_resolved(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    _write(ledger, [
        {"id": "p1", "kind": "prediction", "change": "x", "commit": "deadbeefdead",
         "prediction": "y", "metric": "z", "check_date": "2020-01-01"},
        {"id": "p1", "kind": "resolution", "status": "confirmed", "note": "manual"},
    ])
    mod = _load_predictions(ledger)
    assert mod.cmd_auto_resolve() == 0
    assert len(_resolutions(ledger)) == 1  # no new resolution appended


def test_dry_run_writes_nothing(tmp_path):
    ledger = tmp_path / "predictions.jsonl"
    _write(ledger, [{"id": "p1", "kind": "prediction", "change": "x", "commit": "deadbeefdead",
                     "prediction": "y", "metric": "z", "check_date": "2020-01-01"}])
    mod = _load_predictions(ledger)
    assert mod.cmd_auto_resolve(dry_run=True) == 1
    assert _resolutions(ledger) == []  # dry-run never appends
