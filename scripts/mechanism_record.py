#!/usr/bin/env python3
"""F3 — predict-then-falsify gate (the acceptance discipline).

A governance change (rule / hook / act-drain promotion) is accepted only if its
*pre-registered mechanism fired* — not because an aggregate score improved.
EvoTrainer (arXiv:2606.03108): an intervention counts only if diagnostics +
backtests support the MECHANISM. ~30 of the 38 deep-read papers independently
specify this exact gate (research/2026-06-20-paper-integration-plan.md, F3).

Post-refute scope: the papers support the gate as analogy from versioned
experiments / replayable objective evals — so F3 records bind to an *objective
(or explicitly-labelled proxy) metric query over agentlogs.db* (the replayable
artifact F1 + the trace store supply), and EVERY record carries a negative
control. A change whose metric moved but whose control ALSO moved is CONFOUNDED,
not accepted — the defense against reward-hacking / self-preference
(RHO 2606.05922, NRT-Bench 2606.20408).

A "mechanism record" is a git-tracked governance artifact (native-patterns:
append-only knowledge → files, not a DB). One JSON per change in
mechanism-records/. Subcommands:

  mechanism_record.py record <slug> ...     scaffold a new record (writes a file)
  mechanism_record.py check <slug|path>     run the gate, emit FIRED/NOT_FIRED/CONFOUNDED
  mechanism_record.py list                  table of records + last verdict
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from common.db import open_db_ro
from common.paths import CLAUDE_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = REPO_ROOT / "mechanism-records"
DEFAULT_DB = CLAUDE_DIR / "agentlogs.db"

# Canonical schema. The SINGLE definition of a mechanism record (epistemic #9);
# the rule doc .claude/rules/predict-then-falsify-gate.md documents it in prose,
# this dataclass is the enforceable form.
ALLOWED_DIRECTIONS = ("decrease", "increase")
ALLOWED_STATUS = ("recorded", "fired", "not_fired", "confounded", "rolled_back")


@dataclass
class MechanismRecord:
    slug: str
    change_ref: str                  # commit sha / rule path / improvement-log id the gate guards
    predicted_failure_class: str     # the failure this change reduces (one line)
    expected_trace_observable: str   # what should change in the typed trace / agentlogs
    metric_query: str                # SQL over agentlogs.db; ONE scalar; binds :since :until
    direction: str                   # "decrease" | "increase" — predicted move of the metric
    control_query: str               # same shape; the metric that must stay ~flat (negative control)
    change_date: str                 # ISO date splitting before/after windows
    rollback_criterion: str          # when to revert
    baseline_window_days: int = 30   # how far before change_date to measure the before-rate
    min_effect_frac: float = 0.20    # required relative move to count as fired
    control_tolerance_frac: float = 0.20  # control move beyond this => CONFOUNDED
    recorded_at: str = ""
    status: str = "recorded"
    notes: str = ""
    last_check: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        errs = []
        if self.direction not in ALLOWED_DIRECTIONS:
            errs.append(f"direction must be one of {ALLOWED_DIRECTIONS}, got {self.direction!r}")
        if self.status not in ALLOWED_STATUS:
            errs.append(f"status must be one of {ALLOWED_STATUS}, got {self.status!r}")
        if not self.control_query.strip():
            errs.append("control_query is REQUIRED (negative control; no confound defense without it)")
        for q in (self.metric_query, self.control_query):
            low = q.lower()
            if q.strip() and (":since" not in low or ":until" not in low):
                errs.append(f"query must bind :since and :until — got: {q[:60]}")
        try:
            datetime.fromisoformat(self.change_date)
        except (ValueError, TypeError):
            errs.append(f"change_date not ISO: {self.change_date!r}")
        return errs


def _record_path(token: str) -> Path:
    p = Path(token)
    if p.suffix == ".json" and p.exists():
        return p
    return RECORDS_DIR / f"{token}.json"


def load_record(token: str) -> MechanismRecord:
    path = _record_path(token)
    data = json.loads(path.read_text())
    known = {f for f in MechanismRecord.__dataclass_fields__}  # type: ignore[attr-defined]
    return MechanismRecord(**{k: v for k, v in data.items() if k in known})


def save_record(rec: MechanismRecord) -> Path:
    RECORDS_DIR.mkdir(exist_ok=True)
    path = RECORDS_DIR / f"{rec.slug}.json"
    path.write_text(json.dumps(asdict(rec), indent=2) + "\n")
    return path


def _scalar(con, query: str, since: str, until: str) -> float:
    rows = con.execute(query, {"since": since, "until": until}).fetchall()
    if not rows or rows[0][0] is None:
        return 0.0
    return float(rows[0][0])


def _rate_per_day(con, query: str, since: datetime, until: datetime) -> float:
    days = max((until - since).total_seconds() / 86400.0, 1e-9)
    return _scalar(con, query, since.isoformat(), until.isoformat()) / days


def check_record(rec: MechanismRecord, db: Path) -> dict:
    """Run the gate: did the pre-registered mechanism fire, with the control flat?"""
    errs = rec.validate()
    if errs:
        return {"verdict": "INVALID", "errors": errs}
    change = datetime.fromisoformat(rec.change_date)
    before_start = change - timedelta(days=rec.baseline_window_days)
    now = datetime.now()  # noqa: DTZ005 — local wall clock fine for windowing
    if now <= change:
        return {"verdict": "PENDING", "reason": f"change_date {rec.change_date} is not in the past"}

    with open_db_ro(db) as con:
        m_before = _rate_per_day(con, rec.metric_query, before_start, change)
        m_after = _rate_per_day(con, rec.metric_query, change, now)
        c_before = _rate_per_day(con, rec.control_query, before_start, change)
        c_after = _rate_per_day(con, rec.control_query, change, now)

    def rel_move(before: float, after: float) -> float:
        if before == 0:
            return 0.0 if after == 0 else 1.0
        return (after - before) / before

    m_move = rel_move(m_before, m_after)
    c_move = abs(rel_move(c_before, c_after))
    moved_right_way = (m_move <= -rec.min_effect_frac) if rec.direction == "decrease" \
        else (m_move >= rec.min_effect_frac)
    control_flat = c_move <= rec.control_tolerance_frac

    if not moved_right_way:
        verdict = "NOT_FIRED"
    elif not control_flat:
        verdict = "CONFOUNDED"  # metric moved but so did the control → not attributable
    else:
        verdict = "FIRED"

    return {
        "verdict": verdict,
        "metric": {"before_per_day": round(m_before, 4), "after_per_day": round(m_after, 4),
                    "rel_move": round(m_move, 3), "direction": rec.direction},
        "control": {"before_per_day": round(c_before, 4), "after_per_day": round(c_after, 4),
                     "abs_rel_move": round(c_move, 3), "flat": control_flat},
        "checked_at": now.isoformat(timespec="seconds"),
    }


# --- CLI ---------------------------------------------------------------------

def _cmd_record(args) -> int:
    rec = MechanismRecord(
        slug=args.slug,
        change_ref=args.change_ref,
        predicted_failure_class=args.failure_class,
        expected_trace_observable=args.observable,
        metric_query=args.metric_query,
        direction=args.direction,
        control_query=args.control_query,
        change_date=args.change_date,
        rollback_criterion=args.rollback,
        recorded_at=datetime.now().date().isoformat(),  # noqa: DTZ005
    )
    errs = rec.validate()
    if errs:
        for e in errs:
            print(f"  ✗ {e}", file=sys.stderr)
        return 2
    path = save_record(rec)
    print(f"  ✓ recorded {path.relative_to(REPO_ROOT)}")
    return 0


def _cmd_check(args) -> int:
    rec = load_record(args.token)
    result = check_record(rec, Path(args.db))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        v = result["verdict"]
        mark = {"FIRED": "✓", "NOT_FIRED": "✗", "CONFOUNDED": "!", "PENDING": "…",
                "INVALID": "✗"}.get(v, "?")
        print(f"  {mark} {rec.slug}: {v}")
        if "metric" in result:
            m, c = result["metric"], result["control"]
            print(f"      metric  {m['before_per_day']}/d → {m['after_per_day']}/d "
                  f"({m['rel_move']:+.0%}, want {m['direction']})")
            print(f"      control {c['before_per_day']}/d → {c['after_per_day']}/d "
                  f"({c['abs_rel_move']:+.0%}, {'flat' if c['flat'] else 'MOVED'})")
        for e in result.get("errors", []):
            print(f"      ✗ {e}")
        if result.get("reason"):
            print(f"      {result['reason']}")
    # persist verdict back onto the record (append-only status history via last_check)
    if not args.no_write and "verdict" in result and result["verdict"] not in ("INVALID",):
        rec.last_check = result
        status_map = {"FIRED": "fired", "NOT_FIRED": "not_fired", "CONFOUNDED": "confounded"}
        rec.status = status_map.get(result["verdict"], rec.status)
        save_record(rec)
    return 0


def _cmd_list(args) -> int:
    if not RECORDS_DIR.is_dir():
        print("  (no mechanism-records/ yet)")
        return 0
    recs = sorted(RECORDS_DIR.glob("*.json"))
    if not recs:
        print("  (no records)")
        return 0
    print(f"  {'slug':32} {'status':12} {'change_date':12} predicted_failure_class")
    for p in recs:
        try:
            r = load_record(str(p))
        except (json.JSONDecodeError, TypeError):
            print(f"  ✗ {p.name}: unparseable")
            continue
        print(f"  {r.slug:32} {r.status:12} {r.change_date:12} {r.predicted_failure_class[:50]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="F3 predict-then-falsify mechanism gate")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("record", help="scaffold a new mechanism record")
    pr.add_argument("slug")
    pr.add_argument("--change-ref", required=True)
    pr.add_argument("--failure-class", required=True)
    pr.add_argument("--observable", required=True)
    pr.add_argument("--metric-query", required=True, help="SQL, one scalar, binds :since :until")
    pr.add_argument("--direction", choices=ALLOWED_DIRECTIONS, required=True)
    pr.add_argument("--control-query", required=True, help="negative control SQL, same shape")
    pr.add_argument("--change-date", required=True, help="ISO date")
    pr.add_argument("--rollback", required=True)
    pr.set_defaults(func=_cmd_record)

    pc = sub.add_parser("check", help="run the gate against agentlogs")
    pc.add_argument("token", help="record slug or path")
    pc.add_argument("--db", default=str(DEFAULT_DB))
    pc.add_argument("--json", action="store_true")
    pc.add_argument("--no-write", action="store_true", help="don't persist verdict onto the record")
    pc.set_defaults(func=_cmd_check)

    pl = sub.add_parser("list", help="list records + last verdict")
    pl.set_defaults(func=_cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
