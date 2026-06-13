#!/usr/bin/env python3
"""structure_debt_rank.py — forced ranking of files most worth expensive review.

The "where do I point max reasoning?" tool. Ranks tracked source + markdown files
by a composite of cheap deterministic signals. The deterministic layer does
RECALL + RANKING; an LLM is the precision filter that reads the top-N.

Composite (research/2026-06-13-code-health-diagnostics-for-agents.md):
  CODE      = 0.45 freq + 0.25 size + 0.20 near-dup + 0.10 fan-in   [flag: import cycle]
  MARKDOWN  = 0.40 freq + 0.25 near-dup + 0.20 size + 0.15 orphan/stale [flag: broken [[wikilink]]]

Design rationale:
- The change signal is COMMIT FREQUENCY (distinct commits touching the file in the
  window), NOT line-churn — line-churn equals size for newly-added files and would
  rank "big + new" the same as "thrashing" (Nagappan & Ball ICSE 2005 use *relative*
  churn for exactly this reason; CodeScene hotspots use change frequency).
- Size is a *positive* axis: the goal is navigation/organization debt (big-and-active
  "god files"), not defect-proneness — pure churn÷size would de-prioritize large files.
- Raw length alone is weak/curvilinear; LOC/cyclomatic are redundant → excluded.
- Graph centrality does not pay off below ~1000 files: only fan-in (cheap PageRank
  proxy) + import-cycle detection. Near-dup is lexical shingles + Jaccard (the
  MinHash/jscpd family), $0 and dependency-free. Embeddings skipped by design.
- Sparse axes (freq, dup, fan-in) map zero → zero contribution: a file not touched /
  not duplicated / imported by nobody earns nothing there, rather than the modal
  percentile. Dense axes (size, orphan/stale) use plain percentile.

Native-first: git log + ast + line counts. No deps. Report-only.
Consumers: /upgrade pliability, /improve, a `just` top-N surface.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".go", ".rs", ".rb", ".java", ".sql"}
MD_EXT = {".md"}
SKIP_PREFIX = (".venv/", "node_modules/", ".git/", "artifacts/", "downloads/")
SKIP_SUBSTR = ("/binary-extracts/", "/artifacts/", "/observe/", "/.venv/")
SPARSE_AXES = {"freq", "dup", "fanin"}  # zero → zero contribution
SHINGLE_K = 6
SKETCH_K = 128          # bottom-K MinHash sketch size — bounds dup cost on huge files
DUP_MIN_SHINGLES = 12
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


def _sh(args: list[str], cwd: str) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout


def _tracked(cwd: str) -> list[str]:
    files = [ln for ln in _sh(["git", "ls-files"], cwd).splitlines() if ln]
    root = Path(cwd)
    return [
        f for f in files
        if not f.startswith(SKIP_PREFIX)
        and not any(s in "/" + f for s in SKIP_SUBSTR)
        and not (root / f).is_symlink()  # symlinked AGENTS.md/skills are intentional dupes
    ]


def _read(cwd: str, path: str) -> str:
    try:
        return (Path(cwd) / path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _loc(text: str) -> int:
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


# ---- git signals --------------------------------------------------------------

def _freq_by_file(cwd: str, days: int) -> dict[str, float]:
    """Focus-weighted change frequency: each commit touch counts 1/(files in commit),
    so a bulk reformat across 50 files barely registers while a file that is the sole
    subject of commits scores high. De-noises sweeping maintenance from real churn."""
    out = _sh(["git", "log", f"--since={days} days ago", "--no-renames", "--format=%H", "--name-only"], cwd)
    freq: dict[str, float] = defaultdict(float)
    commits: list[list[str]] = []
    cur: list[str] = []
    for line in out.splitlines():
        if re.fullmatch(r"[0-9a-f]{40}", line):
            if cur:
                commits.append(cur)
            cur = []
        elif line:
            cur.append(line)
    if cur:
        commits.append(cur)
    for cfiles in commits:
        weight = 1.0 / len(cfiles)
        for f in cfiles:
            freq[f] += weight
    return freq


def _age_days_by_file(cwd: str) -> dict[str, float]:
    out = _sh(["git", "log", "--format=%ct", "--no-renames", "--name-only"], cwd)
    now = time.time()
    ages: dict[str, float] = {}
    ts = now
    for line in out.splitlines():
        if line.isdigit():  # commit timestamp line (filenames are never all-digits)
            ts = float(line)
        elif line and line not in ages:  # first (most recent) sighting wins
            ages[line] = (now - ts) / 86400.0
    return ages


# ---- near-duplication (lexical shingles + Jaccard, inverted-index candidates) --

def _shingles(text: str) -> frozenset[int]:
    """Bottom-K MinHash sketch of word k-grams — bounds each file to <=K shingles so
    a 17k-line file costs the same as a 200-line one. Jaccard over sketches estimates
    the true Jaccard (biased but monotonic — fine for ranking/flagging near-dups)."""
    words = text.split()
    if len(words) < SHINGLE_K:
        return frozenset()
    hashes = {hash(tuple(words[i:i + SHINGLE_K])) & 0xFFFFFFFFFFFFFFFF for i in range(len(words) - SHINGLE_K + 1)}
    return frozenset(sorted(hashes)[:SKETCH_K])


def _dup_scores(files: list[str], shingles: dict[str, frozenset[int]]) -> dict[str, float]:
    index: dict[int, list[str]] = defaultdict(list)
    for f in files:
        if len(shingles[f]) >= DUP_MIN_SHINGLES:
            for sh in shingles[f]:
                index[sh].append(f)
    scores: dict[str, float] = {f: 0.0 for f in files}
    for f in files:
        sf = shingles[f]
        if len(sf) < DUP_MIN_SHINGLES:
            continue
        candidates = {g for sh in sf for g in index[sh] if g != f}
        best = 0.0
        for g in candidates:
            sg = shingles[g]
            inter = len(sf & sg)
            if inter:
                best = max(best, inter / len(sf | sg))
        scores[f] = best
    return scores


# ---- python import graph: fan-in + cycles -------------------------------------

def _imported_modules(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _py_graph(py_files: list[str], contents: dict[str, str]) -> tuple[dict[str, int], set[str]]:
    by_stem: dict[str, list[str]] = defaultdict(list)
    for f in py_files:
        by_stem[Path(f).stem].append(f)
    edges: dict[str, set[str]] = {f: set() for f in py_files}
    for f in py_files:
        for mod in _imported_modules(contents[f]):
            for target in by_stem.get(mod.split(".")[-1], []):
                if target != f:
                    edges[f].add(target)
    fan_in: dict[str, int] = {f: 0 for f in py_files}
    for f in py_files:
        for t in edges[f]:
            fan_in[t] += 1
    return fan_in, _nodes_in_cycles(edges)


def _nodes_in_cycles(edges: dict[str, set[str]]) -> set[str]:
    """Tarjan SCC; nodes in an SCC of size>1 (or a self-loop) are in a cycle."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    counter = [0]
    in_cycle: set[str] = set()

    def strongconnect(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in edges.get(v, ()):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or comp[0] in edges.get(comp[0], ()):
                in_cycle.update(comp)

    for v in list(edges):
        if v not in index:
            strongconnect(v)
    return in_cycle


# ---- markdown signals ---------------------------------------------------------

def _md_inbound(md_files: list[str], contents: dict[str, str]) -> dict[str, int]:
    """Inbound references per md file, single pass over all content (O(total_text)).
    Extracts *.md path tokens from every file and tallies matches by relpath/basename;
    each referencing file counts once. inbound==0 => orphan."""
    relset = set(md_files)
    by_base: dict[str, list[str]] = defaultdict(list)
    for f in md_files:
        by_base[Path(f).name].append(f)
    inbound: dict[str, int] = {f: 0 for f in md_files}
    token_re = re.compile(r"[\w./-]+\.md")
    for src, text in contents.items():
        for tok in set(token_re.findall(text)):  # set => count each referencing file once
            norm = tok[2:] if tok.startswith("./") else tok
            targets = [norm] if norm in relset else by_base.get(norm.rsplit("/", 1)[-1], [])
            for t in targets:
                if t != src:
                    inbound[t] += 1
    return inbound


def _broken_wikilinks(md_files: list[str], contents: dict[str, str], stems: set[str]) -> dict[str, int]:
    broken: dict[str, int] = {}
    for f in md_files:
        n = 0
        for m in WIKILINK_RE.findall(contents[f]):
            target = m.strip().split("/")[-1]
            if target and not target.startswith(("http", "#")) and target not in stems:
                n += 1
        broken[f] = n
    return broken


# ---- scoring ------------------------------------------------------------------

def _norm(values: list[float], sparse: bool):
    pool = [v for v in values if v > 0] if sparse else values
    s = sorted(pool)
    n = len(s)

    def f(v: float) -> float:
        if sparse and v <= 0:
            return 0.0
        return bisect.bisect_right(s, v) / n if n else 0.0

    return f


def _rank(rows: list[dict], axes: list[tuple[str, float]], top: int) -> list[dict]:
    if not rows:
        return []
    norms = {name: _norm([r[name] for r in rows], name in SPARSE_AXES) for name, _ in axes}
    for r in rows:
        r["score"] = sum(w * norms[name](r[name]) for name, w in axes)
    rows.sort(key=lambda r: (r["score"], r.get("loc", 0)), reverse=True)
    return rows[:top]


def main() -> int:
    ap = argparse.ArgumentParser(description="Forced ranking of files most worth expensive review.")
    ap.add_argument("repo", nargs="?", default=".", help="repo path (default: cwd)")
    ap.add_argument("--days", type=int, default=90, help="change-frequency window (default 90)")
    ap.add_argument("--top", type=int, default=15, help="top-N per category (default 15)")
    args = ap.parse_args()

    cwd = str(Path(args.repo).expanduser().resolve())
    files = _tracked(cwd)
    contents = {f: _read(cwd, f) for f in files}
    freq = _freq_by_file(cwd, args.days)
    ages = _age_days_by_file(cwd)
    shingles = {f: _shingles(contents[f]) for f in files}

    code = [f for f in files if Path(f).suffix in CODE_EXT]
    md = [f for f in files if Path(f).suffix in MD_EXT]
    py = [f for f in code if f.endswith(".py")]

    code_dup = _dup_scores(code, shingles)
    md_dup = _dup_scores(md, shingles)
    fan_in, in_cycle = _py_graph(py, contents)
    inbound = _md_inbound(md, contents)
    stems = {Path(f).stem for f in md}
    broken = _broken_wikilinks(md, contents, stems)
    max_age = max(ages.values(), default=1.0) or 1.0

    print(f"structure-debt rank — {cwd}  (freq window: {args.days}d; freq = #commits)")

    code_rows = [{
        "file": f, "freq": float(freq.get(f, 0)), "loc": float(_loc(contents[f])),
        "dup": code_dup.get(f, 0.0), "fanin": float(fan_in.get(f, 0)), "cycle": f in in_cycle,
    } for f in code]
    print(f"\n=== CODE  (0.45 freq + 0.25 size + 0.20 dup + 0.10 fan-in)  [{len(code)} files] — top {args.top} ===")
    print(f"  {'score':>5}  {'freq':>4} {'loc':>5} {'dup':>4} {'fan':>3}  flags  file")
    for r in _rank(code_rows, [("freq", 0.45), ("loc", 0.25), ("dup", 0.20), ("fanin", 0.10)], args.top):
        flag = "CYCLE" if r["cycle"] else ""
        print(f"  {r['score']:5.2f}  {r['freq']:4.1f} {int(r['loc']):5d} {r['dup']:4.2f} {int(r['fanin']):3d}  {flag:5}  {r['file']}")

    md_rows = [{
        "file": f, "freq": float(freq.get(f, 0)), "loc": float(_loc(contents[f])), "dup": md_dup.get(f, 0.0),
        "orphan_stale": (0.6 if inbound.get(f, 0) <= 0 else 0.0) + 0.4 * (ages.get(f, 0.0) / max_age),
        "orphan": inbound.get(f, 0) <= 0, "broken": broken.get(f, 0),
    } for f in md]
    print(f"\n=== MARKDOWN  (0.40 freq + 0.25 dup + 0.20 size + 0.15 orphan/stale)  [{len(md)} files] — top {args.top} ===")
    print(f"  {'score':>5}  {'freq':>4} {'loc':>5} {'dup':>4}  flags          file")
    for r in _rank(md_rows, [("freq", 0.40), ("dup", 0.25), ("loc", 0.20), ("orphan_stale", 0.15)], args.top):
        flag = " ".join(x for x in ("ORPHAN" if r["orphan"] else "", f"BROKEN×{r['broken']}" if r["broken"] else "") if x)
        print(f"  {r['score']:5.2f}  {r['freq']:4.1f} {int(r['loc']):5d} {r['dup']:4.2f}  {flag:14}  {r['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
