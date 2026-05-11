"""Graph query CLI — `corpus cites|cited-by|ego|path|similar|contradictions|...`.

Backed by graph.duckdb (built by `corpus maintain --rebuild-graph`).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import store as ps


def _connect(read_only: bool = True):
    try:
        import duckdb  # type: ignore
    except ImportError:
        print("duckdb not installed", file=sys.stderr)
        sys.exit(2)
    gdb = ps.graph_db_path()
    if not gdb.exists():
        print(f"graph.duckdb missing; run `corpus maintain --rebuild-graph`", file=sys.stderr)
        sys.exit(1)
    return duckdb.connect(str(gdb), read_only=read_only)


def cmd_cites(args) -> int:
    con = _connect()
    rows = con.execute(
        "SELECT cited_paper_id, stance_class, stance_confidence, snippet FROM edges WHERE citing_paper_id = ?",
        [args.paper_id],
    ).fetchall()
    for r in rows:
        print(f"  → {r[0]}  [{r[1]}, conf={r[2]:.2f}]  {(r[3] or '')[:120]}")
    print(f"({len(rows)} edges)")
    return 0


def cmd_cited_by(args) -> int:
    con = _connect()
    q = "SELECT citing_paper_id, stance_class, stance_confidence, snippet FROM edges WHERE cited_paper_id = ?"
    params = [args.paper_id]
    if args.stance:
        q += " AND stance_class = ?"
        params.append(args.stance)
    rows = con.execute(q, params).fetchall()
    for r in rows:
        print(f"  ← {r[0]}  [{r[1]}, conf={r[2]:.2f}]  {(r[3] or '')[:120]}")
    print(f"({len(rows)} edges)")
    return 0


def cmd_contradictions(args) -> int:
    con = _connect()
    rows = con.execute(
        """SELECT e.citing_paper_id, e.snippet, p.retraction_status
           FROM edges e LEFT JOIN papers p ON p.paper_id = e.citing_paper_id
           WHERE e.cited_paper_id = ?
             AND (e.stance_class = 'contrasting' OR e.stance_cito LIKE '%disagreesWith%')""",
        [args.paper_id],
    ).fetchall()
    for r in rows:
        marker = " [RETRACTED]" if r[2] == "retracted" else ""
        print(f"  ⚠ {r[0]}{marker}  {(r[1] or '')[:140]}")
    print(f"({len(rows)} contradicting citances)")
    return 0


def cmd_ego(args) -> int:
    con = _connect()
    rows = con.execute(
        """WITH RECURSIVE ego(node, depth) AS (
              SELECT CAST(? AS TEXT), 0
              UNION
              SELECT e.cited_paper_id, ego.depth + 1
              FROM edges e JOIN ego ON e.citing_paper_id = ego.node
              WHERE ego.depth < ?
              UNION
              SELECT e.citing_paper_id, ego.depth + 1
              FROM edges e JOIN ego ON e.cited_paper_id = ego.node
              WHERE ego.depth < ?
           )
           SELECT DISTINCT node, MIN(depth) FROM ego GROUP BY node ORDER BY 2, 1""",
        [args.paper_id, args.depth, args.depth],
    ).fetchall()
    for r in rows:
        print(f"  depth={r[1]}  {r[0]}")
    print(f"({len(rows)} nodes in {args.depth}-hop ego graph)")
    return 0


def cmd_path(args) -> int:
    con = _connect()
    rows = con.execute(
        """WITH RECURSIVE paths(node, path, depth) AS (
              SELECT CAST(? AS TEXT), [CAST(? AS TEXT)], 0
              UNION ALL
              SELECT e.cited_paper_id, list_append(p.path, e.cited_paper_id), p.depth + 1
              FROM edges e JOIN paths p ON e.citing_paper_id = p.node
              WHERE p.depth < 6 AND NOT list_contains(p.path, e.cited_paper_id)
           )
           SELECT path FROM paths WHERE node = ? ORDER BY depth LIMIT 1""",
        [args.a, args.a, args.b],
    ).fetchone()
    if not rows:
        print(f"no path from {args.a} to {args.b} within 6 hops")
        return 1
    print(" → ".join(rows[0]))
    return 0


def cmd_similar(args) -> int:
    con = _connect()
    view = "co_citation_pairs" if args.via == "co-citation" else "biblio_coupling_pairs"
    metric_col = "co_citation_count" if args.via == "co-citation" else "shared_references"
    rows = con.execute(
        f"""SELECT CASE WHEN paper_a = ? THEN paper_b ELSE paper_a END AS other,
                   {metric_col}
            FROM {view}
            WHERE paper_a = ? OR paper_b = ?
            ORDER BY {metric_col} DESC LIMIT 25""",
        [args.paper_id, args.paper_id, args.paper_id],
    ).fetchall()
    for r in rows:
        print(f"  {r[1]:>4}  {r[0]}")
    print(f"({len(rows)} similar by {args.via})")
    return 0


def cmd_cluster(args) -> int:
    con = _connect()
    rows = con.execute(
        """SELECT cited_paper_id AS other, stance_class FROM edges WHERE citing_paper_id = ?
           UNION
           SELECT citing_paper_id AS other, stance_class FROM edges WHERE cited_paper_id = ?""",
        [args.seed, args.seed],
    ).fetchall()
    for r in rows:
        print(f"  {r[1]:>12}  {r[0]}")
    print(f"({len(rows)} papers in cluster of {args.seed})")
    return 0


def cmd_collection(args) -> int:
    coll_dir = ps.store_root() / "collections"
    coll_dir.mkdir(exist_ok=True)
    if args.action == "list":
        for f in sorted(coll_dir.glob("*.txt")):
            n = sum(1 for _ in f.open())
            print(f"  {f.stem:30s} ({n} papers)")
        return 0
    if args.action == "new":
        (coll_dir / f"{args.name}.txt").touch()
        print(f"  created collection {args.name}")
        return 0
    if args.action == "add":
        p = coll_dir / f"{args.name}.txt"
        with p.open("a") as fh:
            fh.write(args.paper_id + "\n")
        print(f"  added {args.paper_id} → {args.name}")
        return 0
    if args.action == "diff":
        print("  diff not implemented in Phase 1 (requires last-seen marker)")
        return 0
    return 2


def cmd_table(args) -> int:
    print("  `corpus table` deferred to Phase 5 (LLM extraction).")
    return 0


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("cites", help="Papers cited by this paper")
    p.add_argument("paper_id")
    p.set_defaults(func=cmd_cites)

    p = subparsers.add_parser("cited-by", help="Papers citing this paper")
    p.add_argument("paper_id")
    p.add_argument("--stance", choices=["supporting", "contrasting", "mentioning"])
    p.set_defaults(func=cmd_cited_by)

    p = subparsers.add_parser("contradictions", help="Contrasting incoming citances")
    p.add_argument("paper_id")
    p.set_defaults(func=cmd_contradictions)

    p = subparsers.add_parser("ego", help="N-hop ego graph")
    p.add_argument("paper_id")
    p.add_argument("--depth", type=int, default=1)
    p.set_defaults(func=cmd_ego)

    p = subparsers.add_parser("path", help="Shortest path between two papers")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(func=cmd_path)

    p = subparsers.add_parser("similar", help="Co-citation / bibliographic-coupling similarity")
    p.add_argument("paper_id")
    p.add_argument("--via", choices=["co-citation", "biblio-coupling"], default="co-citation")
    p.set_defaults(func=cmd_similar)

    p = subparsers.add_parser("cluster", help="Papers within N hops of a seed")
    p.add_argument("seed")
    p.add_argument("--hops", type=int, default=1)
    p.set_defaults(func=cmd_cluster)

    p = subparsers.add_parser("collection", help="Named subsets of papers (Scite-style)")
    p.add_argument("action", choices=["list", "new", "add", "diff"])
    p.add_argument("name", nargs="?")
    p.add_argument("paper_id", nargs="?")
    p.set_defaults(func=cmd_collection)

    p = subparsers.add_parser("table", help="Cross-paper extraction table (Phase 5)")
    p.add_argument("--cols", required=True)
    p.add_argument("--paper-ids", nargs="+", required=True)
    p.set_defaults(func=cmd_table)
