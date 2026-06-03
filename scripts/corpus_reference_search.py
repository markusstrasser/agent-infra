#!/usr/bin/env python3
"""Full-text reference search over LessWrong + Gwern sources in the shared corpus.

The corpus store is graph/citation-oriented and has no text search. This builds a
DuckDB FTS index over the parsed markdown of all `source in {lesswrong, gwern}`
blog_post sources and queries it with metadata filters (source, karma, tag, author).

    # Build / refresh the index (run after an ingest completes)
    corpus_reference_search.py --build

    # Search
    corpus_reference_search.py "mesa optimization"
    corpus_reference_search.py "spaced repetition" --source gwern
    corpus_reference_search.py "AI timelines" --source lesswrong --min-karma 100 --limit 15
    corpus_reference_search.py "scaling laws" --tag "AI" --full   # print top hit body

Index lives at --corpus-root/reference_fts.duckdb (rebuilt, not authoritative).

Run with the corpus-core tool interpreter:
    ~/.local/share/uv/tools/corpus-core/bin/python3 corpus_reference_search.py ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
from corpus_core.store import CorpusStore

SOURCES = ("lesswrong", "gwern")


def _title_from_md(body: str) -> str:
    """trafilatura writes `title:` into a YAML frontmatter block; fall back to # H1."""
    for ln in body.splitlines()[:15]:
        if ln.startswith("title:"):
            return ln[len("title:"):].strip()
        if ln.startswith("# "):
            return ln[2:].strip()
    return ""


def _page_md(p_path: Path) -> str | None:
    cands = sorted(p_path.glob("parsed.*/page.md"))
    for c in cands:
        if "trafilatura" in c.parent.name:
            return c.read_text(encoding="utf-8", errors="replace")
    return cands[0].read_text(encoding="utf-8", errors="replace") if cands else None


def build(store: CorpusStore) -> None:
    root = store.root
    db = store.root / "reference_fts.duckdb"
    rows = []
    scanned = 0
    for meta_path in root.glob("*/metadata.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:  # noqa: BLE001
            continue
        if meta.get("source") not in SOURCES:
            continue
        body = _page_md(meta_path.parent)
        if not body:
            continue
        scanned += 1
        title = meta.get("title") or _title_from_md(body)
        rows.append((
            meta.get("source_id"),
            meta.get("source"),
            title,
            meta.get("source_url") or meta.get("lw_url") or "",
            int(meta.get("karma") or 0),
            meta.get("author") or "",
            (meta.get("posted_at") or "")[:10],
            " ".join(meta.get("tags") or []),
            len(body),
            body,
        ))
    if not rows:
        sys.exit("no lesswrong/gwern sources found — run the ingesters first")

    db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    con.execute("INSTALL fts; LOAD fts")
    con.execute(
        "CREATE TABLE refs(source_id VARCHAR, source VARCHAR, title VARCHAR, "
        "url VARCHAR, karma INTEGER, author VARCHAR, posted_at VARCHAR, "
        "tags VARCHAR, n_chars INTEGER, body VARCHAR)"
    )
    con.executemany("INSERT INTO refs VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute(
        "PRAGMA create_fts_index('refs','source_id','title','body','tags',"
        "overwrite=1)"
    )
    by_src = con.execute(
        "SELECT source, count(*), median(n_chars)::INT FROM refs GROUP BY source"
    ).fetchall()
    con.close()
    print(f"  ✓ indexed {len(rows)} sources -> {db}")
    for s, c, med in by_src:
        print(f"      {s:<10} {c:>6} sources  (median {med} chars)")


def search(store: CorpusStore, q, source, min_karma, tag, author, limit, full) -> None:
    db = store.root / "reference_fts.duckdb"
    if not db.exists():
        sys.exit("index not built — run --build first")
    con = duckdb.connect(str(db), read_only=True)
    con.execute("LOAD fts")
    where = ["score IS NOT NULL"]
    params: list = [q]
    if source:
        where.append("source = ?"); params.append(source)
    if min_karma:
        where.append("karma >= ?"); params.append(min_karma)
    if tag:
        where.append("tags ILIKE ?"); params.append(f"%{tag}%")
    if author:
        where.append("author ILIKE ?"); params.append(f"%{author}%")
    params.append(limit)
    sql = f"""
        WITH scored AS (
            SELECT *, fts_main_refs.match_bm25(source_id, ?) AS score FROM refs
        )
        SELECT source_id, source, title, url, karma, author, posted_at, n_chars,
               score, body
        FROM scored WHERE {' AND '.join(where)}
        ORDER BY score DESC LIMIT ?
    """
    rows = con.execute(sql, params).fetchall()
    con.close()
    if not rows:
        print("(no matches)")
        return
    for r in rows:
        src, title, url, karma, auth, dt, nch, score, body = r[1:]
        km = f"  karma={karma}" if src == "lesswrong" else ""
        print(f"\n[{score:.2f}] {src} · {title[:80]}{km}")
        print(f"      {auth}  {dt}  {nch} chars  {url}")
        if not full:
            snippet = " ".join(body.split())[:300]
            print(f"      {snippet}…")
    if full:
        print("\n" + "=" * 80 + f"\nTOP HIT FULL BODY: {rows[0][2]}\n" + "=" * 80)
        print(rows[0][9])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="?", help="FTS query (DuckDB BM25)")
    ap.add_argument("--corpus-root", required=True, type=Path, help="Explicit corpus store root")
    ap.add_argument("--build", action="store_true", help="(re)build the FTS index")
    ap.add_argument("--source", choices=SOURCES)
    ap.add_argument("--min-karma", type=int, default=0)
    ap.add_argument("--tag")
    ap.add_argument("--author")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--full", action="store_true", help="print full body of top hit")
    args = ap.parse_args()
    store = CorpusStore(args.corpus_root)
    if args.build:
        build(store)
    if args.query:
        search(store, args.query, args.source, args.min_karma, args.tag, args.author,
               args.limit, args.full)
    if not (args.build or args.query):
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
