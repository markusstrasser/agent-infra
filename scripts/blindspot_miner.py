#!/usr/bin/env python3
# Gov-ID: tool:blindspot-miner
# goal: surface the moments the HUMAN had to catch a loop miss, so each becomes a
#       candidate detector — grow the loop's coverage from the supervision stream.
# verifier: null  (the loop's own blindspot-flag RATE is the objective; not yet a grader)
# blast_radius: local
"""blindspot_miner.py — the standing RSI detector.

The directive (Markus, 2026-06-14): "every time I mention something, ask why the
loop didn't find it, and metaimprove a way for the next loop to find stuff like it."
Every user flag is a labeled example of a loop miss. This mines recent sessions for
those moments — the human reproaching/correcting the agent for missing something it
should have caught (a prior decision, an existing tool, a git-log fact) — so each
becomes a candidate DETECTOR. The constitutional gradient is the RATE of these →
declining supervision.

Division of labor (probes, improvement-log 2026-06-14):
  • supervision-kpi.py = cheap regex TREND metric (43% recall, $0, agent-infra-native).
  • THIS = the QUALITY miner — emb-contrastive (the ONLY method catching semantic
    paraphrases like "how come you missed that" at high precision; regex/fuzzy hit a
    lexical ceiling). Runs in emb's env (`uv run --project ~/Projects/emb`) so
    agent-infra never inherits torch. $0 (local embeddings).

DETECT here; CONVERT (LLM "what detector would've caught this?") is the interactive
judgment tier that consumes this digest — not auto-run in the standing job.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"

# Contrastive seeds (validated in the head-to-head bench, improvement-log 2026-06-14).
# blind = the class to catch; normal = the baseline to subtract (kills the "it's all
# agent-instructions" topical similarity that sank plain sim-to-seeds).
BLIND_SEEDS = [
    "why didn't you find this bug", "did you check the git log first",
    "you should have looked at the prior decisions", "we already discussed this",
    "you didn't check what already exists", "you keep rediscovering what we built",
    "isn't there a better tool for this", "that's already in the docs / ideas",
    "go check what exists before building", "how come you missed that",
    "why are you hand-rolling this instead of using the existing tool",
]
NORMAL_SEEDS = [
    "add a test for the parser", "fix the bug in the resolver", "run the tests",
    "commit this and move on", "implement the feature", "what model are you using",
    "summarize the file", "check the tests pass before committing", "look at the PR",
    "deploy this", "go on", "do all three",
]

# Regex Tier-0 — a fast high-precision PRE-FLAG (local optimization, NOT the canonical
# definition; the real detector is contrastive). Mirrors supervision-kpi's intent.
RGX = re.compile(
    r"why (?:did|didn'?t|don'?t|aren'?t|haven'?t|wouldn'?t|didnt|dont) (?:you|the loop|it|we) (?:not |never |fail(?:ed)? to )?(?:find|catch|check|look|notice|see|spot|read|consult)"
    r"|(?:you|it) (?:should|could) have (?:found|caught|checked|looked|noticed|seen|read)"
    r"|did (?:you|the loop) (?:check|look at|read|see|notice|find|consider)"
    r"|we (?:already|just) (?:discussed|decided|did|tried|talked|covered|said)"
    r"|(?:check|look at|read|consult) the (?:git|commit|log|history|ideas|docs|decision|prior|reasoning)"
    r"|you (?:didn'?t|never|forgot to) (?:check|look|read|consult|find|catch|grep)",
    re.IGNORECASE,
)
# Loose recall-preserving pre-filter: a blindspot flag almost always has 2nd-person /
# interrogative / recollection cues. Cuts pure task-instructions before embedding.
PREFILTER = re.compile(r"\b(you|your|why|did|didn|already|check|look|miss|should|we|isn'?t|exist|forgot)\b|\?", re.I)
SKIP = re.compile(r"^(<task-notification>|<command-name>|<command-message>|Base directory for this skill:|Stop hook feedback:|<system-reminder>)", re.I)

THRESH = 0.10  # contrastive score; tuned for precision (bench: clear flags +0.19..+0.35, hard negs <0)


def _user_text(obj: dict) -> str | None:
    if obj.get("type") != "user" or obj.get("toolUseResult"):
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
                    if not t or not PREFILTER.search(t[:300] + t[-200:]):
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
    """Flag = regex Tier-0 hit OR emb-contrastive score > THRESH."""
    import numpy as np
    from emb.embed import EmbeddingEngine
    eng = EmbeddingEngine()

    def norm(xs):
        e = np.asarray(eng.embed_texts(xs), dtype=np.float32)
        return e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-9)

    B, N = norm(BLIND_SEEDS), norm(NORMAL_SEEDS)
    if cands:
        E = norm([c["lead"] for c in cands])
        cont = (E @ B.T).max(1) - (E @ N.T).max(1)
    else:
        cont = []
    flags = []
    for c, sc in zip(cands, cont):
        regex_hit = bool(RGX.search(c["lead"]))
        if regex_hit or sc > THRESH:
            flags.append({**c, "score": round(float(sc), 3), "method": "regex" if regex_hit else "emb"})
    flags.sort(key=lambda x: x["score"], reverse=True)
    return flags


def render(flags: list[dict], days: int, n_cands: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    L = [f"# Blindspot misses — {stamp} (last {days}d)", ""]
    if not flags:
        L.append(f"_No blindspot flags in {n_cands} candidate messages. If the window had real misses the human caught, the seeds/threshold need widening — not a clean bill of health._")
        return "\n".join(L) + "\n"
    L.append(f"**{len(flags)} moments the human had to catch a loop miss** (of {n_cands} candidates). "
             f"Each is a candidate detector — for recurring clusters, ask: *what check would have caught this autonomously?*\n")
    by_proj: dict[str, int] = {}
    for f in flags:
        by_proj[f["project"]] = by_proj.get(f["project"], 0) + 1
    L.append("By project: " + ", ".join(f"{p}={n}" for p, n in sorted(by_proj.items(), key=lambda x: -x[1])) + "\n")
    for f in flags[:25]:
        snip = re.sub(r"\s+", " ", f["text"])[:140]
        L.append(f"- `{f['score']:+.2f}` [{f['method']}] **{f['project']}/{f['session']}** ({f['date']}): {snip}")
    if len(flags) > 25:
        L.append(f"\n_(+{len(flags) - 25} more)_")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Standing RSI miner: surface loop misses the human had to catch.")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / ".claude" / "blindspot-digest.md"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cands = gather_candidates(args.days)
    flags = score(cands)
    if args.json:
        print(json.dumps(flags, indent=2))
        return 0
    digest = render(flags, args.days, len(cands))
    out = Path(args.out)
    if flags:
        out.write_text(digest)
    elif out.exists():
        out.unlink()  # no-noise: a stale "all clear" digest is itself drift
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
