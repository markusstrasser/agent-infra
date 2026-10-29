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
  candidates  seeds, accounts the operator follows, owners and top contributors of his niche stars
  neighbors   IDF-weighted overlap of each candidate's recent stars with his
  feed        repos the top neighbors starred in the last days, scored by neighbor weight

His GitHub starring slowed (431 stars in 2025, 34 by 2026-10); his current taste lives in
X bookmarks, so confirmed bookmark authors get a weight from their bookmark count.

Usage:
  uv run python3 scripts/repo_scout.py seeds [--bookmarks PATH] [--min-bookmarks 2]
  uv run python3 scripts/repo_scout.py neighbors [--repos 400] [--pages 2]
  uv run python3 scripts/repo_scout.py feed [--top 300] [--days 14] [--out PATH]
Cache (rederivable): ~/.cache/repo-scout. Auth: the `gh` CLI's token (5,000 requests an hour).
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CACHE = Path.home() / ".cache" / "repo-scout"
BOOKMARK_SYNC = Path.home() / "Projects/ext/data/twitter-text-sync"
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


def cmd_neighbors(args: argparse.Namespace) -> None:
    me = get("/user")["login"]
    mine = stars_of(None, pages=100)
    mine_set = {r["full_name"]: r for r in mine}
    niche = [r for r in mine if args.min_repo_stars <= r["stars"] <= args.max_repo_stars][: args.repos]

    following = cached("following.json", lambda: [
        u["login"] for page in range(1, 11)
        for u in (get(f"/user/following?per_page=100&page={page}", kind="following") or [])])

    def contributors(full_name: str) -> list[str]:
        rows = cached(f"contributors/{full_name.replace('/', '__')}.json",
                      lambda: get(f"/repos/{full_name}/contributors?per_page=5", kind="contributors") or [],
                      max_age=30 * 86400)
        return [c["login"] for c in rows if c.get("type") == "User"]

    source: Counter[str] = Counter()  # how many of his niche stars a candidate authored
    for login in following:
        source[login] += 1
    for r in niche:
        if r["owner_type"] == "User":
            source[r["owner"]] += 1
    with ThreadPoolExecutor(WORKERS) as pool:
        for logins in pool.map(lambda r: contributors(r["full_name"]), niche):
            for login in set(logins):
                source[login] += 1
    x_seeds = {s["login"]: s["bookmarks"] for s in
               (json.loads((CACHE / "x_seeds.json").read_text()) if (CACHE / "x_seeds.json").exists() else [])}
    for login in x_seeds:
        source[login] += 1
    source.pop(me, None)
    candidates = list(source)
    print(f"{len(mine)} own stars, {len(niche)} niche, {len(following)} followed, "
          f"{len(candidates)} candidates, <= {len(candidates) * args.pages} star calls", file=sys.stderr)

    with ThreadPoolExecutor(WORKERS) as pool:
        theirs = list(pool.map(lambda u: stars_of(u, args.pages), candidates))
    rows = []
    for login, stars in zip(candidates, theirs):
        shared = [mine_set[r["full_name"]] for r in stars
                  if r["full_name"] in mine_set and r["owner"] != login]
        bookmarks = x_seeds.get(login, 0)
        if len(shared) < args.min_shared and not bookmarks:
            continue
        overlap = sum(idf(r["stars"]) * recency(r["starred_at"], args.half_life)
                      for r in shared) / math.sqrt(max(1, len(stars)))
        score = overlap + args.x_weight * math.log1p(bookmarks)
        rows.append({"login": login, "score": round(score, 4), "overlap": round(overlap, 4),
                     "bookmarks": bookmarks, "shared": len(shared), "starred": len(stars),
                     "source": source[login]})
    rows.sort(key=lambda r: r["score"], reverse=True)
    (CACHE / "neighbors.json").write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} neighbors with >= {args.min_shared} shared stars; 404s: {dict(MISSING)}",
          file=sys.stderr)
    for r in rows[:30]:
        print(f"{r['score']:7.3f}  overlap {r['overlap']:.3f}  bm {r['bookmarks']:2d}  "
              f"shared {r['shared']:3d}/{r['starred']:3d}  {r['login']}")


def cmd_feed(args: argparse.Namespace) -> None:
    neighbors = json.loads((CACHE / "neighbors.json").read_text())[: args.top]
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
    lines = [f"# Repo scout feed {datetime.now(timezone.utc):%Y-%m-%d}",
             f"{len(neighbors)} neighbors, last {args.days} days, {skipped_bulk} bulk-starrers skipped, "
             f">= {args.min_neighbors} neighbors per repo, <= {args.max_stars} stars", ""]
    for k in ranked[: args.limit]:
        m = meta[k]
        lines.append(f"- **[{k}](https://github.com/{k})** {score[k]:.2f} · {len(who[k])} neighbors · "
                     f"{m['stars']}★ · created {m['created_at'][:10]} · {m['language'] or '-'}\n"
                     f"  {m['description'][:200]}\n  via {', '.join(who[k][:6])}")
    text = "\n".join(lines) + "\n"
    out = Path(args.out) if args.out else CACHE / f"feed-{datetime.now():%Y-%m-%d}.md"
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
    n = sub.add_parser("neighbors")
    n.add_argument("--min-repo-stars", type=int, default=10)
    n.add_argument("--max-repo-stars", type=int, default=5000)
    n.add_argument("--repos", type=int, default=400, help="most recent niche stars to mine")
    n.add_argument("--pages", type=int, default=2, help="pages of 100 stars per candidate")
    n.add_argument("--min-shared", type=int, default=2)
    n.add_argument("--x-weight", type=float, default=0.04, help="score per log1p(bookmarks)")
    n.add_argument("--half-life", type=float, default=365, help="days; weight of his older stars")
    f = sub.add_parser("feed")
    f.add_argument("--top", type=int, default=300)
    f.add_argument("--pages", type=int, default=2, help="same as neighbors, to reuse its cache")
    f.add_argument("--days", type=int, default=14)
    f.add_argument("--max-stars", type=int, default=20000)
    f.add_argument("--min-neighbors", type=int, default=2)
    f.add_argument("--limit", type=int, default=60)
    f.add_argument("--out")
    args = p.parse_args()
    {"seeds": cmd_seeds, "neighbors": cmd_neighbors, "feed": cmd_feed}[args.cmd](args)


if __name__ == "__main__":
    main()
