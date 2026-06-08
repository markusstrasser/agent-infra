#!/usr/bin/env python3
"""Acqui-hire / acquisition cluster detector (Live Data panel).

Signal: a CLUSTER of people who joined the same target B within a tight window,
all FROM the same SMALL source company A = the fingerprint of an acqui-hire or
acquisition (a startup's team landing together). 4-from-Kumo→NVIDIA is the seed
case (research/2026-06-08-talent-flow-intelligence-feasibility.md, Rev 2026-06-08b).

Why this beats whole-company net-flow: it sidesteps function-dispersion (NVIDIA
hires everyone) — clustered same-window moves from a small source are discrete,
rare, and verifiable, not HR noise.

Credits: downloads are cached to .scratch/livedata/ — re-running the SAME
(target, since, n) is FREE after the first pull. Each NEW pull costs ~n credits
(beta cap 500/mo). size:0 counts are always free.

Usage:
    python3 scripts/acqui_hire_scan.py --targets "Databricks,Meta,NVIDIA" \
        --since 2024-06-01 --sample 80 --min-cluster 3 --small-cap 3000
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

ORG = os.environ.get("LIVEDATA_ORG_ID", "o_3daf8872")
URL = f"https://gotlivedata.io/api/people/v1/{ORG}/search"
CACHE = os.path.join(os.path.dirname(__file__), "..", ".scratch", "livedata")


def _post(body, key, timeout=60):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_joiners(target, since, n, key):
    """Download (cached) up to n recent joiners at `target` (recency-sorted)."""
    os.makedirs(CACHE, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", target.lower()).strip("-")
    path = os.path.join(CACHE, f"{slug}_{since}_{n}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f), True  # cache hit (free)
    body = {"size": n, "past_jobs": 6, "sort_by": "-company_change_detected_at",
            "filters": [{"operator": "and", "filters": [
                {"field": "jobs.company.name", "type": "must", "match_type": "exact", "string_values": [target]},
                {"field": "jobs.started_at", "type": "must", "match_type": "exists", "date_from": since}]}]}
    people = _post(body, key).get("people", [])
    with open(path, "w") as f:
        json.dump(people, f)
    return people, False  # fresh pull (billed)


def inbound(person, target, since):
    """Return (from_company, from_employee_count, join_ym) for a move INTO target, else None."""
    jobs = person.get("jobs") or []
    bidx = next((i for i, j in enumerate(jobs) if (j.get("company") or {}).get("name") == target), None)
    if bidx is None:
        return None
    bstart = (jobs[bidx].get("started_at") or "")[:10]
    if since and bstart and bstart < since:
        return None  # B-job itself not in window (server filter is loose)
    prior = next((j for j in jobs[bidx + 1:] if (j.get("company") or {}).get("name")
                  and (j.get("company") or {}).get("name") != target), None)
    if not prior:
        return None
    pc = prior.get("company") or {}
    return pc.get("name"), pc.get("employee_count"), bstart[:7]


def ym_span(months):
    """Span in months between earliest and latest YYYY-MM."""
    def k(s):
        y, m = s.split("-")[:2]
        return int(y) * 12 + int(m)
    ks = [k(m) for m in months if m and "-" in m]
    return (max(ks) - min(ks)) if ks else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets", required=True, help="Comma-separated target companies to scan.")
    ap.add_argument("--since", default="2024-06-01", help="Join-date floor YYYY-MM-DD (default 2024-06-01).")
    ap.add_argument("--sample", type=int, default=80, help="Recent joiners to pull per target (credits per NEW pull).")
    ap.add_argument("--min-cluster", type=int, default=3, help="Min same-source joiners to flag (default 3).")
    ap.add_argument("--small-cap", type=int, default=3000, help="Source headcount below this = likely acqui-hire (default 3000).")
    ap.add_argument("--window", type=int, default=9, help="Max month-span for a 'same window' cluster (default 9).")
    args = ap.parse_args()

    key = os.environ.get("LIVEDATA_API_KEY", "")
    if not key:
        print("LIVEDATA_API_KEY not set", file=sys.stderr); sys.exit(1)

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    billed = 0
    for B in targets:
        try:
            people, cached = fetch_joiners(B, args.since, args.sample, key)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"\n[{B}] API error: {e}"); continue
        if not cached:
            billed += len(people)
        # Group inbound moves by source company.
        groups = {}  # src -> {"count","emp","months":[]}
        kept = 0
        for p in people:
            mv = inbound(p, B, args.since)
            if not mv:
                continue
            kept += 1
            src, emp, ym = mv
            g = groups.setdefault(src, {"count": 0, "emp": emp, "months": []})
            g["count"] += 1
            if emp is not None:
                g["emp"] = emp
            if ym:
                g["months"].append(ym)
        tag = "CACHED(free)" if cached else f"billed {len(people)}cr"
        print(f"\n[{B}]  {kept} in-window joiners parsed from {len(people)} pulled  ({tag})")
        clusters = []
        for src, g in groups.items():
            if not src or g["count"] < args.min_cluster:
                continue
            emp = g["emp"]
            span = ym_span(g["months"])
            small = emp is not None and emp < args.small_cap
            unknown = emp is None
            acqui = (small or unknown) and span <= args.window
            clusters.append((g["count"], src, emp, span, sorted(set(g["months"])), acqui, small, unknown))
        clusters.sort(key=lambda c: (-int(c[5]), -c[0]))
        if not clusters:
            print("  (no clusters ≥ min-cluster)")
        for cnt, src, emp, span, months, acqui, small, unknown in clusters:
            emps = f"{emp:,}emp" if emp is not None else "size?"
            flag = "★ ACQUI-HIRE" if acqui else ("· big-source pipeline" if not (small or unknown) else "· dispersed")
            print(f"  {cnt:>2}× {src[:30]:<30} [{emps:>9}] span={span}mo {months}  {flag}")
    print(f"\n[credits billed this run: ~{billed}]")


if __name__ == "__main__":
    main()
