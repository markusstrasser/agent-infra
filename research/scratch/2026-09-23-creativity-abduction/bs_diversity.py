#!/usr/bin/env python3
"""Screening check: old vs new /brainstorm Step-2 generation payload — idea diversity + bridge-framing rate.

Diversity = mean pairwise cosine distance and Vendi score of idea embeddings (emb, gte-modernbert).
    uv run --with numpy python3 bs_diversity.py gen      # run SUT calls
    uv run --with numpy python3 bs_diversity.py score    # embed + score
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "bs_runs"
OLD = ("First, name 4–6 broad, mutually distant semantic DIRECTIONS the solution could take (directions, not ideas). "
       "Then generate 15 genuinely different approaches that fill those directions — and give a probability/confidence "
       "for each approach. Report the distribution; do not pre-rank or filter. No feasibility filtering yet. "
       "Do NOT adopt an expert/authority persona.")
NEW = "Optimize for originality, not the most effective or expected answer. " + OLD
TOPICS = {
    "t1": "How should a solo developer's agent harness decide which past-session lessons to surface at the start of a new coding session, without bloating context?",
    "t2": "Design a way to detect when a long-running autonomous research agent has stopped making progress, before it burns its budget.",
    "t3": "How could a personal genomics pipeline let its owner trust results from stages they cannot inspect themselves?",
}
SPEC = ('\n\nFinish with a ```json fence holding {"ideas": [{"direction": "...", "idea": "<one paragraph: the mechanism>", '
        '"probability": <0-1>}, ...]} with exactly 15 ideas.')
BRIDGE = re.compile(r"\b(bridg\w*|unif\w*|integrat\w*|combin\w*|hybrid|connect\w* (?:the|existing|both))\b", re.I)


def call(arm: str, topic: str, rep: int) -> None:
    path = OUT / f"{arm}_{topic}_r{rep}.json"
    if path.exists():
        return
    prompt = f"{TOPICS[topic]}\n\n{OLD if arm == 'old' else NEW}{SPEC}"
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    p = subprocess.run(["claude", "-p", "--safe-mode", "--tools", "", "--model", "claude-opus-5-5",
                        "--effort", "low", "--output-format", "json", "--", prompt],
                       capture_output=True, text=True, timeout=900, env=env, cwd="/private/tmp")
    d = json.loads(p.stdout)
    m = re.findall(r"```json\s*(\{.*?\})\s*```", d["result"], re.S)
    ideas = json.loads(m[-1])["ideas"] if m else []
    path.write_text(json.dumps({"ideas": ideas, "out_tok": d["usage"]["output_tokens"],
                                "served": list(d.get("modelUsage", {}))}))


def gen() -> None:
    OUT.mkdir(exist_ok=True)
    jobs = [(a, t, r) for a in ("old", "new") for t in TOPICS for r in (1, 2)]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda j: call(*j), jobs))


def score() -> None:
    import numpy as np
    rows, keys = [], []
    for f in sorted(OUT.glob("*.json")):
        for i, idea in enumerate(json.loads(f.read_text())["ideas"]):
            rows.append({"id": f"{f.stem}#{i}", "text": idea["idea"]})
            keys.append(f.stem)
    src = OUT / "ideas.jsonl"
    src.write_text("".join(json.dumps(r) + "\n" for r in rows))
    idx = OUT / "idx"
    subprocess.run(["emb", "embed", str(src), "-o", str(idx), "--app-git-commit", "none", "--emb-git-commit", subprocess.run(["git", "-C", str(Path.home() / "Projects/emb"), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()], check=True, capture_output=True)
    gen_dir = max((p.parent for p in idx.rglob("embeddings.npy")), key=lambda p: p.stat().st_mtime)
    entries = [json.loads(line) for line in (gen_dir / "entries.jsonl").open()]
    emb = np.load(gen_dir / "embeddings.npy")
    vec = {e["id"]: v for e, v in zip(entries, np.asarray(emb))}
    res: dict = {}
    for f in sorted(OUT.glob("*_r*.json")):
        d = json.loads(f.read_text())
        X = np.stack([vec[f"{f.stem}#{i}"] for i in range(len(d["ideas"]))])
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        S = X @ X.T
        n = len(X)
        mpd = 1 - (S.sum() - n) / (n * (n - 1))
        ev = np.clip(np.linalg.eigvalsh(S / n), 1e-12, None)
        vendi = float(np.exp(-(ev * np.log(ev)).sum()))
        bridge = sum(bool(BRIDGE.search(i["idea"])) for i in d["ideas"]) / n
        arm, topic, _ = f.stem.split("_")
        res.setdefault(arm, []).append((topic, n, mpd, vendi, bridge, d["out_tok"]))
        print(f"{f.stem:12} n={n:2} mean_pair_dist={mpd:.3f} vendi={vendi:5.2f} bridge_rate={bridge:.2f} out_tok={d['out_tok']}")
    for arm, rs in res.items():
        a = np.array([r[2:] for r in rs])
        print(f"{arm}: mean_pair_dist={a[:,0].mean():.3f} vendi={a[:,1].mean():.2f} bridge={a[:,2].mean():.2f} out_tok={a[:,3].mean():.0f}")


if __name__ == "__main__":
    {"gen": gen, "score": score}[sys.argv[1]]()
