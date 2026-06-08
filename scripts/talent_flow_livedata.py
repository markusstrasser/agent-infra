#!/usr/bin/env python3
"""Talent-flow measurement via Live Data Technologies workforce panel.

Granularity #2 (measure a flow, not just verify a move) — the thing Exa could NOT
do (see research/2026-06-08-talent-flow-intelligence-feasibility.md, Revision).

Two phases:
  FREE  — size:0 `count` queries. For target B and each source A, count people with
          BOTH an A-job and a B-job (co-occurrence) → real feeder histogram, 0 credits.
  PAID  — --sample N downloads N recent joiners at B, parses each prior company from
          the full jobs[] history → directed from-distribution. Costs N credits
          (beta cap: 500 people/month).

Auth: Authorization: Bearer $LIVEDATA_API_KEY  (org via $LIVEDATA_ORG_ID, default o_3daf8872)

Usage:
    python3 scripts/talent_flow_livedata.py --to NVIDIA \
        --from "Intel,AMD,Qualcomm,Google,Meta,Apple,Microsoft,Broadcom,Amazon" \
        --controls "Walmart,JPMorgan Chase" --since 2024-01-01
    python3 scripts/talent_flow_livedata.py --to NVIDIA --from "Intel,AMD" --sample 25
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ORG = os.environ.get("LIVEDATA_ORG_ID", "o_3daf8872")
URL = f"https://gotlivedata.io/api/people/v1/{ORG}/search"


def _post(body, api_key, timeout=45):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _clause(field, values=None, match="exact", date_from=None, exists=False, neg=False):
    c = {"field": field, "type": "must_not" if neg else "must"}
    if exists:
        c["match_type"] = "exists"
    else:
        c["match_type"] = match
    if values is not None:
        c["string_values"] = values
    if date_from:
        c["date_from"] = date_from
    return c


def count(filters, api_key):
    """size:0 count — FREE (no people returned)."""
    body = {"size": 0, "filters": [{"operator": "and", "filters": filters}]}
    return _post(body, api_key).get("count", 0)


def cooccur(a, b, since, api_key):
    f = [_clause("jobs.company.name", [a]), _clause("jobs.company.name", [b])]
    if since:
        f.append(_clause("jobs.started_at", date_from=since, exists=True))
    return count(f, api_key)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--to", required=True, help="Target company B (measure inflow to).")
    ap.add_argument("--from", dest="sources", default="", help="Comma-separated candidate source companies A.")
    ap.add_argument("--controls", default="", help="Comma-separated non-peer controls (sanity floor).")
    ap.add_argument("--since", default="2024-01-01", help="Activity floor (YYYY-MM-DD). Default 2024-01-01.")
    ap.add_argument("--sample", type=int, default=0, help="Download N recent joiners to validate direction (costs N credits).")
    args = ap.parse_args()

    key = os.environ.get("LIVEDATA_API_KEY", "")
    if not key:
        print("LIVEDATA_API_KEY not set", file=sys.stderr); sys.exit(1)

    B = args.to.strip()
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    controls = [s.strip() for s in args.controls.split(",") if s.strip()]

    try:
        total_B = count([_clause("jobs.company.name", [B])], key)
        recent_B = count([_clause("jobs.company.name", [B]), _clause("jobs.started_at", date_from=args.since, exists=True)], key) if args.since else total_B
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"API error: {e}", file=sys.stderr); sys.exit(1)

    print(f"\n[{B}] panel population: {total_B:,} ever-employed  |  {recent_B:,} with a job since {args.since}")
    print(f"\n[FEEDER CO-OCCURRENCE → {B}]  (people with BOTH an A-job and a {B}-job, active since {args.since}; FREE size:0 counts)")
    rows = []
    for a in sources:
        try:
            c = cooccur(a, B, args.since, key)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  ! {a}: {e}"); continue
        rows.append((a, c))
    rows.sort(key=lambda r: -r[1])
    mx = max((c for _, c in rows), default=1) or 1
    for a, c in rows:
        share = (100 * c / total_B) if total_B else 0
        bar = "█" * max(1, round(30 * c / mx)) if c else ""
        print(f"  {c:>6,}  {share:4.1f}%  {a[:26]:<26} {bar}")
    if controls:
        print(f"  -- controls (expect near-zero) --")
        for a in controls:
            try:
                c = cooccur(a, B, args.since, key)
            except Exception:
                c = -1
            print(f"  {c:>6,}         {a[:26]:<26}")

    if args.sample > 0:
        print(f"\n[DIRECTED SAMPLE] downloading {args.sample} recent {B} joiners (costs ~{args.sample} credits)…")
        body = {"size": args.sample, "past_jobs": 6,
                "sort_by": "-company_change_detected_at",
                "filters": [{"operator": "and", "filters": [
                    _clause("jobs.company.name", [B]),
                    _clause("jobs.started_at", date_from=args.since, exists=True)]}]}
        data = _post(body, key)
        people = data.get("people", [])
        from_hist = {}
        moves = []
        for p in people:
            jobs = p.get("jobs") or []
            # jobs are most-recent-first; find the B job, then the next (older) different company.
            bidx = next((i for i, j in enumerate(jobs) if (j.get("company") or {}).get("name") == B), None)
            if bidx is None:
                continue
            # Client-side guard: only count if the B-job itself started in-window (server
            # filter is loose — it matches any job started since `since`, not the B-job).
            bstart = (jobs[bidx].get("started_at") or "")[:10]
            if args.since and bstart and bstart < args.since:
                continue
            prior = next((j for j in jobs[bidx + 1:] if (j.get("company") or {}).get("name") and (j.get("company") or {}).get("name") != B), None)
            fc = (prior.get("company") or {}).get("name") if prior else "(none/first job)"
            from_hist[fc] = from_hist.get(fc, 0) + 1
            bjob = jobs[bidx]
            moves.append((bjob.get("started_at", "")[:7], p.get("name"), fc, bjob.get("title")))
        moves.sort(reverse=True)
        for d, name, fc, title in moves[:40]:
            print(f"  {d}  {str(name)[:24]:<24}  {str(fc)[:24]:<24} → {B}  ({str(title)[:28]})")
        print(f"\n  [SAMPLE FROM-DISTRIBUTION]")
        for fc, n in sorted(from_hist.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>3}  {fc}")


if __name__ == "__main__":
    main()
