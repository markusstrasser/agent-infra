#!/usr/bin/env python3
# Gov-ID: tool:extract-behavioral-eval-cases
# goal: turn steer-mining corrections into reconstructible behavioral-eval cases.
#       Each human correction is a GROUND-TRUTH label (revealed preference), not a
#       judge opinion — the bridge the evals repo lacks (survey 2026-06-19).
# blast_radius: local (writes an artifact; reads transcripts read-only)
"""Steer-signals -> behavioral-eval case seeds (over-caution / scope-authorization).

A case = (scenario the agent faced, what it DID, the human correction = label, gold action).
The over-ask core: agent ASKED / OFFERED / DEFERRED / WAITED when scope was already
authorized. We reconstruct the pre-correction assistant turn from the transcript so the
case carries the real context, not just the one-line summary.

Usage:
    uv run python3 scripts/extract_behavioral_eval_cases.py            # stats + 2 reconstructions
    uv run python3 scripts/extract_behavioral_eval_cases.py --write OUT.jsonl
"""
import argparse, glob, json
from pathlib import Path

PROJ = Path.home() / ".claude/projects"
REPO = Path(__file__).resolve().parent.parent


def steer_signal_paths() -> list[Path]:
    paths = sorted((REPO / "artifacts" / "observe").glob("*-steer-signals.jsonl"))
    probe_dir = Path.home() / ".claude" / "steer-mining"
    if probe_dir.is_dir():
        paths += sorted(probe_dir.glob("probe-*.jsonl"))
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen and p.is_file():
            seen.add(key)
            out.append(p)
    return out

# tighter over-caution core: the agent's ACTION was an ask/offer/defer/wait/stop/fork,
# AND the human's correction pushed toward acting / proceeding now.
DID_TIMID = ("asked", "offered", "waiting", "stopped", "deferred", "presented an askuserquestion",
             "ended with 'want", "want me to", "whether to proceed", "optional follow", "framed remaining")
GOLD_ACT = ("execute", "implement it", "just do", "why not", "act now", "proceed", "do it now",
            "now, not more", "without asking", "see it through", "fix baseline", "green the")

def load_signals():
    rows = []
    for p in steer_signal_paths():
        rows += [json.loads(l) for l in p.open() if l.strip()]
    return rows

def is_overcaution(r):
    before = str(r.get("before", "")).lower()
    gold = (str(r.get("vector", "")) + " " + str(r.get("quote", ""))).lower()
    timid = any(k in before for k in DID_TIMID)
    act = any(k in gold for k in GOLD_ACT)
    return timid and act

def transcript_path(sid):
    if not sid:
        return None
    hits = glob.glob(str(PROJ / f"*/{sid}.jsonl"))
    return hits[0] if hits else None

def reconstruct_pre_correction(sid, human_quote):
    """Find the assistant turn JUST BEFORE the human's correction quote in the transcript."""
    p = transcript_path(sid)
    if not p:
        return None
    needle = human_quote.strip()[:40].lower()
    prev_assistant = None
    for line in open(p):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        role = ev.get("message", {}).get("role") or ev.get("role")
        content = ev.get("message", {}).get("content") or ev.get("content") or ""
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        content = str(content)
        if role == "user" and needle and needle in content.lower():
            return (prev_assistant or "")[:1200]
        if role == "assistant":
            prev_assistant = content
    return None

def to_case(r):
    sid = r.get("_session")
    return {
        "id": f"{sid[:8]}-{abs(hash(r.get('quote',''))) % 10000:04d}" if sid else None,
        "session": sid,
        "type": r.get("type"),
        "scenario": r.get("before"),          # what the agent faced + did (the over-ask)
        "human_correction": r.get("quote"),   # GROUND-TRUTH label
        "gold_action": r.get("vector"),        # corrected direction
        "transcript": transcript_path(sid),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", metavar="OUT.jsonl")
    args = ap.parse_args()

    rows = load_signals()
    cand = [r for r in rows if is_overcaution(r)]
    # dedup by (session, first 60 chars of correction)
    seen, uniq = set(), []
    for r in cand:
        key = (r.get("_session"), str(r.get("quote", ""))[:60])
        if key not in seen:
            seen.add(key); uniq.append(r)

    print(f"merged signals:        {len(rows)}")
    print(f"over-caution core:     {len(cand)}  (deduped: {len(uniq)})")
    print(f"transcript recoverable: {sum(1 for r in uniq if transcript_path(r.get('_session')))}/{len(uniq)}")

    if args.write:
        cases = [to_case(r) for r in uniq if r.get("_session")]
        with open(args.write, "w") as fh:
            for c in cases:
                fh.write(json.dumps(c) + "\n")
        print(f"\nwrote {len(cases)} cases -> {args.write}")

    print("\n=== reconstruction proof (2 cases: the real pre-correction agent turn) ===")
    shown = 0
    for r in uniq:
        if shown >= 2:
            break
        ctx = reconstruct_pre_correction(r.get("_session"), str(r.get("quote", "")))
        if ctx:
            print(f"\n[{r.get('type')}] human said: {str(r.get('quote'))[:80]}")
            print(f"  gold: {str(r.get('vector'))[:80]}")
            print(f"  --- agent's actual turn just before (reconstructed) ---")
            print("  " + ctx.replace("\n", "\n  ")[:700])
            shown += 1
    if shown == 0:
        print("(no quote matched a transcript turn — needle-match needs tuning; summaries still usable)")

if __name__ == "__main__":
    main()
