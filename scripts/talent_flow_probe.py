#!/usr/bin/env python3
"""Talent-flow tracker (Exa prototype) — dated A→B job transitions for an industry.

Granularity #1 from research/2026-06-08-talent-flow-intelligence-feasibility.md:
individual high-signal moves, parsed from the dated employment timeline Exa
embeds in each person record. NOT aggregate net-flows (that needs a longitudinal
panel — Live Data / Coresignal / Revelio; see the memo).

Decomposition: Exa structured-summary does the messy profile→jobs parse (semantic);
this script does the transition extraction + flow aggregation (deterministic).

Usage:
    export EXA_API_KEY=...   # already in ~/.zshenv
    python3 scripts/talent_flow_probe.py --companies "Anthropic" --since 2024-01
    python3 scripts/talent_flow_probe.py \
        --companies "Anthropic,Mistral AI,Safe Superintelligence,Thinking Machines Lab" \
        --since 2025-01 --per-company 25 --json /tmp/flows.json

Personal-research use only (LinkedIn-derived data via Exa; see memo §Compliance).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

EXA_URL = "https://api.exa.ai/search"

# Exa structured-summary schema: pull a person's dated job history out of the profile.
PERSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "current_company": {"type": "string"},
        "current_title": {"type": "string"},
        "jobs": {
            "type": "array",
            "description": "Employment history, most recent first.",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start": {"type": "string", "description": "YYYY-MM or YYYY"},
                    "end": {"type": "string", "description": "YYYY-MM, YYYY, or 'present'"},
                },
            },
        },
    },
}


def _ok(m): print(f"  ✓ {m}")
def _warn(m): print(f"  ! {m}")
def _header(s): print(f"\n[{s}]")


def exa_people_search(query, num_results, api_key, timeout=45):
    """POST Exa /search for people profiles with per-result structured summary."""
    payload = {
        "query": query,
        "type": "neural",
        "category": "linkedin profile",
        "numResults": num_results,
        "contents": {"summary": {"schema": PERSON_SCHEMA}},
    }
    req = urllib.request.Request(
        EXA_URL,
        data=json.dumps(payload).encode(),
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _ym(s):
    """Normalize 'YYYY-MM' / 'YYYY' / 'present' → sortable key; None if unparseable."""
    if not s:
        return None
    s = str(s).strip().lower()
    if s in ("present", "current", "now"):
        return "9999-99"
    parts = s.replace("/", "-").split("-")
    try:
        y = int(parts[0])
    except (ValueError, IndexError):
        return None
    m = 1
    if len(parts) > 1:
        try:
            m = int(parts[1])
        except ValueError:
            m = 1
    return f"{y:04d}-{m:02d}"


def extract_inbound_move(person, target_company):
    """Find the transition INTO target_company: prior job → target. Returns dict or None."""
    jobs = person.get("jobs") or []
    if not jobs:
        return None
    tnorm = target_company.lower()
    # Find the target-company tenure (and its start), then the job that preceded it.
    target_jobs = [j for j in jobs if tnorm in (j.get("company") or "").lower()]
    if not target_jobs:
        return None
    # Earliest target start = when they joined the target.
    target_starts = [k for k in (_ym(j.get("start")) for j in target_jobs) if k]
    join = min(target_starts) if target_starts else None
    # Prior = the job with the latest start strictly before the target join.
    prior = None
    for j in jobs:
        c = (j.get("company") or "").lower()
        if tnorm in c:
            continue
        ks = _ym(j.get("start"))
        if ks and (join is None or ks < join):
            pk = _ym(prior.get("start")) if prior else None
            if prior is None or pk is None or ks > pk:
                prior = j
    if prior is None:
        return None
    return {
        "name": person.get("name"),
        "from_company": prior.get("company"),
        "from_title": prior.get("title"),
        "to_company": target_company,
        "to_title": person.get("current_title") or (target_jobs[0].get("title")),
        "joined": join,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--companies", required=True, help="Comma-separated target companies (track inflows TO these).")
    ap.add_argument("--from", dest="from_peers", default="", help="Optional comma-separated 'from' companies to bias the query.")
    ap.add_argument("--since", default="2024-01", help="Only report moves with join date >= this (YYYY-MM). Default 2024-01.")
    ap.add_argument("--per-company", type=int, default=20, help="Exa results per target company (default 20, max 100).")
    ap.add_argument("--json", dest="json_out", default="", help="Write full results to this JSON path.")
    args = ap.parse_args()

    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        print("EXA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    targets = [c.strip() for c in args.companies.split(",") if c.strip()]
    peers = [c.strip() for c in args.from_peers.split(",") if c.strip()]
    since = _ym(args.since)
    n = max(5, min(100, args.per_company))

    all_moves = []
    flow = {}  # (from, to) -> count
    seen = set()

    for company in targets:
        if peers:
            q = f"engineers, researchers, and leaders who recently joined {company} from {', '.join(peers)}"
        else:
            q = f"engineers, researchers, and leaders who recently joined {company}"
        _header(f"{company} — querying Exa")
        try:
            data = exa_people_search(q, n, api_key)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            _warn(f"Exa call failed: {e}")
            continue
        results = data.get("results", [])
        _ok(f"{len(results)} profiles returned")
        parsed = 0
        for r in results:
            summary = r.get("summary")
            if not summary:
                continue
            try:
                person = json.loads(summary)
            except (json.JSONDecodeError, TypeError):
                continue
            person["_url"] = r.get("url")
            move = extract_inbound_move(person, company)
            if not move:
                continue
            if since and move["joined"] and move["joined"] < since:
                continue
            key = (move["name"], move["to_company"])
            if key in seen:
                continue
            seen.add(key)
            move["url"] = person["_url"]
            all_moves.append(move)
            fc = (move["from_company"] or "?").strip()
            flow[(fc, company)] = flow.get((fc, company), 0) + 1
            parsed += 1
        _ok(f"{parsed} dated inbound moves extracted (since {args.since})")

    # ── Report ──
    all_moves.sort(key=lambda m: (m.get("joined") or ""), reverse=True)

    _header(f"RECENT MOVES ({len(all_moves)} total, since {args.since})")
    for m in all_moves:
        j = m.get("joined") or "?"
        print(f"  {j}  {m['name']:<26}  {(m['from_company'] or '?')[:24]:<24} → {m['to_company']}")

    _header("FLOW MATRIX (from → to : count)")
    for (fc, tc), cnt in sorted(flow.items(), key=lambda kv: -kv[1]):
        bar = "█" * min(cnt, 30)
        print(f"  {cnt:>3}  {fc[:28]:<28} → {tc:<24} {bar}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"generated": date.today().isoformat(), "since": args.since,
                       "moves": all_moves,
                       "flows": [{"from": fc, "to": tc, "count": c} for (fc, tc), c in flow.items()]},
                      f, indent=2)
        _ok(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
