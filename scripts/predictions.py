#!/usr/bin/env python3
"""predictions.py — pre-registered prediction ledger + resolver.

Every substantive behavioral/infra change registers a FALSIFIABLE prediction with a
check_date. The Questions-for-you VIEW (questions_view.py) surfaces DUE-and-unresolved
predictions as governance questions so they get a verdict (confirmed/refuted/partial)
instead of accreting unverified — the constitution's secondary constraint
("error-correction per session": autonomy only counts if errors are caught) made
concrete, and the existing 5 constitution-level Pre-Registered Tests generalized to
per-change.

The RESOLVER is the point. A write-only prediction log is false comfort
(generation-without-consumption) — so this ships WITH a surfacing, never alone. The
surfacing moved drift-sentinel → the Questions VIEW (2026-06-16) so every human-gated
verdict converges in ONE place. Scope it to changes with a MEASURABLE predicted effect.

Append-only JSONL (`predictions.jsonl` at repo root), records joined by `id`:
  prediction:  {"id","ts","kind":"prediction","change","commit","prediction","metric","check_date"}
  resolution:  {"id","ts","kind":"resolution","status":"confirmed|refuted|partial","note"}
A prediction is OPEN until a resolution with its id lands; DUE if OPEN and check_date<=today.
Resolution is append-only too (the belief-change history IS calibration data) — never edit.

Usage:
  predictions.py due                                 # DUE-and-open (drift-sentinel greps "DUE")
  predictions.py list                                # all, with status
  predictions.py resolve <id> <confirmed|refuted|partial> "<note>"
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "predictions.jsonl"


def _load() -> tuple[dict, set]:
    preds: dict = {}
    resolved: set = set()
    if LEDGER.is_file():
        for line in LEDGER.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("kind") == "prediction" and r.get("id"):
                preds[r["id"]] = r
            elif r.get("kind") == "resolution" and r.get("id"):
                resolved.add(r["id"])
    return preds, resolved


def _today() -> str:
    return datetime.date.today().isoformat()


def due_predictions() -> list[dict]:
    """DUE-and-open prediction records (OPEN ∧ check_date<=today), oldest first.

    The data behind `due`; imported by questions_view so the Questions VIEW and the CLI
    agree on what's DUE (single-source — consumers LOAD this, never re-derive the rule)."""
    preds, resolved = _load()
    today = _today()
    due = [p for pid, p in preds.items()
           if pid not in resolved and p.get("check_date", "9999") <= today]
    due.sort(key=lambda p: p.get("check_date", ""))
    return due


def cmd_due() -> None:
    for p in due_predictions():
        print(f"DUE {p['check_date']} [{p['id']}] {p.get('change', '')}")
        print(f"    predict: {p.get('prediction', '')}")
        print(f"    metric:  {p.get('metric', '')}  (resolve: predictions.py resolve {p['id']} <verdict> \"...\")")


def cmd_list() -> None:
    preds, resolved = _load()
    today = _today()
    if not preds:
        print("(no predictions registered)")
        return
    for pid, p in sorted(preds.items(), key=lambda kv: kv[1].get("check_date", "")):
        if pid in resolved:
            st = "resolved"
        elif p.get("check_date", "9999") <= today:
            st = "DUE"
        else:
            st = "open"
        print(f"[{st:8}] {p.get('check_date', '?')}  {pid}  — {p.get('change', '')}")


def cmd_resolve(pid: str, status: str, note: str) -> None:
    if status not in ("confirmed", "refuted", "partial"):
        print("status must be confirmed|refuted|partial")
        sys.exit(1)
    rec = {"id": pid, "ts": _today(), "kind": "resolution", "status": status, "note": note}
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"resolved [{pid}]: {status} — {note}")


def main() -> None:
    a = sys.argv[1:]
    if not a or a[0] == "due":
        cmd_due()
    elif a[0] == "list":
        cmd_list()
    elif a[0] == "resolve" and len(a) >= 3:
        cmd_resolve(a[1], a[2], a[3] if len(a) > 3 else "")
    else:
        print("usage: predictions.py [due|list|resolve <id> <confirmed|refuted|partial> <note>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
