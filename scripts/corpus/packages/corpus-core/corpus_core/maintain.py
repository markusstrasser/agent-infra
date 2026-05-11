"""Store maintenance — stats, verify, rebuild indexes/citances/graph, gc.

`gc` requires `--after-rebuild` flag in the same invocation; refuses to operate
on a stale INDEX.json (model-review #11).
"""
from __future__ import annotations

import argparse
import importlib.resources
import json
import sys
from pathlib import Path
from typing import Optional

from . import store as ps
from . import extract_citances as ec


SCHEMA_RESOURCE = "graph_schema.sql"


def _read_schema() -> str:
    here = Path(__file__).parent
    sql = (here / SCHEMA_RESOURCE).read_text()
    return sql


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def cmd_stats(args) -> int:
    root = ps.store_root()
    if not root.exists():
        print(f"papers=0 size=0  (store does not exist at {root})")
        return 0
    paper_ids = list(ps.iter_papers())
    total_size = 0
    by_repo: dict[str, int] = {}
    drifted = 0
    no_used_by = 0
    for pid in paper_ids:
        p = ps.paper_path(pid)
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total_size += f.stat().st_size
                except OSError:
                    pass
        meta = ps.get(pid).metadata
        for repo in meta.get("used_by_repos") or []:
            by_repo[repo] = by_repo.get(repo, 0) + 1
        if not meta.get("used_by_repos"):
            no_used_by += 1
    print(f"papers={len(paper_ids)}  size={_human_size(total_size)}")
    if by_repo:
        for repo, n in sorted(by_repo.items()):
            print(f"  by repo: {repo}={n}")
    print(f"  no used_by:  {no_used_by}")

    # Graph stats
    gdb = ps.graph_db_path()
    if gdb.exists():
        try:
            import duckdb  # type: ignore
            con = duckdb.connect(str(gdb), read_only=True)
            n_edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            n_papers = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            n_annot = con.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
            con.close()
            print(f"  graph: nodes={n_papers} edges={n_edges} annotations={n_annot}")
        except Exception as exc:
            print(f"  graph: (read failed: {exc})")
    return 0


def cmd_show(args) -> int:
    try:
        rec = ps.get(args.paper_id)
    except ps.PaperNotFoundError:
        print(f"paper not found: {args.paper_id}", file=sys.stderr)
        return 1
    meta = rec.metadata
    print(f"paper_id:        {rec.paper_id}")
    print(f"doi:             {meta.get('doi')}")
    print(f"pmid:            {meta.get('pmid')}")
    print(f"title:           {meta.get('title')}")
    print(f"pdf_sha256:      {meta.get('pdf_sha256')}")
    print(f"parsed_sha256:   {meta.get('parsed_sha256')}")
    print(f"retrieved_at:    {meta.get('retrieved_at')}")
    print(f"path:            {rec.path}")
    print(f"pdf:             {rec.pdf_path}")
    print(f"parsed/:         {rec.parsed_dir}")
    parser = meta.get("parser") or {}
    if parser:
        print(f"parser_id:       {parser.get('parser_id')}")
        print(f"  marker:        {parser.get('marker_version')}")
        print(f"  llm:           {parser.get('llm_service')}")
        print(f"  pages_total:   {parser.get('pages_total')}")
    if args.depth == "full":
        cin = rec.path / "citances_in.jsonl"
        cout = rec.path / "citances_out.jsonl"
        ann = rec.path / "annotations.jsonl"
        def _count(p: Path) -> int:
            return sum(1 for _ in p.open()) if p.exists() else 0
        print(f"citances_in:     {_count(cin)}")
        print(f"citances_out:    {_count(cout)}")
        print(f"annotations:     {_count(ann)}")
        used = meta.get("used_by_repos") or []
        print(f"used_by_repos:   {used}")
        revisions = meta.get("revisions") or []
        if revisions:
            print(f"revisions ({len(revisions)}):")
            for r in revisions:
                print(f"  - {r.get('retired_at')}  prior_pdf_sha={r.get('prior_pdf_sha256','')[:16]}")
    return 0


def cmd_verify(args) -> int:
    drift = 0
    for pid in ps.iter_papers():
        rec = ps.get(pid)
        if rec.pdf_path.exists():
            actual_pdf = ps.sha256_file(rec.pdf_path)
            if rec.metadata.get("pdf_sha256") != actual_pdf:
                print(f"  ! {pid} pdf_sha256 drift: meta={rec.metadata.get('pdf_sha256','')[:16]} actual={actual_pdf[:16]}")
                drift += 1
        if rec.parsed_dir.is_dir():
            actual_parsed = ps.compute_parsed_sha(rec.parsed_dir)
            if rec.metadata.get("parsed_sha256") != actual_parsed:
                print(f"  ! {pid} parsed_sha256 drift: meta={rec.metadata.get('parsed_sha256','')[:16]} actual={actual_parsed[:16]}")
                drift += 1
    print(f"verify: {drift} drifted papers")
    return 1 if drift else 0


def cmd_rebuild_indexes(args) -> int:
    """Rebuild INDEX.json per paper by grepping `canonical_paper_id` across repos."""
    import subprocess
    repos = [Path.home() / "Projects" / r for r in ("genomics", "phenome", "research-mcp", "agent-infra")]
    paper_ids = list(ps.iter_papers())
    refs_by_paper: dict[str, list[dict]] = {pid: [] for pid in paper_ids}
    for repo in repos:
        if not repo.exists():
            continue
        try:
            out = subprocess.check_output(
                ["git", "-C", str(repo), "grep", "-h", "-E", "canonical_paper_id"],
                stderr=subprocess.DEVNULL, text=True,
            )
        except subprocess.CalledProcessError:
            continue
        for line in out.splitlines():
            for pid in paper_ids:
                if pid in line:
                    refs_by_paper[pid].append({"repo": repo.name, "evidence": line.strip()[:200]})
    for pid, used_by in refs_by_paper.items():
        index_path = ps.paper_path(pid) / "INDEX.json"
        index_path.write_text(json.dumps({"paper_id": pid, "used_by": used_by}, indent=2))
    print(f"rebuilt INDEX.json for {len(paper_ids)} papers")
    return 0


def cmd_rebuild_citances(args) -> int:
    if args.paper_id:
        targets = [args.paper_id]
    else:
        targets = list(ps.iter_papers())
    for pid in targets:
        try:
            ec.extract_citances(pid)
        except Exception as exc:
            print(f"  ! {pid}: {exc}", file=sys.stderr)
    return 0


def cmd_rebuild_graph(args) -> int:
    try:
        import duckdb  # type: ignore
    except ImportError:
        print("duckdb not installed; run `uv pip install duckdb` or install via the uv tool.", file=sys.stderr)
        return 2
    gdb = ps.graph_db_path()
    if gdb.exists():
        gdb.unlink()
    con = duckdb.connect(str(gdb))
    con.execute(_read_schema())
    n_edges = 0
    n_papers = 0
    n_annot = 0
    for pid in ps.iter_papers():
        rec = ps.get(pid)
        meta = rec.metadata
        con.execute(
            "INSERT OR REPLACE INTO papers VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                pid,
                meta.get("doi"),
                meta.get("pmid"),
                meta.get("title"),
                meta.get("fabio_class"),
                meta.get("wikidata_qid"),
                meta.get("openalex_id"),
                meta.get("retrieved_at"),
                meta.get("retraction_status"),
                meta.get("used_by_repos") or [],
            ],
        )
        n_papers += 1
        for f in ("citances_in.jsonl", "citances_out.jsonl"):
            path = rec.path / f
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                # citances_in: rows carry citing_paper_id; cited_paper_id is THIS paper (the dir).
                # citances_out: rows carry cited_paper_id; citing_paper_id is THIS paper.
                citing = row.get("citing_paper_id") or (rec.paper_id if f == "citances_out.jsonl" else None)
                cited = row.get("cited_paper_id") or (rec.paper_id if f == "citances_in.jsonl" else None)
                if not citing or not cited:
                    continue
                try:
                    con.execute(
                        """INSERT OR REPLACE INTO edges VALUES
                           (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        [
                            citing,
                            cited,
                            row["citance_id"],
                            row["stance_class"],
                            row.get("stance_cito"),
                            row.get("stance_confidence"),
                            row.get("stance_source") or "unknown",
                            row.get("snippet") or "",
                            row.get("citing_section"),
                            row.get("citing_page"),
                            row.get("providers") or [],
                            row.get("fetched_at"),
                        ],
                    )
                    n_edges += 1
                except Exception as exc:
                    print(f"  ! edge insert failed: {exc}", file=sys.stderr)
        ann = rec.path / "annotations.jsonl"
        if ann.exists():
            for line in ann.read_text().splitlines():
                if not line.strip():
                    continue
                a = json.loads(line)
                try:
                    con.execute(
                        "INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?,?,?,?,?)",
                        [
                            a["event_id"],
                            pid,
                            a["annotated_at"],
                            a["annotated_by"],
                            (a.get("target") or {}).get("kind") or "paper",
                            (a.get("target") or {}).get("ref"),
                            a["kind"],
                            a["body"],
                            (a.get("links") or {}).get("claim_ids") or [],
                        ],
                    )
                    n_annot += 1
                except Exception as exc:
                    print(f"  ! annotation insert failed: {exc}", file=sys.stderr)
    con.close()
    print(f"rebuilt graph.duckdb  papers={n_papers} edges={n_edges} annotations={n_annot}")
    return 0


def cmd_gc(args) -> int:
    # Enforce --after-rebuild + the rebuild must have run in THIS invocation.
    if not args.after_rebuild:
        print("`corpus maintain --gc` requires --after-rebuild (model-review #11)", file=sys.stderr)
        print("Run: corpus maintain --rebuild-indexes && corpus maintain --gc --after-rebuild --dry-run", file=sys.stderr)
        return 2
    if not args._rebuild_ran_this_invocation:
        print("`--after-rebuild` set but --rebuild-indexes was not run in this invocation.", file=sys.stderr)
        return 2
    candidates: list[str] = []
    for pid in ps.iter_papers():
        index_path = ps.paper_path(pid) / "INDEX.json"
        if not index_path.exists():
            continue
        idx = json.loads(index_path.read_text())
        if not idx.get("used_by"):
            candidates.append(pid)
    print(f"gc candidates (papers with no used_by): {len(candidates)}")
    for pid in candidates:
        print(f"  - {pid}")
    if args.dry_run:
        print("(dry-run; no deletions)")
    else:
        print("(non-dry gc not enabled in Phase 1)")
    return 0


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("stats", help="Store summary")
    p.set_defaults(func=cmd_stats)

    p = subparsers.add_parser("show", help="Show metadata for one paper")
    p.add_argument("paper_id")
    p.add_argument("--depth", choices=["meta", "full"], default="meta")
    p.set_defaults(func=cmd_show)

    p = subparsers.add_parser("maintain", help="Verify / rebuild / gc")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--rebuild-indexes", action="store_true")
    p.add_argument("--rebuild-citances", action="store_true")
    p.add_argument("--rebuild-graph", action="store_true")
    p.add_argument("--gc", action="store_true")
    p.add_argument("--after-rebuild", action="store_true",
                   help="Required for --gc (model-review #11)")
    p.add_argument("--all", action="store_true", help="With --rebuild-citances, all papers")
    p.add_argument("--paper-id", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_maintain)


def _cmd_maintain(args) -> int:
    args._rebuild_ran_this_invocation = False
    if not any([args.verify, args.rebuild_indexes, args.rebuild_citances,
                args.rebuild_graph, args.gc]):
        print("specify one of --verify --rebuild-indexes --rebuild-citances --rebuild-graph --gc",
              file=sys.stderr)
        return 2
    rc = 0
    if args.verify:
        rc = max(rc, cmd_verify(args))
    if args.rebuild_indexes:
        rc = max(rc, cmd_rebuild_indexes(args))
        args._rebuild_ran_this_invocation = True
    if args.rebuild_citances:
        rc = max(rc, cmd_rebuild_citances(args))
    if args.rebuild_graph:
        rc = max(rc, cmd_rebuild_graph(args))
    if args.gc:
        rc = max(rc, cmd_gc(args))
    return rc
