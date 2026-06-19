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
  predictions.py register "<change>" "<prediction>" "<metric>" <check_date> [commit] [id]

The registration trigger (register_implementations.py, run daily by drift-sentinel) is the
closing-force actuator: every implemented finding gets a scheduled earn-its-keep re-check so
no scaffold escapes the "does this still need to exist?" verdict (gov telos: shrink as IQ rises).
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "predictions.jsonl"


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


def register_prediction(change: str, prediction: str, metric: str,
                        check_date: str, commit: str = "", pid: str = "",
                        source: str = "") -> str | None:
    """Append a new prediction record; return its id, or None if already present.

    Idempotent by id — the SOLE writer of `kind:"prediction"` rows (cmd_resolve owns
    resolutions). Callers that derive a deterministic id (e.g. from commit+finding) get
    free dedup: a second call with the same id is a no-op. Append-only, never edits."""
    if not pid:
        pid = f"pred-{_today()}-{abs(hash(change)) % 10**8:08d}"
    preds, _ = _load()
    if pid in preds:
        return None
    rec = {"id": pid, "ts": _today(), "kind": "prediction", "change": change,
           "commit": commit, "prediction": prediction, "metric": metric,
           "check_date": check_date}
    if source:
        rec["source"] = source
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pid


def cmd_resolve(pid: str, status: str, note: str) -> None:
    if status not in ("confirmed", "refuted", "partial"):
        print("status must be confirmed|refuted|partial")
        sys.exit(1)
    _append_resolution(pid, status, note)
    print(f"resolved [{pid}]: {status} — {note}")


def _append_resolution(pid: str, status: str, note: str) -> None:
    rec = {"id": pid, "ts": _today(), "kind": "resolution", "status": status,
           "note": note, "auto": note.startswith("auto:")}
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


_SHA = __import__("re").compile(r"^[0-9a-f]{7,40}$")


def cmd_auto_resolve(dry_run: bool = False) -> int:
    """Resolve the PROXY-FREE subset of DUE predictions; leave the rest to the operator.

    The accept-gate half of predict-then-falsify (steal #1, 2026-06-19 SoTA synthesis).
    The ledger was write-only — 24 registered, 0 resolved — so the loop never closed
    (consumption-over-autonomy inside the RSI machinery). This resolves ONLY what is
    deterministically derivable WITHOUT a fragile commit→scaffold join:

      refuted — DUE+OPEN, `commit` is a bare agent-infra SHA, and that SHA is no longer
                reachable from HEAD ⇒ the change was reverted/rebased out ⇒ it did not
                earn its keep (the build-then-undo signal, directly checkable).

    Everything else (cross-repo `commit` refs, non-SHA commits, scaffolds whose
    earn-its-keep needs the ablation/gov-shrink verdict) is LEFT OPEN for the operator
    via questions_view — semantics/blast is the operator's boundary, never auto-judged.
    Confirming a prediction is NOT auto-done here: 'still present in history' is far
    weaker than 'predicted metric moved', and a false 'confirmed' is the worse error.
    """
    import subprocess
    preds, resolved = _load()
    today = _today()
    due_open = [p for pid, p in preds.items()
                if pid not in resolved and p.get("check_date", "9999") <= today]
    acted = 0
    for p in due_open:
        commit = (p.get("commit") or "").strip()
        if not _SHA.match(commit):
            continue  # cross-repo ref / prose / empty → operator's call
        reachable = subprocess.run(
            ["git", "-C", str(REPO), "merge-base", "--is-ancestor", commit, "HEAD"],
            capture_output=True).returncode == 0
        if reachable:
            continue  # still in history → can't auto-confirm; leave for operator
        note = f"auto: commit {commit} no longer reachable from HEAD — reverted/rebased, did not earn its keep"
        if dry_run:
            print(f"WOULD refute [{p['id']}] — {note}")
        else:
            _append_resolution(p["id"], "refuted", note)
            print(f"  ✗ refuted [{p['id']}] — {note}")
        acted += 1
    _, now_resolved = _load()
    print(f"auto-resolve: {acted} refuted; resolution_rate now {len(now_resolved)}/{len(preds)}")
    return acted


def main() -> None:
    a = sys.argv[1:]
    if not a or a[0] == "due":
        cmd_due()
    elif a[0] == "list":
        cmd_list()
    elif a[0] == "resolve" and len(a) >= 3:
        cmd_resolve(a[1], a[2], a[3] if len(a) > 3 else "")
    elif a[0] == "auto-resolve":
        cmd_auto_resolve(dry_run="--dry-run" in a)
    elif a[0] == "register" and len(a) >= 5:
        pid = register_prediction(
            change=a[1], prediction=a[2], metric=a[3], check_date=a[4],
            commit=a[5] if len(a) > 5 else "", pid=a[6] if len(a) > 6 else "")
        print(f"registered [{pid}]" if pid else "already present (no-op)")
    else:
        print("usage: predictions.py [due|list|auto-resolve [--dry-run]|"
              "resolve <id> <verdict> <note>|"
              "register <change> <prediction> <metric> <check_date> [commit] [id]]")
        sys.exit(1)


if __name__ == "__main__":
    main()
