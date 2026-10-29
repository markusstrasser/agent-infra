#!/usr/bin/env python3
"""repo_scout.py — find new GitHub repos through the operator's taste neighbors.

Popularity (trending, star counts, topic search) ends in noise: star farms, paper-day
fork farms, hype. This ranks repos by WHO starred them instead. The operator's own
stars define the taste; users whose stars overlap them on niche repos are neighbors;
what neighbors starred in the last days, weighted by how close they are, is the feed.

GitHub hides who starred another user's repo (REST stargazers and watchers return 404,
GraphQL an empty list; checked 2026-10-29), but a user's own starred list stays public
with timestamps. So candidates come from people tied to the operator's stars, and each
candidate's similarity is computed from their own starred list:
  seeds       X bookmark authors whose same-named GitHub account lists that X handle
  deps        GitHub repos his active projects depend on (Cargo, PyPI, npm), by project activity
  candidates  seeds, contributors of his dependencies, authors of his recent niche stars
  neighbors   IDF-weighted overlap of each candidate's recent stars with deps + recent stars
  feed        repos the top neighbors starred in the last days, scored by neighbor weight

His GitHub starring slowed (431 stars in 2025, 34 by 2026-10); his current taste lives in
X bookmarks, so confirmed bookmark authors get a weight from their bookmark count.

Usage:
  uv run python3 scripts/repo_scout.py seeds [--bookmarks PATH] [--min-bookmarks 2]
  uv run python3 scripts/repo_scout.py deps [--days 90]
  uv run python3 scripts/repo_scout.py neighbors [--star-days 600] [--pages 2]
  uv run python3 scripts/repo_scout.py feed [--top 300] [--days 14] [--out PATH]
Cache (rederivable): ~/.cache/repo-scout. Auth: the `gh` CLI's token (5,000 requests an hour).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CACHE = Path.home() / ".cache" / "repo-scout"
BOOKMARK_SYNC = Path.home() / "Projects/ext/data/twitter-text-sync"
PROJECTS = Path.home() / "Projects"
LENSES = Path(__file__).resolve().parent.parent / "config" / "repo-scout-lenses.toml"
API = "https://api.github.com"
STAR_JSON = "application/vnd.github.star+json"  # adds starred_at
WORKERS = 6
FRESH_S = 20 * 3600
_TOKEN: str | None = None
MISSING: Counter[str] = Counter()  # 404s per endpoint kind, reported at the end of a run


def token() -> str:
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        ).stdout.strip()
    return _TOKEN


def get(path: str, accept: str = "application/vnd.github+json", kind: str = "") -> Any:
    """One API GET. Waits out rate limits; a 404 returns None and is counted under `kind`."""
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Bearer {token()}", "Accept": accept,
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and e.headers.get("x-ratelimit-remaining") == "0":
                reset = int(e.headers.get("x-ratelimit-reset", time.time() + 60))
                wait = max(5, reset - time.time() + 2)
                print(f"[rate-limit] waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code in (403, 429, 502, 503) and attempt < 4:  # secondary limit / transient
                time.sleep(10 * (attempt + 1))
                continue
            if e.code in (404, 451):
                MISSING[kind or path] += 1
                return None
            raise
    raise RuntimeError(f"GET {path} failed after retries")


def cached(name: str, fetch, max_age: float = FRESH_S) -> Any:
    path = CACHE / name
    if path.exists() and time.time() - path.stat().st_mtime < max_age:
        return json.loads(path.read_text())
    value = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return value


def star_row(r: dict) -> dict:
    repo = r["repo"]
    return {"starred_at": r["starred_at"], "full_name": repo["full_name"],
            "owner": repo["owner"]["login"], "owner_type": repo["owner"]["type"],
            "stars": repo["stargazers_count"], "created_at": repo["created_at"],
            "language": repo["language"], "description": repo["description"] or "",
            "fork": repo["fork"]}


def stars_of(login: str | None, pages: int) -> list[dict]:
    """A user's most recent stars, newest first (login None = the authenticated user)."""
    base = "/user/starred" if login is None else f"/users/{login}/starred"

    def fetch() -> list[dict]:
        out: list[dict] = []
        for page in range(1, pages + 1):
            rows = get(f"{base}?per_page=100&page={page}", STAR_JSON, kind="starred")
            if not rows:
                break
            out += [star_row(r) for r in rows]
        return out

    return cached(f"stars/{login or '_me'}-{pages}.json", fetch)


def idf(stars: int) -> float:
    """Sharing a 200-star repo says more than sharing a 50k one."""
    return 1 / math.log(2 + stars)


def age_days(iso: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days


def recency(starred_at: str, half_life_days: float) -> float:
    """His taste drifts (a Clojure era dominated an unweighted run); recent stars count more."""
    return 0.5 ** (age_days(starred_at) / half_life_days)


def cmd_seeds(args: argparse.Namespace) -> None:
    path = Path(args.bookmarks) if args.bookmarks else max(BOOKMARK_SYNC.glob("*/bookmarks.jsonl"))
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    count: Counter[str] = Counter()
    for line in path.open():
        b = json.loads(line)
        for t in (b, b.get("quoted")):
            if t and datetime.strptime(t["created_at"], "%a %b %d %H:%M:%S %z %Y") >= since:
                count[t["author"]] += 1
    handles = [h for h, n in count.items() if n >= args.min_bookmarks]

    def confirm(handle: str) -> dict | None:
        user = cached(f"users/{handle.lower()}.json",
                      lambda: get(f"/users/{handle}", kind="users") or {}, max_age=30 * 86400)
        x = (user.get("twitter_username") or "").lower()
        return {"login": user["login"], "x": handle, "bookmarks": count[handle]} if x == handle.lower() else None

    with ThreadPoolExecutor(WORKERS) as pool:
        seeds = [s for s in pool.map(confirm, handles) if s]
    seeds.sort(key=lambda s: s["bookmarks"], reverse=True)
    (CACHE / "x_seeds.json").write_text(json.dumps(seeds, indent=1))
    print(f"{path}: {len(count)} authors in {args.days} days, {len(handles)} with >= "
          f"{args.min_bookmarks} bookmarks, {len(seeds)} confirmed on GitHub", file=sys.stderr)
    for s in seeds[:40]:
        print(f"{s['bookmarks']:3d}  {s['x']}")


GITHUB_REPO = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?]|$)")
REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def http_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "repo-scout (markusstrasser)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            MISSING["registry"] += 1
            return None
        raise


def github_of(text: str | None) -> str | None:
    m = GITHUB_REPO.search(text or "")
    return f"{m[1]}/{m[2]}".lower() if m else None


def resolve(eco: str, name: str) -> str | None:
    """A package's GitHub repo from its registry entry (cached 30 days)."""
    def fetch() -> Any:
        if eco == "cargo":
            d = http_json(f"https://crates.io/api/v1/crates/{name}")
            return github_of(d and (d["crate"].get("repository") or d["crate"].get("homepage")))
        if eco == "pypi":
            d = http_json(f"https://pypi.org/pypi/{name}/json")
            info = (d or {}).get("info") or {}
            urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page")]
            return next((g for g in map(github_of, urls) if g), None)
        d = http_json(f"https://registry.npmjs.org/{name}")
        repo = (d or {}).get("repository")
        return github_of(repo.get("url") if isinstance(repo, dict) else repo)
    return cached(f"registry/{eco}/{name.replace('/', '__')}.json", fetch, max_age=30 * 86400)


def manifest_deps(path: Path) -> list[tuple[str, str]]:
    if path.name == "package.json":
        d = json.loads(path.read_text())
        return [("npm", n) for k in ("dependencies", "devDependencies") for n in d.get(k) or {}]
    d = tomllib.loads(path.read_text())
    if path.name == "Cargo.toml":
        tables = [d.get("dependencies"), d.get("dev-dependencies"), d.get("build-dependencies"),
                  (d.get("workspace") or {}).get("dependencies")]
        out = []
        for t in filter(None, tables):
            for key, spec in t.items():
                if isinstance(spec, dict) and (spec.get("path") or spec.get("workspace")):
                    continue
                out.append(("cargo", spec.get("package", key) if isinstance(spec, dict) else key))
        return out
    reqs = list((d.get("project") or {}).get("dependencies") or [])
    for group in list((d.get("dependency-groups") or {}).values()) + \
            list(((d.get("project") or {}).get("optional-dependencies") or {}).values()):
        reqs += [r for r in group if isinstance(r, str)]
    return [("pypi", m[1].lower()) for r in reqs if (m := REQ_NAME.match(r))]


def cmd_deps(args: argparse.Namespace) -> None:
    """Repos his active projects depend on: current taste, weighted by project activity."""
    weight: dict[str, float] = defaultdict(float)
    users: dict[str, set[str]] = defaultdict(set)
    n_projects = 0
    for project in sorted(p for p in PROJECTS.iterdir() if (p / ".git").exists()):
        log = subprocess.run(["git", "-C", str(project), "log", f"--since={args.days}.days", "--oneline"],
                             capture_output=True, text=True).stdout
        commits = len(log.splitlines())
        if not commits:
            continue
        n_projects += 1
        found = subprocess.run(["fd", "-d", "3", "-t", "f", "-E", "node_modules", "-E", "target",
                                "-E", ".venv", "-E", ".claude", "^(Cargo\\.toml|pyproject\\.toml|package\\.json)$",
                                str(project)], capture_output=True, text=True).stdout.split()
        deps = {dep for f in found for dep in manifest_deps(Path(f))}
        with ThreadPoolExecutor(WORKERS) as pool:
            repos = {r for r in pool.map(lambda d: resolve(*d), deps) if r}
        for repo in repos:
            weight[repo] += math.log1p(commits)
            users[repo].add(project.name)
    with ThreadPoolExecutor(WORKERS) as pool:
        meta = list(pool.map(lambda r: get(f"/repos/{r}", kind="repos"), list(weight)))
    rows = [{"full_name": m["full_name"], "stars": m["stargazers_count"], "weight": round(weight[r], 3),
             "projects": sorted(users[r])} for r, m in zip(weight, meta) if m]
    rows.sort(key=lambda r: r["weight"], reverse=True)
    (CACHE / "deps.json").write_text(json.dumps(rows, indent=1))
    print(f"{n_projects} active projects, {len(rows)} dependency repos; 404s: {dict(MISSING)}", file=sys.stderr)
    for r in rows[:25]:
        print(f"{r['weight']:6.2f}  {r['stars']:6d}  {r['full_name']}  {','.join(r['projects'][:4])}")


def contributors(full_name: str, n: int = 5) -> list[str]:
    rows = cached(f"contributors/{full_name.replace('/', '__')}-{n}.json",
                  lambda: get(f"/repos/{full_name}/contributors?per_page={n}", kind="contributors") or [],
                  max_age=30 * 86400)
    return [c["login"] for c in rows if c.get("type") == "User"]


def lens_taste(name: str) -> tuple[dict[str, float], dict[str, int], list[str]]:
    """An exemplar lens: taste weight 1 per exemplar, candidates its top-10 contributors."""
    lens = tomllib.loads(LENSES.read_text())[name]
    with ThreadPoolExecutor(WORKERS) as pool:
        metas = list(pool.map(lambda r: cached(f"repos/{r.replace('/', '__')}.json",
                                               lambda: get(f"/repos/{r}", kind="repos") or {}, max_age=7 * 86400),
                              lens["exemplars"]))
        found = [m for m in metas if m]
        people = [u for logins in pool.map(lambda m: contributors(m["full_name"], 10), found) for u in logins]
    missing = [r for r, m in zip(lens["exemplars"], metas) if not m]
    if missing:
        print(f"[lens {name}] exemplars not found: {missing}", file=sys.stderr)
    owners = [m["owner"]["login"] for m in found if m["owner"]["type"] == "User"]
    return ({m["full_name"].lower(): 1.0 for m in found},
            {m["full_name"].lower(): m["stargazers_count"] for m in found}, people + owners)


def score_candidates(candidates: list[str], taste: dict[str, float], meta: dict[str, int],
                     x_seeds: dict[str, int], args: argparse.Namespace) -> list[dict]:
    with ThreadPoolExecutor(WORKERS) as pool:
        theirs = list(pool.map(lambda u: stars_of(u, args.pages), candidates))
    rows = []
    for login, stars in zip(candidates, theirs):
        shared = [r["full_name"].lower() for r in stars
                  if r["full_name"].lower() in taste and r["owner"] != login]
        bookmarks = x_seeds.get(login, 0)
        if len(shared) < args.min_shared and not bookmarks:
            continue
        overlap = sum(idf(meta[k]) * taste[k] for k in shared) / math.sqrt(max(1, len(stars)))
        rows.append({"login": login, "score": round(overlap + args.x_weight * math.log1p(bookmarks), 4),
                     "overlap": round(overlap, 4), "bookmarks": bookmarks, "shared": len(shared),
                     "starred": len(stars), "via": shared[:5]})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def cmd_neighbors(args: argparse.Namespace) -> None:
    me = get("/user")["login"]
    x_seeds = {s["login"]: s["bookmarks"] for s in
               (json.loads((CACHE / "x_seeds.json").read_text()) if (CACHE / "x_seeds.json").exists() else [])}
    if args.lens != "projects":
        taste, meta, hop1 = lens_taste(args.lens)
        hop1 = sorted(set(hop1) - {me})
        rows = score_candidates(hop1, taste, meta, {}, args)
        # Hop 2: authors of repos that several hop-1 neighbors starred lately reach people
        # outside the exemplars' own contributor lists.
        co: Counter[str] = Counter()
        owner_of: dict[str, tuple[str, str]] = {}
        for r in rows[: args.hop_top]:
            for st in stars_of(r["login"], args.pages):
                if st["stars"] <= args.max_repo_stars and st["full_name"].lower() not in taste:
                    co[st["full_name"]] += 1
                    owner_of[st["full_name"]] = (st["owner"], st["owner_type"])
        hubs = [k for k, c in co.items() if c >= args.hop_min]
        hop2 = {owner_of[k][0] for k in hubs if owner_of[k][1] == "User"}
        with ThreadPoolExecutor(WORKERS) as pool:
            for logins in pool.map(lambda k: contributors(k, 3), hubs):
                hop2.update(logins)
        hop2 -= set(hop1) | {me}
        print(f"[lens {args.lens}] {len(taste)} exemplars, {len(hop1)} hop-1 people, "
              f"{len(hubs)} co-starred hubs, {len(hop2)} hop-2 people", file=sys.stderr)
        rows = sorted(rows + score_candidates(sorted(hop2), taste, meta, {}, args),
                      key=lambda r: r["score"], reverse=True)
        write_neighbors(rows, args)
        return
    # Taste = what his active projects depend on, plus what he starred recently. Both
    # weighted; his old stars (a Clojure era) and old follows are left out on purpose.
    taste: dict[str, float] = {}
    meta: dict[str, int] = {}
    for d in json.loads((CACHE / "deps.json").read_text()):
        taste[d["full_name"].lower()] = d["weight"]
        meta[d["full_name"].lower()] = d["stars"]
    recent = [r for r in stars_of(None, pages=100) if age_days(r["starred_at"]) <= args.star_days]
    for r in recent:
        key = r["full_name"].lower()
        taste[key] = taste.get(key, 0) + args.star_weight * recency(r["starred_at"], args.half_life)
        meta[key] = r["stars"]
    dep_repos = [d["full_name"] for d in json.loads((CACHE / "deps.json").read_text())
                 if d["stars"] <= args.max_repo_stars]
    niche_recent = [r for r in recent if args.min_repo_stars <= r["stars"] <= args.max_repo_stars]

    source: Counter[str] = Counter()
    for r in niche_recent:
        if r["owner_type"] == "User":
            source[r["owner"]] += 1
    with ThreadPoolExecutor(WORKERS) as pool:
        for logins in pool.map(contributors, dep_repos + [r["full_name"] for r in niche_recent]):
            for login in set(logins):
                source[login] += 1
    for login in x_seeds:
        source[login] += 1
    source.pop(me, None)
    candidates = list(source)
    print(f"taste: {len(taste)} repos ({len(dep_repos)} niche deps, {len(recent)} stars in "
          f"{args.star_days} days); {len(candidates)} candidates, <= {len(candidates) * args.pages} calls",
          file=sys.stderr)

    write_neighbors(score_candidates(candidates, taste, meta, x_seeds, args), args)


def write_neighbors(rows: list[dict], args: argparse.Namespace) -> None:
    (CACHE / f"neighbors-{args.lens}.json").write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} neighbors with >= {args.min_shared} shared; 404s: {dict(MISSING)}", file=sys.stderr)
    for r in rows[:30]:
        print(f"{r['score']:7.3f}  overlap {r['overlap']:.3f}  bm {r['bookmarks']:2d}  "
              f"shared {r['shared']:3d}/{r['starred']:3d}  {r['login']:20s} {' '.join(r['via'][:3])}")


def cmd_feed(args: argparse.Namespace) -> None:
    neighbors = json.loads((CACHE / f"neighbors-{args.lens}.json").read_text())[: args.top]
    mine = {r["full_name"] for r in stars_of(None, pages=100)}
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    with ThreadPoolExecutor(WORKERS) as pool:
        stars = list(pool.map(lambda n: stars_of(n["login"], args.pages), neighbors))
    score: dict[str, float] = defaultdict(float)
    who: dict[str, list[str]] = defaultdict(list)
    meta: dict[str, dict] = {}
    skipped_bulk = 0
    for n, rows in zip(neighbors, stars):
        recent = [r for r in rows if datetime.fromisoformat(r["starred_at"].replace("Z", "+00:00")) >= since]
        # A full page inside the window is bulk-starring; such stars say little each.
        if len(recent) >= 100:
            skipped_bulk += 1
            continue
        damp = 1 / math.sqrt(max(1, len(recent)))
        for r in recent:
            if r["full_name"] in mine or r["fork"] or r["stars"] > args.max_stars:
                continue
            score[r["full_name"]] += n["score"] * damp
            who[r["full_name"]].append(n["login"])
            meta[r["full_name"]] = r
    ranked = [k for k in sorted(score, key=lambda k: score[k], reverse=True)
              if len(who[k]) >= args.min_neighbors]
    lines = [f"# Repo scout feed: {args.lens} {datetime.now(timezone.utc):%Y-%m-%d}",
             f"{len(neighbors)} neighbors, last {args.days} days, {skipped_bulk} bulk-starrers skipped, "
             f">= {args.min_neighbors} neighbors per repo, <= {args.max_stars} stars", ""]
    for k in ranked[: args.limit]:
        m = meta[k]
        lines.append(f"- **[{k}](https://github.com/{k})** {score[k]:.2f} · {len(who[k])} neighbors · "
                     f"{m['stars']}★ · created {m['created_at'][:10]} · {m['language'] or '-'}\n"
                     f"  {m['description'][:200]}\n  via {', '.join(who[k][:6])}")
    text = "\n".join(lines) + "\n"
    out = Path(args.out) if args.out else CACHE / f"feed-{args.lens}-{datetime.now():%Y-%m-%d}.md"
    out.write_text(text)
    print(text)
    print(f"wrote {out}; 404s: {dict(MISSING)}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sd = sub.add_parser("seeds")
    sd.add_argument("--bookmarks", help="bookmarks.jsonl (default: newest twitter-text-sync)")
    sd.add_argument("--days", type=int, default=730)
    sd.add_argument("--min-bookmarks", type=int, default=2)
    dp = sub.add_parser("deps")
    dp.add_argument("--days", type=int, default=90, help="a project is active with a commit in this window")
    n = sub.add_parser("neighbors")
    n.add_argument("--lens", default="projects", help="projects, or a lens in config/repo-scout-lenses.toml")
    n.add_argument("--hop-top", type=int, default=60, help="hop-1 neighbors whose stars seed hop 2")
    n.add_argument("--hop-min", type=int, default=3, help="hop-1 neighbors who must share a hub repo")
    n.add_argument("--min-repo-stars", type=int, default=10)
    n.add_argument("--max-repo-stars", type=int, default=20000)
    n.add_argument("--star-days", type=int, default=600, help="his stars older than this are ignored")
    n.add_argument("--star-weight", type=float, default=2.0, help="taste weight of a fresh star")
    n.add_argument("--pages", type=int, default=2, help="pages of 100 stars per candidate")
    n.add_argument("--min-shared", type=int, default=2)
    n.add_argument("--x-weight", type=float, default=0.04, help="score per log1p(bookmarks)")
    n.add_argument("--half-life", type=float, default=365, help="days; weight of his older stars")
    f = sub.add_parser("feed")
    f.add_argument("--lens", default="projects")
    f.add_argument("--top", type=int, default=300)
    f.add_argument("--pages", type=int, default=2, help="same as neighbors, to reuse its cache")
    f.add_argument("--days", type=int, default=14)
    f.add_argument("--max-stars", type=int, default=20000)
    f.add_argument("--min-neighbors", type=int, default=2)
    f.add_argument("--limit", type=int, default=60)
    f.add_argument("--out")
    args = p.parse_args()
    {"seeds": cmd_seeds, "deps": cmd_deps, "neighbors": cmd_neighbors, "feed": cmd_feed}[args.cmd](args)


if __name__ == "__main__":
    main()
