#!/usr/bin/env python3
"""Export agentlogs sessions → JSONL for `emb embed` (the embed-once feed).

The durable, angle-agnostic extraction layer: embed sessions ONCE, then every future
angle is a free `emb search` / cheap `emb read` — no per-angle LLM re-read of the corpus.
Validated 2026-06-17 (research/2026-06-17-embed-once-validated-recurring-mistakes.md).

  uv run python3 scripts/export_sessions_for_emb.py --out sessions.jsonl
  uv run --project ~/Projects/emb emb embed sessions.jsonl -o session_index/ --chunk
  uv run --project ~/Projects/emb emb search session_index/ "any new angle"
"""
import sqlite3, json, os, argparse

DB = os.path.expanduser("~/.claude/agentlogs.db")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--limit", type=int, default=0, help="0 = all matching sessions")
    ap.add_argument("--operator-only", action="store_true", default=True,
                    help="is_subagent=0 (default; operator sessions = real supervision signal)")
    ap.add_argument("--include-subagents", dest="operator_only", action="store_false")
    ap.add_argument("--vendor", default=None, help="filter to one vendor (default: all)")
    ap.add_argument("--min-lines", type=int, default=40)
    ap.add_argument("--per-session-cap", type=int, default=24000, help="chars; emb --chunk handles the rest")
    a = ap.parse_args()

    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    where = ["session_uuid IS NOT NULL", "transcript_lines >= ?"]
    params = [a.min_lines]
    if a.operator_only:
        where.append("is_subagent = 0")
    if a.vendor:
        where.append("vendor = ?"); params.append(a.vendor)
    sql = f"SELECT session_pk, session_uuid, vendor, start_ts, transcript_lines FROM sessions WHERE {' AND '.join(where)} ORDER BY start_ts DESC"
    if a.limit:
        sql += f" LIMIT {a.limit}"
    sess = con.execute(sql, params).fetchall()

    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for s in sess:
            rows = con.execute(
                "SELECT e.role, e.kind, e.text FROM events e JOIN runs r ON e.run_id = r.run_id "
                "WHERE r.session_pk = ? AND e.text IS NOT NULL AND e.text != '' "
                # harness-injected re-quotes (labeled at ingest by the claude adapter)
                "AND (e.vendor_kind IS NULL OR e.vendor_kind NOT IN ('compact_summary','meta_injected')) "
                "ORDER BY r.run_id, e.seq",
                (s["session_pk"],)).fetchall()
            parts = []
            for r in rows:
                t = (r["text"] or "").strip()
                if t.startswith("[tool_result]") or t.startswith("[tool_use"):
                    continue
                parts.append(f"{(r['role'] or r['kind'] or '?').upper()}: {t}")
            text = "\n".join(parts)[:a.per_session_cap]
            if len(text) < 200:
                continue
            fh.write(json.dumps({
                "id": s["session_uuid"], "text": text, "source": s["vendor"],
                "date": (s["start_ts"] or "")[:10], "metadata": {"lines": s["transcript_lines"]},
            }, ensure_ascii=False) + "\n")
            n += 1
    print(f"exported {n} sessions (operator_only={a.operator_only}) -> {a.out}")


if __name__ == "__main__":
    main()
