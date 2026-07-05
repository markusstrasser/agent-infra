#!/usr/bin/env python3
# Gov-ID: tool:blindspot-miner
# goal: surface the moments the HUMAN had to correct the loop, CLASSIFIED by direction
#       (timid / wrong / missed-context / taste) so each becomes the right kind of fix.
# verifier: scripts/tests/test_supervision_taxonomy.py
# blast_radius: local
"""blindspot_miner.py — the standing RSI miner, now direction-aware.

The directive (Markus, 2026-06-14): "every time I mention something, ask why the loop
didn't find it, and meta-improve a way for the next loop to find stuff like it." Every
user correction is a labeled example of a loop miss. This mines recent sessions for those
moments and CLASSIFIES each via the single-source taxonomy (`supervision_taxonomy.py`).

Why classification matters (the upgrade): a correction's TYPE determines the fix.
  • over_caution  (RAISE_AUTONOMY) → loosen / act more — the agent was timid, not wrong.
  • rediscovery   (GROW_COVERAGE)  → a detector — the agent missed existing context.
  • error_correction (REDUCE_ERROR)→ a correctness guardrail — the agent was wrong.
  • taste_steer   (AMPLIFY_TASTE)  → produce options, keep the human as judge.
The old miner saw only the rediscovery class and reported an undifferentiated count, so
the loop could not tell "be more careful" from "stop hesitating." It was, in particular,
BLIND to over_caution — the failure mode most opposed to autonomy.

Division of labor:
  • supervision-kpi.py = cheap regex TREND over the same taxonomy ($0, agent-infra env).
  • THIS = the QUALITY miner — emb-contrastive (catches semantic paraphrases at precision),
    run in emb's env (`uv run --project ~/Projects/emb`) so agent-infra never inherits torch.

DETECT here; CONVERT (LLM "what fix would this direction call for?") is the interactive tier.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import supervision_taxonomy as tax
from common.transcript_text import is_harness_injected

PROJECTS = Path.home() / ".claude" / "projects"

SKIP = re.compile(
    r"^(<task-notification>|<command-name>|<command-message>|Base directory for this skill:|Stop hook feedback:|<system-reminder>)",
    re.IGNORECASE,
)


def _user_text(obj: dict) -> str | None:
    if obj.get("type") != "user" or obj.get("toolUseResult"):
        return None
    # Compaction summaries / meta expansions re-quote old corrections — mining
    # them double-counts flags (duplicate imagegen rows in the 2026-07-05 digest).
    if is_harness_injected(obj):
        return None
    content = (obj.get("message") or {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str) or not content.strip():
        return None
    t = content.strip()
    return None if SKIP.match(t) else t


def recent_sessions(days: int) -> list[Path]:
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()
    out = []
    if not PROJECTS.is_dir():
        return out
    for proj in PROJECTS.iterdir():
        if not proj.is_dir():
            continue
        for j in proj.glob("*.jsonl"):
            try:
                if j.stat().st_mtime >= cutoff:
                    out.append(j)
            except OSError:
                pass
    return out


def gather_candidates(days: int) -> list[dict]:
    cands = []
    for j in recent_sessions(days):
        project = j.parent.name.replace("-Users-alien-Projects-", "")
        try:
            with open(j, errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = _user_text(obj)
                    if not t or not tax.PREFILTER.search(t[:300] + t[-200:]):
                        continue
                    cands.append({
                        "session": j.stem[:8], "project": project,
                        "date": (obj.get("timestamp") or "")[:10],
                        "text": t, "lead": (t[:250] + " ¦ " + t[-200:]),
                    })
        except OSError:
            continue
    return cands


def score(cands: list[dict]) -> list[dict]:
    """Flag = taxonomy regex tier-0 hit (precision) OR emb-contrastive match (recall).
    Each flag carries its type + direction + inspectable evidence."""
    from emb.embed import EmbeddingEngine
    eng = EmbeddingEngine()

    emb_matches = tax.classify_emb_batch([c["lead"] for c in cands], eng) if cands else []
    flags = []
    for c, em in zip(cands, emb_matches):
        m = tax.classify_regex(c["text"]) or em  # regex tier-0 wins (high precision); emb fills recall
        if m:
            flags.append({
                **c, "type": m.type_id, "direction": m.direction,
                "method": m.method, "score": float(m.score), "evidence": m.evidence,
            })
    flags.sort(key=lambda x: x["score"], reverse=True)
    return flags


def render(flags: list[dict], days: int, n_cands: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    L = [f"# Blindspot misses — {stamp} (last {days}d)", ""]
    if not flags:
        L.append(f"_No correction flags in {n_cands} candidate messages. If the window had real "
                 f"misses the human caught, the seeds/threshold need widening — not a clean bill of health._")
        return "\n".join(L) + "\n"

    by_dir = Counter(f["direction"] for f in flags)
    by_type = Counter(f["type"] for f in flags)
    L.append(f"**{len(flags)} corrections the human had to make** (of {n_cands} candidates), "
             f"classified by the direction each implies:\n")
    # Direction is the headline — it says what KIND of fix each cluster calls for.
    dir_label = {
        "raise_autonomy": "RAISE_AUTONOMY (agent was timid → loosen/act more)",
        "grow_coverage": "GROW_COVERAGE (agent missed context → add detector)",
        "reduce_error": "REDUCE_ERROR (agent was wrong → correctness guardrail)",
        "amplify_taste": "AMPLIFY_TASTE (missed taste → options, keep human judge)",
    }
    for d, n in by_dir.most_common():
        types = ", ".join(f"{t}={by_type[t]}" for t in by_type if tax.BY_ID[t].direction.value == d)
        L.append(f"- **{dir_label.get(d, d)}** — {n}  ({types})")
    L.append("")
    by_proj = Counter(f["project"] for f in flags)
    L.append("By project: " + ", ".join(f"{p}={n}" for p, n in by_proj.most_common()) + "\n")
    L.append("Top flags (sorted by confidence):\n")
    for f in flags[:25]:
        snip = re.sub(r"\s+", " ", f["text"])[:130]
        L.append(f"- `{f['score']:+.2f}` [{f['type']}/{f['method']}] **{f['project']}/{f['session']}** "
                 f"({f['date']}): {snip}")
    if len(flags) > 25:
        L.append(f"\n_(+{len(flags) - 25} more)_")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Standing RSI miner: classify the corrections the human had to make.")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / ".claude" / "blindspot-digest.md"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-file", action="store_true", help="skip digest file write (pulse tick owns surfacing)")
    args = ap.parse_args()

    cands = gather_candidates(args.days)
    flags = score(cands)
    if args.json:
        # Direction enums → values for JSON
        print(json.dumps([{**f, "direction": f["direction"].value if hasattr(f["direction"], "value") else f["direction"]} for f in flags], indent=2))
        return 0
    digest = render(flags, args.days, len(cands))
    if not args.no_file:
        out = Path(args.out)
        if flags:
            out.write_text(digest)
        elif out.exists():
            out.unlink()  # no-noise: a stale "all clear" digest is itself drift
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
