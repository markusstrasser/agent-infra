#!/usr/bin/env python3
"""Ingest LessWrong high-karma posts into the shared corpus.

LessWrong exposes a public GraphQL API (no auth) at /graphql. Post bodies come
back as clean article HTML via `contents{html}`; the live pages are a JS-rendered
SPA, so we must use GraphQL (trafilatura-on-URL would get an empty shell).

Two phases (run --build-index once, then --ingest):

    # 1. Walk every month 2009-01..now, fetch post metadata (karma, author,
    #    tags, ...), write an index, and print the karma distribution so you
    #    can pick a floor on real numbers.
    corpus_ingest_lesswrong.py --build-index

    # 2. Filter the index to baseScore >= FLOOR, fetch each post body, wrap it
    #    in a minimal <article> doc, and ingest via corpus_core (trafilatura ->
    #    markdown). Resumable: processed _ids are checkpointed.
    corpus_ingest_lesswrong.py --ingest --floor 50 [--max N]

Each post lands in --corpus-root as a content-addressed
sha_<hash> source, source_type=blog_post, with extra_metadata carrying lw_post_id,
author, karma, posted_at, tags, word_count, lw_url.

Run with the corpus-core tool interpreter so imports resolve:
    ~/.local/share/uv/tools/corpus-core/bin/python3 corpus_ingest_lesswrong.py ...
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import httpx
from corpus_core import ingest as ci
from corpus_core.store import CorpusStore

GQL = "https://www.lesswrong.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0 corpus-ingest (+local research mirror)",
    "Content-Type": "application/json",
}
HERE = Path(__file__).resolve().parent
INDEX = HERE / "lesswrong_index.jsonl"
DONE = HERE / "lesswrong_ingested.txt"

# ---------------------------------------------------------------------------


def _ok(m):
    print(f"  ✓ {m}", flush=True)


def _warn(m):
    print(f"  ! {m}", flush=True)


def gql(query: str, retries: int = 5):
    last = None
    for i in range(retries):
        try:
            r = httpx.post(GQL, headers=HEADERS, json={"query": query}, timeout=90.0)
            r.raise_for_status()
            d = r.json()
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GraphQL failed after {retries}: {last}")


def iter_months(start=(2009, 1)):
    y, m = start
    today = date.today()
    while (y, m) <= (today.year, today.month):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        yield f"{y:04d}-{m:02d}-01", f"{ny:04d}-{nm:02d}-01"
        y, m = ny, nm


META_Q = (
    '{{posts(input:{{terms:{{view:"top",after:"{a}",before:"{b}",limit:1000}}}})'
    "{{results{{_id title slug postedAt baseScore voteCount pageUrl wordCount "
    "user{{username displayName}} tags{{name}}}}}}}}"
)

BODY_Q = '{{post(input:{{selector:{{_id:"{pid}"}}}}){{result{{contents{{html}}}}}}}}'


# ---------------------------------------------------------------------------
# Phase 1 — build index
# ---------------------------------------------------------------------------


def build_index() -> None:
    n = 0
    scores = []
    with INDEX.open("w") as fh:
        for a, b in iter_months():
            data = gql(META_Q.format(a=a, b=b))
            results = data["posts"]["results"] or []
            for p in results:
                if p.get("baseScore") is None:
                    continue
                rec = {
                    "_id": p["_id"],
                    "title": p.get("title") or "",
                    "slug": p.get("slug") or "",
                    "posted_at": p.get("postedAt"),
                    "karma": p["baseScore"],
                    "vote_count": p.get("voteCount"),
                    "url": p.get("pageUrl"),
                    "word_count": p.get("wordCount"),
                    "author": (p.get("user") or {}).get("displayName"),
                    "author_username": (p.get("user") or {}).get("username"),
                    "tags": [t["name"] for t in (p.get("tags") or []) if t.get("name")],
                }
                fh.write(json.dumps(rec) + "\n")
                scores.append(p["baseScore"])
                n += 1
            print(f"  {a[:7]}: {len(results):>4} posts (cumulative {n})", flush=True)
            time.sleep(0.2)
    _report_distribution(scores)
    _ok(f"index written: {INDEX}  ({n} posts)")


def _report_distribution(scores) -> None:
    print("\n[karma distribution]")
    for floor in (10, 20, 30, 50, 75, 100, 200):
        c = sum(1 for s in scores if s >= floor)
        print(f"  >= {floor:>4} karma : {c:>6} posts")
    print(f"  total           : {len(scores):>6} posts")


# ---------------------------------------------------------------------------
# Phase 2 — ingest bodies
# ---------------------------------------------------------------------------


def _load_done() -> set[str]:
    if DONE.exists():
        return {ln.strip() for ln in DONE.read_text().splitlines() if ln.strip()}
    return set()


def ingest(store: CorpusStore, floor: int, limit: int | None, delay: float) -> None:
    if not INDEX.exists():
        sys.exit("index not found — run --build-index first")
    done = _load_done()
    rows = []
    with INDEX.open() as fh:
        for ln in fh:
            r = json.loads(ln)
            if r["karma"] >= floor and r["_id"] not in done:
                rows.append(r)
    rows.sort(key=lambda r: r["karma"], reverse=True)
    if limit:
        rows = rows[:limit]
    total = len(rows)
    print(f"[ingest] {total} posts >= {floor} karma to fetch "
          f"({len(done)} already done)\n", flush=True)

    fail = 0
    with DONE.open("a") as donefh:
        for i, r in enumerate(rows, 1):
            try:
                body = gql(BODY_Q.format(pid=r["_id"]))
                html_body = ((body.get("post") or {}).get("result") or {}).get(
                    "contents"
                )
                html_body = (html_body or {}).get("html") if html_body else None
                if not html_body:
                    _warn(f"[{i}/{total}] {r['_id']} no body — skip")
                    fail += 1
                    continue
                title = html.escape(r["title"])
                doc = (
                    f"<html><head><title>{title}</title></head>"
                    f"<body><article><h1>{title}</h1>{html_body}</article></body></html>"
                )
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".html", delete=False, encoding="utf-8"
                ) as tf:
                    tf.write(doc)
                    tmp = Path(tf.name)
                try:
                    ci.ingest_html(
                        store,
                        tmp,
                        source_url=r["url"],
                        source_type="blog_post",
                        title=r["title"],
                        extra_metadata={
                            "source": "lesswrong",
                            "lw_post_id": r["_id"],
                            "author": r["author"],
                            "author_username": r["author_username"],
                            "karma": r["karma"],
                            "vote_count": r["vote_count"],
                            "posted_at": r["posted_at"],
                            "word_count": r["word_count"],
                            "lw_slug": r["slug"],
                            "tags": r["tags"],
                        },
                    )
                finally:
                    tmp.unlink(missing_ok=True)
                donefh.write(r["_id"] + "\n")
                donefh.flush()
                if i % 25 == 0 or i == total:
                    print(f"  [{i}/{total}] karma={r['karma']} {r['title'][:60]}",
                          flush=True)
            except Exception as e:  # noqa: BLE001
                _warn(f"[{i}/{total}] {r['_id']} ERROR: {str(e)[:120]}")
                fail += 1
            time.sleep(delay)
    _ok(f"ingest done — {total - fail} ok, {fail} failed/skipped")


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-index", action="store_true")
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--floor", type=int, default=50, help="min karma (default 50)")
    ap.add_argument("--max", type=int, default=None, help="cap N posts (smoke test)")
    ap.add_argument("--delay", type=float, default=0.25, help="seconds between fetches")
    ap.add_argument("--corpus-root", required=True, type=Path, help="Explicit corpus store root")
    args = ap.parse_args()
    if args.build_index:
        build_index()
    if args.ingest:
        ingest(CorpusStore(args.corpus_root), args.floor, args.max, args.delay)
    if not (args.build_index or args.ingest):
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
