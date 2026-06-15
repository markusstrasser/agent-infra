"""`agentlogs` CLI — single entry point for the unified agent log store.

Subcommands:
  index     Discover + ingest new sources (respects single-writer lock)
  search    FTS over events, grouped by session or flat
  show      Pretty-print a session transcript
  recent    List recent sessions
  query     Run a named analytical SQL query
  stats     DB size, per-vendor counts, indexer health
  who       Code line/range → the session/model that authored it (blame + agentlogs)
  whence    A session → the code it produced (v_session_commits)
  dispatch  Run a session through an analysis prompt via llmx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .db import DEFAULT_DB_PATH, connect


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agentlogs",
        description=__doc__.splitlines()[0] if __doc__ else "",
    )
    p.add_argument("--db", default=None,
                   help=f"Path to agentlogs.db (default: {DEFAULT_DB_PATH})")
    p.add_argument("--version", action="version", version=f"agentlogs {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    # index
    s_index = sub.add_parser("index", help="Ingest new sessions from all vendors")
    s_index.add_argument("--vendor", action="append", choices=["claude", "codex", "cursor", "gemini", "kimi"],
                         help="Limit to one or more vendors (default: all)")
    s_index.add_argument("--limit-sources", type=int, default=None,
                         help="Cap sources per vendor (useful for smoke tests)")
    s_index.add_argument("--force", action="store_true",
                         help="Re-import even if source sha+parser_version already succeeded")
    s_index.add_argument("--no-lock", action="store_true",
                         help="Skip single-writer lock (debug only)")
    s_index.add_argument("--max-run-seconds", type=float, default=600.0,
                         help="Total wall-clock budget for the whole run. Checked "
                              "between sources (defers the rest to the next run); a "
                              "hard SIGALRM backstop at +60s covers an in-source hang. "
                              "0 disables. Default 600 (10 min).")
    s_index.add_argument("--source-timeout", type=float, default=180.0,
                         help="Per-source DB-work budget in seconds (sqlite progress-handler "
                              "watchdog). A source exceeding it is aborted + marked failed rather "
                              "than hanging the indexer (and its lock) indefinitely. Default 180.")
    s_index.add_argument("--since-days", type=float, default=None,
                         help="Only index sources modified within the last N days (rolling recency "
                              "window). Keeps runs cheap and avoids re-touching legacy sources. "
                              "Default: all history.")
    s_index.add_argument("--bulk", action="store_true",
                         help="Drop FTS triggers during indexing and rebuild the FTS index at the "
                              "end. Major speedup for large first-pass / catch-up runs (FTS triggers "
                              "fire per-event-row and dominate write time on big batches). Safe: "
                              "FTS5 'rebuild' regenerates from the events table content.")

    # search
    s_search = sub.add_parser("search", help="FTS search across events/sessions")
    s_search.add_argument("query", help="FTS5 query string")
    s_search.add_argument("--mode", choices=["session", "event"], default="session")
    s_search.add_argument("--vendor")
    s_search.add_argument("--project")
    s_search.add_argument("--since")
    s_search.add_argument("--until")
    s_search.add_argument("--kind")
    s_search.add_argument("--limit", type=int, default=50)
    s_search.add_argument("--format", choices=["table", "json"], default="table")

    # show
    s_show = sub.add_parser("show", help="Render a session transcript")
    s_show.add_argument("session", help="session_uuid or session_pk")
    s_show.add_argument("--format", choices=["text", "json"], default="text")

    # recent
    s_recent = sub.add_parser("recent", help="List recent sessions")
    s_recent.add_argument("--vendor")
    s_recent.add_argument("--project")
    s_recent.add_argument("-n", "--limit", type=int, default=20)
    s_recent.add_argument("--format", choices=["table", "json"], default="table")

    # query
    s_query = sub.add_parser("query", help="Run a named analytical query")
    s_query.add_argument("name", nargs="?", help="Query name (omit to list)")
    s_query.add_argument("--param", action="append", default=[],
                         help="Parameter in key=value form (repeatable)")
    s_query.add_argument("--format", choices=["table", "json"], default="table")

    # stats
    sub.add_parser("stats", help="Per-vendor counts + indexer health + DB size")

    # git-import
    s_git = sub.add_parser("git-import",
                           help="Import git commits with Session-ID attribution")
    s_git.add_argument("--days", type=int, default=30,
                       help="Lookback window (default: 30)")
    s_git.add_argument("--project", action="append",
                       help="Project(s) to import (default: agent-infra, intel, "
                            "phenome, genomics, skills)")

    # who — code line → session/model that authored it
    s_who = sub.add_parser("who", help="Which session/model authored a code line/range")
    s_who.add_argument("file", help="path[:LINE | :START-END] (e.g. src/agentlogs/db.py:25-40)")
    s_who.add_argument("--history", action="store_true",
                       help="Show EVERY session in the range's lineage (git log -L), "
                            "not just blame's last-touch. Requires a line range.")
    s_who.add_argument("--format", choices=["table", "json"], default="table")

    # whence — session → the code it produced
    s_whence = sub.add_parser("whence", help="What code a session produced")
    s_whence.add_argument("session", help="session_uuid / vendor_session_id")
    s_whence.add_argument("--format", choices=["table", "json"], default="table")

    # dispatch
    s_disp = sub.add_parser("dispatch", help="Analyze a session via llmx")
    s_disp.add_argument("session", help="session_uuid or session_pk")
    s_disp.add_argument("--prompt", help="Inline prompt text")
    s_disp.add_argument("--prompt-file", type=Path, help="Prompt from file")
    s_disp.add_argument("--model", default="gemini-3.1-pro-preview")
    s_disp.add_argument("--timeout", type=int, default=300)

    # prune ---------------------------------------------------------------
    s_prune = sub.add_parser(
        "prune",
        help="Delete sessions older than --keep-days and reclaim space (dry-run by default)",
    )
    s_prune.add_argument("--keep-days", type=int, default=21,
                         help="Retain sessions newer than this many days (default: 21)")
    s_prune.add_argument("--yes", "--apply", dest="apply", action="store_true",
                         help="Execute the prune (default: dry-run preview, deletes nothing)")
    s_prune.add_argument("--no-lock", action="store_true",
                         help="Skip the single-writer indexer lock (debug only)")

    return p


def _resolve_db_path(args) -> Path:
    return Path(args.db) if args.db else DEFAULT_DB_PATH


def _print_table(rows: list, columns: list[str] | None = None) -> None:
    if not rows:
        print("(no results)", file=sys.stderr)
        return
    if columns is None:
        columns = list(rows[0].keys()) if hasattr(rows[0], "keys") else None
    if columns is None:
        for row in rows:
            print(row)
        return
    widths = [len(c) for c in columns]
    render_rows: list[list[str]] = []
    for row in rows:
        values = [str(row[col] if row[col] is not None else "") for col in columns]
        render_rows.append(values)
        for i, v in enumerate(values):
            widths[i] = max(widths[i], len(v[:80]))
    print("  ".join(c.ljust(widths[i]) for i, c in enumerate(columns)))
    print("  ".join("-" * widths[i] for i in range(len(columns))))
    for values in render_rows:
        print("  ".join(values[i][:80].ljust(widths[i]) for i in range(len(values))))


def cmd_index(args) -> int:
    from . import index as ix
    from .locks import IndexerLockBusy, indexer_lock
    from .paths import AGENTLOGS_LOCK

    vendors = args.vendor or ["claude", "codex", "cursor", "gemini", "kimi"]

    def _run_all(reap: bool = False) -> int:
        db = connect(_resolve_db_path(args))
        if reap:
            # Under the exclusive lock, any 'running' row is a dead holder from a
            # prior crash/hard-deadline exit — finalize it so it stops tripping
            # doctor's stuck-holder warning.
            reaped = ix.reap_orphaned_runs(db)
            if reaped:
                print(f"[reap] finalized {reaped} orphaned 'running' indexer_runs row(s)")
        bulk = bool(getattr(args, "bulk", False))
        if bulk:
            # Drop FTS triggers — bulk-load mode rebuilds at the end.
            for trig in ("events_ai", "events_ad", "events_au"):
                db.execute(f"DROP TRIGGER IF EXISTS {trig}")
            print("[bulk] dropped FTS triggers — will rebuild after indexing")
        try:
            total_imported = total_skipped = total_failed = 0
            vendor_errors = 0
            since_ts = None
            if getattr(args, "since_days", None) is not None:
                import time as _time
                since_ts = _time.time() - args.since_days * 86400
            # Total wall-clock budget shared across all vendors (absolute
            # monotonic deadline). index_vendor checks it between sources and
            # defers the rest to the next run when exceeded.
            import time as _time2
            max_run_s = getattr(args, "max_run_seconds", 600.0) or 0.0
            run_deadline = (_time2.monotonic() + max_run_s) if max_run_s > 0 else None
            if max_run_s > 0:
                # Hard backstop for a hang INSIDE one source (pure-Python parse,
                # which the sqlite progress handler can't interrupt): SIGALRM
                # hard-exits so the flock + RAM are released. WAL rolls back any
                # open txn on next open; the run resumes next cycle. exit 75 and
                # no launchd KeepAlive => no crash-loop.
                import os as _os
                import signal as _signal
                def _hard_deadline(_sig, _frm):
                    _os.write(2, b"[agentlogs] HARD run deadline exceeded -- exiting 75\n")
                    _os._exit(75)
                try:
                    _signal.signal(_signal.SIGALRM, _hard_deadline)
                    _signal.setitimer(_signal.ITIMER_REAL, max_run_s + 60.0)
                except (ValueError, OSError):
                    pass  # not main thread / unsupported — soft deadline still applies
            # Fairness: index the most-behind vendor first so one vendor's big
            # backlog (claude, 1754 sessions) can't monopolize the shared
            # run_deadline and starve another. Codex went dark 06-09→06-13 exactly
            # this way (claude indexed first, ate the budget; same class as the
            # May-4 incident). Order by each vendor's newest session, oldest-first;
            # vendors with no sessions yet sort first (most behind).
            run_vendors = vendors
            if len(vendors) > 1:
                placeholders = ",".join("?" * len(vendors))
                newest = dict(db.execute(
                    f"SELECT vendor, MAX(start_ts) FROM sessions "
                    f"WHERE vendor IN ({placeholders}) GROUP BY vendor",
                    vendors,
                ).fetchall())
                run_vendors = sorted(vendors, key=lambda v: (newest.get(v) or ""))
            for v in run_vendors:
                stats = ix.index_vendor(
                    db, v, limit_sources=args.limit_sources, force=args.force,
                    source_timeout_s=getattr(args, "source_timeout", 180.0),
                    since_ts=since_ts, deadline=run_deadline,
                )
                # index_vendor catches outer exceptions and writes
                # indexer_runs.status='error'; check for those vendor-level
                # fatals so the CLI exits non-zero.
                latest = db.execute(
                    "SELECT status FROM indexer_runs "
                    "WHERE vendor = ? ORDER BY run_id DESC LIMIT 1",
                    (v,),
                ).fetchone()
                if latest and latest["status"] == "error":
                    vendor_errors += 1
                print(
                    f"{v}: discovered={stats.sources_discovered} "
                    f"imported={stats.sources_imported} skipped={stats.sources_skipped} "
                    f"failed={stats.sources_failed} events={stats.events_written}"
                    + (" [VENDOR ERROR]" if (latest and latest["status"] == "error") else "")
                )
                total_imported += stats.sources_imported
                total_skipped += stats.sources_skipped
                total_failed += stats.sources_failed
            return 1 if (total_failed or vendor_errors) else 0
        finally:
            if bulk:
                # Rebuild FTS index from events table content, then recreate
                # triggers so subsequent (non-bulk) indexing keeps FTS in sync.
                print("[bulk] rebuilding events_fts...")
                db.execute("INSERT INTO events_fts(events_fts) VALUES('rebuild')")
                db.execute("""
                    CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
                        INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
                    END
                """)
                db.execute("""
                    CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
                        INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
                    END
                """)
                db.execute("""
                    CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
                        INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
                        INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
                    END
                """)
                print("[bulk] FTS rebuilt + triggers restored")
            db.close()

    if args.no_lock:
        return _run_all()
    try:
        with indexer_lock(AGENTLOGS_LOCK, timeout_s=30.0):
            return _run_all(reap=True)
    except IndexerLockBusy:
        print("another indexer is running; exiting cleanly", file=sys.stderr)
        return 0


def cmd_search(args) -> int:
    from . import search as se

    db = connect(_resolve_db_path(args))
    try:
        if args.mode == "session":
            hits = se.search_sessions(
                db, args.query,
                vendor=args.vendor, project=args.project,
                since=args.since, until=args.until, limit=args.limit,
            )
            if args.format == "json":
                print(json.dumps([h.__dict__ for h in hits], indent=2, default=str))
            else:
                if not hits:
                    print("(no hits)", file=sys.stderr)
                    return 0
                for h in hits:
                    print(
                        f"{h.session_uuid or h.session_pk}  "
                        f"{h.vendor:<8}  {h.project_slug or '-':<16}  "
                        f"{h.matching_events:>3} hits  {h.start_ts or '-'}"
                    )
                    if h.snippet:
                        print(f"  {h.snippet}")
        else:
            hits = se.search_events(
                db, args.query,
                vendor=args.vendor, project=args.project,
                since=args.since, until=args.until, kind=args.kind,
                limit=args.limit,
            )
            if args.format == "json":
                print(json.dumps([h.__dict__ for h in hits], indent=2, default=str))
            else:
                for h in hits:
                    print(f"[{h.ts or '-'}] {h.vendor}/{h.project_slug or '-'} "
                          f"{h.kind}: {h.snippet}")
        return 0
    finally:
        db.close()


def cmd_show(args) -> int:
    from . import search as se
    from . import show as sh

    db = connect(_resolve_db_path(args))
    try:
        row = se.get_session(db, args.session)
        if not row:
            print(f"session not found: {args.session}", file=sys.stderr)
            return 2
        if args.format == "json":
            print(sh.render_json(db, row["session_pk"]))
        else:
            print(sh.render_text(db, row["session_pk"]))
        return 0
    finally:
        db.close()


def cmd_recent(args) -> int:
    from . import search as se

    db = connect(_resolve_db_path(args))
    try:
        rows = se.recent_sessions(
            db, vendor=args.vendor, project=args.project, limit=args.limit,
        )
        if args.format == "json":
            print(json.dumps([dict(r) for r in rows], indent=2, default=str))
        else:
            _print_table(
                rows,
                ["session_uuid", "vendor", "project_slug", "start_ts",
                 "duration_min", "model", "first_message"],
            )
        return 0
    finally:
        db.close()


def cmd_query(args) -> int:
    from . import query as q

    if not args.name:
        for name in q.list_queries():
            qparams = q.query_params(name)
            suffix = f"  params: {', '.join(qparams)}" if qparams else ""
            print(f"  {name}{suffix}")
        return 0

    db = connect(_resolve_db_path(args))
    try:
        params: dict[str, object] = {}
        for kv in args.param:
            if "=" not in kv:
                print(f"bad --param {kv!r} (expected key=value)", file=sys.stderr)
                return 2
            k, _, v = kv.partition("=")
            # Coerce numeric-looking values so :limit / :offset bind as INTEGER.
            try:
                params[k] = int(v)
            except ValueError:
                try:
                    params[k] = float(v)
                except ValueError:
                    params[k] = v
        rows = q.run_query(db, args.name, **params)
        if args.format == "json":
            print(json.dumps([dict(r) for r in rows], indent=2, default=str))
        else:
            _print_table(rows)
        return 0
    finally:
        db.close()


def cmd_stats(args) -> int:
    from dataclasses import asdict
    from . import health as h

    db_path = _resolve_db_path(args)
    db = connect(db_path)
    try:
        size_mb = h.db_size_bytes(db_path) / 1024 / 1024
        print(f"DB: {db_path}  ({size_mb:.1f} MB)")
        print()
        stats = h.vendor_stats(db)
        _print_table(
            [asdict(vs) for vs in stats],
            ["vendor", "sessions", "runs", "events", "tool_calls",
             "last_session_at", "last_index_success_at",
             "last_index_error_at", "errors_7d"],
        )
        return 0
    finally:
        db.close()


def cmd_dispatch(args) -> int:
    from . import dispatch as dp
    from . import search as se

    prompt: str | None = args.prompt
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    if not prompt:
        print("--prompt or --prompt-file required", file=sys.stderr)
        return 2

    db = connect(_resolve_db_path(args))
    try:
        row = se.get_session(db, args.session)
        if not row:
            print(f"session not found: {args.session}", file=sys.stderr)
            return 2
        return dp.dispatch_session(
            db, row["session_pk"],
            prompt=prompt, model=args.model, timeout_s=args.timeout,
        )
    finally:
        db.close()


def cmd_git_import(args) -> int:
    from .git_import import import_git_commits

    db = connect(_resolve_db_path(args))
    try:
        count = import_git_commits(
            db, projects=args.project, days=args.days,
        )
        print(f"Imported {count} commits across "
              f"{len(args.project) if args.project else 5} projects "
              f"({args.days}d window)")
        # Summary of newly-visible fix-of-fix chains
        rows = db.execute(
            "SELECT COUNT(*) FROM v_fix_chains WHERE fix1_date >= "
            "date('now', ?)", (f"-{args.days} days",),
        ).fetchone()
        if rows and rows[0]:
            print(f"Fix-of-fix chains in window: {rows[0]}")
        return 0
    finally:
        db.close()


def _fmt_who_row(h) -> dict:
    # Prefer the RAW trailer id (h.session_id) — it matches the trailer and is what
    # `whence`/`show` accept. session_uuid is `vendor:raw`-namespaced; strip the prefix.
    sid = h.session_id or (h.session_uuid or "").split(":", 1)[-1] or "unknown"
    return {
        "lines": f"{h.start}-{h.end}" if h.end != h.start else str(h.start),
        "commit": h.sha[:8],
        "date": (h.authored_at or "")[:10],
        "session": sid[:8] if sid != "unknown" else "unknown",
        "model": h.model or ("unknown" if h.note == "pre-index" else "-"),
        "effort": "n/a",
        "scope": h.scope or "-",
        "subject": (h.subject or "")[:48],
        "note": h.note or "",
    }


def cmd_who(args) -> int:
    from . import provenance as pv

    db = connect(_resolve_db_path(args))
    try:
        fn = pv.history if args.history else pv.who
        try:
            rel, hunks = fn(db, args.file)
        except (FileNotFoundError, ValueError) as e:
            print(f"who: {e}", file=sys.stderr)
            return 2
        rows = [_fmt_who_row(h) for h in hunks]
        if args.format == "json":
            print(json.dumps(rows, indent=2, default=str))
            return 0
        mode = "lineage (oldest→newest)" if args.history else "last-authored"
        print(f"{rel}  [{mode}]")
        _print_table(
            rows,
            ["lines", "commit", "date", "session", "model", "effort", "scope", "subject", "note"],
        )
        return 0
    finally:
        db.close()


def cmd_whence(args) -> int:
    from . import provenance as pv

    db = connect(_resolve_db_path(args))
    try:
        sess, rows = pv.whence(db, args.session)
        if args.format == "json":
            print(json.dumps(
                {"session": dict(sess) if sess else None,
                 "commits": [dict(r) for r in rows]},
                indent=2, default=str))
            return 0
        if sess is None and not rows:
            print(f"no session or commits for {args.session!r}", file=sys.stderr)
            return 2
        if sess is not None:
            print(f"session {sess['session_uuid']}  {sess['vendor']}  "
                  f"model={sess['model'] or 'unknown'}  "
                  f"start={sess['start_ts'] or '-'}  "
                  f"dur={sess['duration_min'] or '-'}min  "
                  f"lines={sess['transcript_lines'] or '-'}")
        print(f"produced {len(rows)} commit(s):")
        _print_table(
            rows,
            ["authored_at", "hash", "project", "files",
             "insertions", "deletions", "subject"],
        )
        return 0
    finally:
        db.close()


def cmd_prune(args) -> int:
    from . import prune as pr
    from .locks import IndexerLockBusy, indexer_lock
    from .paths import AGENTLOGS_LOCK

    def _run() -> int:
        db = connect(_resolve_db_path(args))
        try:
            if not args.apply:
                plan = pr.plan_prune(db, args.keep_days)
                print(f"[dry-run] keep_days={plan.keep_days}  cutoff={plan.cutoff}")
                print(f"  would delete: sessions={plan.sessions:,} runs={plan.runs:,} "
                      f"events={plan.events:,} tool_calls={plan.tool_calls:,} "
                      f"file_touches={plan.file_touches:,} record_refs≈{plan.record_refs:,}")
                print(f"  db size now: {plan.size_before_mb:,.0f} MB "
                      f"(VACUUM reclaims free pages on --yes)")
                print("  re-run with --yes to execute")
                return 0
            plan = pr.apply_prune(db, args.keep_days)
            reclaimed = plan.size_before_mb - (plan.size_after_mb or plan.size_before_mb)
            print(f"[pruned] keep_days={plan.keep_days}  cutoff={plan.cutoff}")
            print(f"  deleted: sessions={plan.sessions:,} runs={plan.runs:,} "
                  f"events={plan.events:,} tool_calls={plan.tool_calls:,} "
                  f"file_touches={plan.file_touches:,} record_refs={plan.record_refs:,}")
            print(f"  db size: {plan.size_before_mb:,.0f} MB -> "
                  f"{plan.size_after_mb:,.0f} MB (reclaimed {reclaimed:,.0f} MB)")
            return 0
        finally:
            db.close()

    if args.no_lock:
        return _run()
    try:
        with indexer_lock(AGENTLOGS_LOCK, timeout_s=30.0):
            return _run()
    except IndexerLockBusy:
        print("another indexer/prune is running; exiting cleanly", file=sys.stderr)
        return 0


_COMMANDS = {
    "index": cmd_index,
    "prune": cmd_prune,
    "search": cmd_search,
    "show": cmd_show,
    "recent": cmd_recent,
    "query": cmd_query,
    "stats": cmd_stats,
    "dispatch": cmd_dispatch,
    "git-import": cmd_git_import,
    "who": cmd_who,
    "whence": cmd_whence,
}


def main(argv: list[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)
    return _COMMANDS[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
