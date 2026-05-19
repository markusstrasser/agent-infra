#!/usr/bin/env python3
"""Random-sample re-verifier for subagent verdict files.

Catches the over-confident-negation failure mode: a fact-check subagent
confidently flags something FALSE/PARTIAL when a re-fetch would confirm it
TRUE (e.g. Victoria-In-Monte-Oliveti — subagent said Victoria didn't set
this responsory; Wikipedia's 1585 list shows he did).

Reads a verdicts JSON file (any subagent's output that has a list of
{verdict, evidence_url, load_bearing_claim} dicts), picks a random 10%
sample (always including ALL FALSE/PARTIAL verdicts since they are the
high-stakes minority), re-fetches each evidence URL, asks: does this page
still support the verdict? Flags disagreements for human review.

Usage:
    python3 verify-subagent-claims.py /tmp/partc-batch1-verdicts.json
    python3 verify-subagent-claims.py /tmp/partc-batch1-verdicts.json --key gap_verdicts
    python3 verify-subagent-claims.py /tmp/partc-batch1-verdicts.json --frac 0.15

Output is a brief report (markdown) listing which verdicts to manually
re-check before applying caption fixes.

Why this exists: spot-checking is what the parent agent SHOULD do after
every subagent run, but it's labor-intensive and rarely happens. This
script does the bookkeeping (which 10%, which URLs, which verdicts) so the
human only needs to read a short flag list.

Note: this script does NOT actually re-fetch (that's Anthropic-API-side
work — agent reading the URL via WebFetch). It produces the SAMPLE LIST
and the questions to ask. Run it, then have the parent agent re-verify
the flagged subset via WebFetch.
"""
import argparse
import json
import pathlib
import random
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("verdicts_file", type=pathlib.Path)
    parser.add_argument("--key", default=None, help="Top-level key holding the verdict list (auto-detected if not given)")
    parser.add_argument("--frac", type=float, default=0.10, help="Random-sample fraction of TRUE verdicts (default 0.10)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--out", type=pathlib.Path, default=None, help="Output report path (default: stdout)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = json.loads(args.verdicts_file.read_text())

    # Auto-detect verdict list key
    if args.key:
        verdicts = data[args.key]
    else:
        candidates = [k for k, v in data.items() if isinstance(v, list) and v and isinstance(v[0], dict) and "verdict" in v[0]]
        if not candidates:
            print(f"ERROR: no verdict list found in {args.verdicts_file}", file=sys.stderr)
            sys.exit(2)
        if len(candidates) > 1:
            print(f"WARN: multiple candidate keys ({candidates}); using {candidates[0]}", file=sys.stderr)
        verdicts = data[candidates[0]]

    # Partition by verdict bucket
    high_stakes = [v for v in verdicts if v.get("verdict") in ("FALSE", "PARTIALLY_TRUE", "PARTIAL", "PARTIALLY_VERIFIED", "UNCERTAIN")]
    true_verdicts = [v for v in verdicts if v.get("verdict") in ("TRUE", "VERIFIED")]

    # Sample TRUE verdicts (random-frac) — false positives risk
    n_true_sample = max(1, int(len(true_verdicts) * args.frac))
    true_sample = random.sample(true_verdicts, min(n_true_sample, len(true_verdicts)))

    # Compose verify list — high-stakes always included
    verify_list = high_stakes + true_sample

    # Report
    lines = []
    lines.append(f"# Subagent claim re-verification list")
    lines.append("")
    lines.append(f"Source: `{args.verdicts_file}`  ")
    lines.append(f"Total verdicts: {len(verdicts)}  ")
    lines.append(f"High-stakes (FALSE/PARTIAL/UNCERTAIN): {len(high_stakes)} — re-verify ALL")
    lines.append(f"TRUE sample at frac={args.frac}: {len(true_sample)} of {len(true_verdicts)}")
    lines.append(f"Total to re-verify: {len(verify_list)}")
    lines.append("")
    lines.append("## Items to re-verify")
    lines.append("")
    lines.append("For each: WebFetch the evidence_url, ask whether the page still supports the stated verdict. If disagreement → flag for human review.")
    lines.append("")
    for i, v in enumerate(verify_list, 1):
        rid = v.get("id", "?")
        kind = v.get("kind", "?")
        reader = v.get("reader", "?")
        vd = v.get("verdict", "?")
        claim = v.get("load_bearing_claim", "")[:140]
        url = v.get("evidence_url", "?")
        flag = "HIGH-STAKES" if v in high_stakes else "TRUE-sample"
        lines.append(f"### {i}. [{flag}] {kind}:{reader}#{rid} — claimed {vd}")
        lines.append(f"- claim: {claim}")
        lines.append(f"- url: {url}")
        if v.get("correction"):
            lines.append(f"- subagent's correction: {v['correction'][:200]}")
        lines.append("")

    report = "\n".join(lines)
    if args.out:
        args.out.write_text(report)
        print(f"Wrote {args.out} ({len(verify_list)} items to verify)")
    else:
        print(report)


if __name__ == "__main__":
    main()
