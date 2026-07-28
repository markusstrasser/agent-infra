#!/usr/bin/env python3
# Gov-ID: tool:self-inflicted-miner
# goal: surface the loop's OWN recurring errors — the ones no human ever corrected,
#       because the agent caught and locally fixed each instance and then forgot it.
# blast_radius: local (read-only over ~/.claude/event-log.jsonl)
"""self_inflicted_miner.py — the miss channel blindspot_miner cannot see.

WHY THIS EXISTS, stated as the gap it closes rather than as a feature:

`blindspot_miner.py` implements the operator's standing directive ("every time I mention
something, ask why the loop didn't find it") by mining HUMAN CORRECTIONS. That is the
right instrument for one channel and it is blind to the other:

    an error the agent makes, notices, fixes locally, and forgets
    produces NO human correction — so it is INVISIBLE to a corrections miner,
    no matter how many times it recurs.

Exhibit, 2026-07-28: markdown `inline code` inside a double-quoted shell argument executes
as command substitution and silently deletes the span. It happened 5 times across 4
sessions and 3 weeks (agentlogs: dc9fefad 07-06, 6f4a8626 + b0826e4e 07-17, 56b4ac68
07-25, c0db7fc1 07-28). Every single instance was self-caught and self-fixed in-session,
which is exactly why no human correction existed and why the corrections miner had nothing
to see. The operator eventually noticed the PATTERN across sessions — a job no instrument
was doing — and said "this keeps reappearing, maybe we can solve it for good."

The data to have caught it was already being written. `hook-trigger-log.sh` has logged every
gate fire since March; `~/.claude/event-log.jsonl` holds 33MB of them. Nothing reads it.

WHAT THE TWO SIGNALS MEAN — they call for OPPOSITE fixes, which is the whole point of
separating them:

  * HIGH-VOLUME GUARD (many blocks, many sessions) = the guard WORKS and the affordance is
    WRONG. Agents are re-learning the same rule several times per session, forever. The fix
    is to make the underlying operation safe by construction, not to nag harder. Global
    rule: "a guard with >50% force-rate gets retuned, not obeyed-around."
  * NEW/RARE PATTERN = a class that just started recurring. Worth a guard before it accretes.

A class with NO guard at all is invisible here too — this miner sees only what some gate
already catches. That residue is the agentlogs text channel's job (`agentlogs search`), and
the two together cover the space. Stating the limit so no one reads a clean run as "no
self-inflicted errors."
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib

LOG = pathlib.Path.home() / ".claude" / "event-log.jsonl"


def load(days: int, action_filter: str) -> list[dict]:
    cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for ln in LOG.read_text(errors="ignore").splitlines():
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if not isinstance(d, dict) or d.get("ts", "") < cut:
            continue
        if action_filter not in str(d.get("action", "")).lower():
            continue
        out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--action", default="block", help="block | warn | remind")
    ap.add_argument("--nag-threshold", type=int, default=20,
                    help="blocks/window above which a guard is a NAG, not a fix")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = load(a.days, a.action)
    per_hook: collections.Counter = collections.Counter()
    sessions = collections.defaultdict(set)
    projects = collections.defaultdict(set)
    for d in rows:
        h = d.get("hook") or "?"
        per_hook[h] += 1
        sessions[h].add(d.get("session"))
        projects[h].add(d.get("project"))

    findings = []
    for h, cnt in per_hook.most_common():
        ns, npj = len(sessions[h]), len(projects[h])
        per_sess = cnt / max(1, ns)
        verdict = ("NAG — fix the AFFORDANCE, not the guard" if cnt >= a.nag_threshold and ns >= 5
                   else "RECURRING — candidate for a guard upgrade" if cnt >= 5
                   else "sporadic")
        findings.append({"hook": h, "blocks": cnt, "sessions": ns, "projects": npj,
                         "per_session": round(per_sess, 1), "verdict": verdict})

    if a.json:
        print(json.dumps({"days": a.days, "action": a.action, "total": len(rows),
                          "findings": findings}, indent=1))
        return 0

    print(f"SELF-INFLICTED ERROR MINER — {len(rows)} '{a.action}' events / {a.days}d "
          f"across {len(per_hook)} gates")
    print("  (errors the loop made and no human corrected — the channel blindspot_miner cannot see)\n")
    print(f"  {'blocks':>7} {'sess':>5} {'proj':>5} {'per-sess':>9}  gate / verdict")
    for f in findings:
        print(f"  {f['blocks']:7d} {f['sessions']:5d} {f['projects']:5d} {f['per_session']:9.1f}  "
              f"{f['hook']}")
        if f["verdict"] != "sporadic":
            print(f"  {'':29}-> {f['verdict']}")
    nags = [f for f in findings if f["verdict"].startswith("NAG")]
    if nags:
        print(f"\n{len(nags)} gate(s) at NAG volume. A guard firing this often across this many "
              f"sessions is\nevidence the OPERATION is unsafe by default — make it safe by "
              f"construction, then the\nguard should go quiet on its own. Retuning the guard "
              f"instead treats the symptom.")
    print("\nLIMIT: a recurring error with NO gate is invisible here. Pair with "
          "`agentlogs search`\nover the same window for the un-guarded residue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
