#!/usr/bin/env python3
"""Ingest Gwern.net essays into the shared corpus.

Gwern publishes a sitemap (https://gwern.net/sitemap.xml). It contains ~22k URLs,
but ~20k are the /doc/ mirror of third-party papers/data (PDFs, CSVs, zips) — NOT
Gwern's own writing. We keep only the essay-class pages: extensionless, non-/doc/
URLs (his essays, notes, fiction, blog, newsletters). That's ~670 pages.

Gwern's pages are static HTML with `cache-control: immutable`, so trafilatura-on-URL
extracts cleanly (validated: scaling-hypothesis -> 124k chars). We reuse the corpus
ingest_url path directly.

    corpus_ingest_gwern.py                 # ingest all essays (resumable)
    corpus_ingest_gwern.py --no-newsletters  # skip /newsletter/* link digests
    corpus_ingest_gwern.py --max 5         # smoke test

Each page lands in $CORPUS_ROOT as a content-addressed sha_<hash> source,
source_type=blog_post, extra_metadata={source:gwern, gwern_path:...}.

Run with the corpus-core tool interpreter:
    ~/.local/share/uv/tools/corpus-core/bin/python3 corpus_ingest_gwern.py ...
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import httpx
from corpus_core import ingest as ci

SITEMAP = "https://gwern.net/sitemap.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 corpus-ingest (+local research mirror)"}
HERE = Path(__file__).resolve().parent
DONE = HERE / "gwern_ingested.txt"

# extensionless = no `.ext` in the final path segment
_EXT_RE = re.compile(r"\.[a-z0-9]{1,5}$", re.I)
# non-essay sections: build scripts, assets, generated metadata
_EXCLUDE_PREFIXES = ("/doc/", "/static/", "/metadata/")


def essay_urls(include_newsletters: bool) -> list[str]:
    r = httpx.get(SITEMAP, headers=HEADERS, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    locs = re.findall(r"<loc>(https://gwern\.net[^<]*)</loc>", r.text)
    out = []
    for u in locs:
        path = u[len("https://gwern.net"):]
        if any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
            continue
        if _EXT_RE.search(u):
            continue
        if not include_newsletters and path.startswith("/newsletter/"):
            continue
        out.append(u)
    # de-dup, stable order
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def _load_done() -> set[str]:
    if DONE.exists():
        return {ln.strip() for ln in DONE.read_text().splitlines() if ln.strip()}
    return set()


def run(include_newsletters: bool, limit: int | None, delay: float) -> None:
    urls = essay_urls(include_newsletters)
    done = _load_done()
    todo = [u for u in urls if u not in done]
    if limit:
        todo = todo[:limit]
    total = len(todo)
    print(f"[gwern] {len(urls)} essay-class pages, {len(done)} done, "
          f"{total} to ingest\n", flush=True)

    ok = fail = 0
    with DONE.open("a") as donefh:
        for i, u in enumerate(todo, 1):
            path = u[len("https://gwern.net"):]
            try:
                meta = ci.ingest_url(
                    u,
                    source_type="blog_post",
                    extra_metadata={"source": "gwern", "gwern_path": path},
                )
                chars = (meta.get("parser") or {}).get("char_count", 0)
                if not chars:
                    # empty extraction (redirect stub / asset) — drop the source
                    from corpus_core import store as ps
                    import shutil
                    sd = ps.paper_path(meta["source_id"])
                    if sd.exists():
                        shutil.rmtree(sd, ignore_errors=True)
                    print(f"  · [{i}/{total}] {path} empty — dropped", flush=True)
                    fail += 1
                    time.sleep(delay)
                    continue
                donefh.write(u + "\n")
                donefh.flush()
                ok += 1
                if i % 20 == 0 or i == total:
                    print(f"  [{i}/{total}] {path} ({chars} chars)", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  ! [{i}/{total}] {path} ERROR: {str(e)[:120]}", flush=True)
                fail += 1
            time.sleep(delay)
    print(f"\n  ✓ gwern done — {ok} ok, {fail} failed", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-newsletters", action="store_true",
                    help="skip /newsletter/* monthly link digests")
    ap.add_argument("--max", type=int, default=None, help="cap N pages (smoke test)")
    ap.add_argument("--delay", type=float, default=0.8, help="seconds between fetches")
    ap.add_argument("--list", action="store_true", help="just print the URL list")
    args = ap.parse_args()
    if args.list:
        for u in essay_urls(not args.no_newsletters):
            print(u)
        return 0
    run(not args.no_newsletters, args.max, args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
