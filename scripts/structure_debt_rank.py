#!/usr/bin/env python3
"""structure_debt_rank.py — forced ranking of files most worth expensive review.

The "where do I point max reasoning?" tool. Ranks tracked source + markdown files
by a percentile-normalized composite dominated by CHANGE-FREQUENCY (churn) and
SIZE — the two signals with the strongest empirical backing for maintenance debt
(Nagappan & Ball, ICSE 2005; CodeScene hotspots). The deterministic layer does
RECALL + RANKING; an LLM is the precision filter that reads the top-N.

Design notes (see research/2026-06-13-code-health-diagnostics-for-agents.md):
- Raw file length alone is a WEAK signal (curvilinear; LOC/cyclomatic are redundant).
  We keep size as a *positive* axis because the goal here is navigation/organization
  debt (big-and-active "god files"), not defect-proneness. Pure relative churn
  (churn ÷ size) would de-prioritize large files — wrong objective for this tool.
- Graph centrality is NOT worth it at this scale; import-cycle + fan-in are the only
  graph signals that pay off (TODO axes below). Embeddings are skipped by design.

$0 / native-first: git log --numstat + line counts. No deps. Report-only.
Consumers: /upgrade pliability, /improve, a `just` top-N surface.
"""

from __future__ import annotations

import argparse
import bisect
import subprocess
from collections import defaultdict
from pathlib import Path

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".go", ".rs", ".rb", ".java", ".sql"}
MD_EXT = {".md"}
SKIP_PREFIX = (".venv/", "node_modules/", ".git/", "artifacts/", "downloads/")
# machine-generated dumps (vendor extracts, observe/audit transcripts) are not
# curated files an agent navigates — same out-of-scope class as artifacts/observe.
SKIP_SUBSTR = ("/binary-extracts/", "/artifacts/", "/observe/", "/.venv/")


def _sh(args: list[str], cwd: str) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout


def _tracked(cwd: str) -> list[str]:
    return [ln for ln in _sh(["git", "ls-files"], cwd).splitlines() if ln]


def _churn_by_file(cwd: str, days: int) -> dict[str, int]:
    out = _sh(["git", "log", f"--since={days} days ago", "--no-renames", "--numstat", "--format="], cwd)
    churn: dict[str, int] = defaultdict(int)
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        if added == "-" or deleted == "-":  # binary
            continue
        churn[path] += int(added) + int(deleted)
    return churn


def _loc(cwd: str, path: str) -> int:
    try:
        with (Path(cwd) / path).open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def _pct(values: list[int]) -> dict[int, float]:
    """Rank percentile: fraction of items <= x (0..1)."""
    s = sorted(values)
    n = len(s)
    return {v: (bisect.bisect_right(s, v) / n if n else 0.0) for v in set(values)}


def _rank(cwd: str, files: list[str], churn: dict[str, int], w_churn: float, w_size: float, top: int) -> list[dict]:
    rows = [{"file": f, "churn": churn.get(f, 0), "loc": _loc(cwd, f)} for f in files]
    if not rows:
        return []
    pc = _pct([r["churn"] for r in rows])
    ps = _pct([r["loc"] for r in rows])
    for r in rows:
        r["score"] = w_churn * pc[r["churn"]] + w_size * ps[r["loc"]]
    rows.sort(key=lambda r: (r["score"], r["loc"]), reverse=True)
    return rows[:top]


def main() -> int:
    ap = argparse.ArgumentParser(description="Forced ranking of files most worth expensive review.")
    ap.add_argument("repo", nargs="?", default=".", help="repo path (default: cwd)")
    ap.add_argument("--days", type=int, default=90, help="churn lookback window (default 90)")
    ap.add_argument("--top", type=int, default=15, help="top-N per category (default 15)")
    args = ap.parse_args()

    cwd = str(Path(args.repo).expanduser().resolve())
    files = [
        f for f in _tracked(cwd)
        if not f.startswith(SKIP_PREFIX) and not any(s in "/" + f for s in SKIP_SUBSTR)
    ]
    churn = _churn_by_file(cwd, args.days)
    code = [f for f in files if Path(f).suffix in CODE_EXT]
    md = [f for f in files if Path(f).suffix in MD_EXT]

    print(f"structure-debt rank — {cwd}  (churn window: {args.days}d)")
    print("composite = w·pct(churn) + w·pct(loc); dup / fan-in / orphan axes are TODO")
    for label, flist, wc, ws in [
        (f"CODE  (0.45 churn + 0.25 size)  [{len(code)} files]", code, 0.45, 0.25),
        (f"MARKDOWN  (0.40 churn + 0.20 size)  [{len(md)} files]", md, 0.40, 0.20),
    ]:
        print(f"\n=== {label} — top {args.top} ===")
        rows = _rank(cwd, flist, churn, wc, ws, args.top)
        print(f"  {'score':>5}  {'churn':>7}  {'loc':>6}  file")
        for r in rows:
            print(f"  {r['score']:5.2f}  {r['churn']:7d}  {r['loc']:6d}  {r['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
