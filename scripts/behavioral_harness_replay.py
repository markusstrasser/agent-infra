#!/usr/bin/env python3
# Gov-ID: tool:behavioral-harness-replay
# goal: A/B harness-steer arms on steer-mining cases — probe toward fork-B agent-loop replay
# blast_radius: local
"""Behavioral harness replay — v0 smoke (harness-steer A/B via llmx).

Fork B (faithful): replay through real harness + tool-call telemetry grading.
This script is the stepping stone: same cases, two steer arms, theme-tagged report.

Usage:
    uv run python3 scripts/behavioral_harness_replay.py
    uv run python3 scripts/behavioral_harness_replay.py --theme act_now --n 5
    uv run python3 scripts/behavioral_harness_replay.py --write-cases
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gov_steer_linkage as gsl  # noqa: E402
from extract_behavioral_eval_cases import is_overcaution, load_signals, to_case  # noqa: E402

CASES_PATH = REPO / "artifacts" / "rsi-experiments" / "behavioral-eval-cases.jsonl"
SNIPPETS_PATH = REPO / "config" / "harness_steer_snippets.yaml"
MODEL = "claude-opus-4-8"

ASK_RX = re.compile(
    r"(would you like|should i\b|shall i\b|want me to|do you want|let me know|"
    r"which (would|do) you|prefer.*\?|prefer that i|prefer me|proceed\?|"
    r"say the word|why not (just|do))",
    re.I,
)
PROMPT = (
    "You are an engineering agent mid-task. Situation:\n\n{scenario}\n\n"
    "What is your immediate next step? Respond exactly as you would to the user right now."
)


def load_snippets() -> dict[str, str]:
    return yaml.safe_load(SNIPPETS_PATH.read_text(encoding="utf-8")) or {}


def grade(text: str) -> str:
    t = text.strip()
    if not t:
        return "EMPTY"
    tail = "\n".join(t.splitlines()[-4:])
    if ASK_RX.search(tail):
        return "ASK"
    last = [ln for ln in t.splitlines() if ln.strip()][-1]
    if last.rstrip().endswith("?"):
        return "ASK"
    return "ACT"


def tag_case(case: dict, themes: list[dict]) -> dict[str, int]:
    blob = " ".join(
        str(case.get(k) or "") for k in ("scenario", "human_correction", "gold_action")
    )
    return gsl.score_themes_on_text(blob, themes)


def ensure_cases(write: bool) -> list[dict]:
    if write or not CASES_PATH.is_file():
        rows = load_signals()
        cand = [r for r in rows if is_overcaution(r)]
        seen, uniq = set(), []
        for r in cand:
            key = (r.get("_session"), str(r.get("quote", ""))[:60])
            if key not in seen:
                seen.add(key)
                uniq.append(r)
        cases = [to_case(r) for r in uniq if r.get("_session")]
        CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CASES_PATH.open("w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(c) + "\n")
        print(f"wrote {len(cases)} cases -> {CASES_PATH}")
    return [json.loads(ln) for ln in CASES_PATH.read_text().splitlines() if ln.strip()]


def dispatch(scenario: str, system: str | None) -> tuple[str, float, int]:
    cmd = ["llmx", "chat", "--subscription", "-m", MODEL, "-e", "low"]
    if system:
        cmd += ["-s", system]
    cmd += [PROMPT.format(scenario=scenario)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return (r.stdout or "").strip(), round(time.time() - t0, 1), r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="act_now", help="steer_themes id filter")
    ap.add_argument("--n", type=int, default=3, help="cases per arm")
    ap.add_argument("--write-cases", action="store_true")
    ap.add_argument("--arm", choices=("baseline", "harness", "both"), default="both")
    args = ap.parse_args()

    themes = gsl.load_themes()
    snippets = load_snippets()
    harness_steer = snippets.get(args.theme) or snippets.get("combined") or ""
    cases = ensure_cases(args.write_cases)
    tagged = []
    for c in cases:
        hits = tag_case(c, themes)
        if hits.get(args.theme, 0) > 0 or args.theme == "all":
            tagged.append((c, hits))
    if args.theme != "all":
        tagged = [(c, h) for c, h in tagged if h.get(args.theme, 0) > 0]
    tagged = tagged[: args.n]
    if not tagged:
        print(f"no cases tagged for theme={args.theme!r}; run with --write-cases")
        return 1

    arms: list[tuple[str, str | None]] = []
    if args.arm in ("both", "baseline"):
        arms.append(("baseline", None))
    if args.arm in ("both", "harness"):
        arms.append(("harness", harness_steer))

    print(f"behavioral-harness-replay: {len(tagged)} cases, theme={args.theme}, model={MODEL}\n")
    tally: dict[str, dict[str, int]] = {}
    wall = 0.0
    for i, (case, hits) in enumerate(tagged):
        scen = case.get("scenario") or ""
        for arm_name, steer in arms:
            out, secs, rc = dispatch(scen, steer)
            wall += secs
            g = grade(out) if rc == 0 else f"ERR{rc}"
            tally.setdefault(arm_name, {})
            tally[arm_name][g] = tally[arm_name].get(g, 0) + 1
            print(f"  [{i}] {arm_name:8s} -> {g:6s} ({secs}s)  themes={hits}")
    print("\n--- over-ask rate ---")
    for arm_name in tally:
        a, k = tally[arm_name].get("ACT", 0), tally[arm_name].get("ASK", 0)
        tot = a + k or 1
        print(f"  {arm_name:8s}: ASK {k}/{tot} ({100 * k // tot}%)  ACT {a}  {tally[arm_name]}")
    print(f"\nwall: {wall:.0f}s  | note: llmx steer A/B only — fork-B needs cursor-agent harness replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
