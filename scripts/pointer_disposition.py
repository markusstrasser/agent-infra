#!/usr/bin/env python3
"""pointer_disposition.py — external URL/pointer ledger for operator-free triage.

Operator-pasted links (GitHub cookbooks, arxiv, HF, blog posts) should answer with
one of: known · in_queue · doesnt_apply · tried · adopted — never a fresh cold eval
as if the loop had never seen the pointer.

Miss class (RSI-hindsight rsi-arc-agi-d8da85ee-*, 2026-07-07 + 2026-07-18):
operator brings a source → agent evaluates reactively → operator asks why the loop
did not already know. This ledger + lookup is the CONVERT of that flag.

Usage:
  just pointer-disposition lookup <url>
  just pointer-disposition record <url> --disposition doesnt_apply --reason "..."
  just pointer-disposition list [--project arc-agi]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "artifacts" / "pointer-dispositions"
LEDGER = OUT_DIR / "ledger.jsonl"

DISPOSITIONS = (
    "known",          # we know — cite reason/threads
    "in_queue",       # already queued for evaluate/adopt
    "doesnt_apply",   # thanks but doesn't apply
    "tried",          # tried already — negative or inconclusive logged
    "adopted",        # already done / wired in
    "pending",        # seen, disposition not yet written (transient)
)

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


def normalize_url(url: str) -> str:
    """Collapse noise so blob/tree/raw and trailing junk share one key."""
    raw = url.strip().rstrip(").,;\"'")
    p = urlparse(raw)
    scheme = (p.scheme or "https").lower()
    netloc = (p.netloc or "").lower()
    path = p.path or ""
    # github.com/org/repo/{blob,tree,raw}/REF/rest → org/repo/rest
    m = re.match(
        r"^/([^/]+)/([^/]+)/(?:blob|tree|raw)/[^/]+/(.*)$",
        path,
    )
    if netloc in ("github.com", "www.github.com") and m:
        path = f"/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    # raw.githubusercontent.com/org/repo/REF/rest → github.com/org/repo/rest
    m2 = re.match(r"^/([^/]+)/([^/]+)/[^/]+/(.*)$", path)
    if netloc == "raw.githubusercontent.com" and m2:
        netloc = "github.com"
        path = f"/{m2.group(1)}/{m2.group(2)}/{m2.group(3)}"
    path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def url_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()[:12]


def extract_urls(text: str) -> list[str]:
    return [normalize_url(u) for u in URL_RE.findall(text or "")]


def _load() -> list[dict]:
    if not LEDGER.is_file():
        return []
    rows: list[dict] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def lookup(url: str) -> dict | None:
    key = normalize_url(url)
    for row in reversed(_load()):
        if normalize_url(row.get("url", "")) == key:
            return row
    return None


def lookup_many(urls: list[str]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for u in urls:
        key = normalize_url(u)
        if key in seen:
            continue
        seen.add(key)
        row = lookup(key)
        if row:
            out.append(row)
        else:
            out.append({
                "id": url_id(key),
                "url": key,
                "disposition": "pending",
                "reason": "not in ledger — evaluate AND record before answering",
            })
    return out


def record(
    url: str,
    disposition: str,
    reason: str,
    *,
    project: str = "",
    threads: list[str] | None = None,
    source: str = "manual",
) -> dict:
    if disposition not in DISPOSITIONS:
        raise SystemExit(f"disposition must be one of {DISPOSITIONS}")
    if disposition == "pending":
        raise SystemExit("do not record pending — that is the miss state")
    reason = (reason or "").strip()
    if len(reason) < 8:
        raise SystemExit("reason required (≥8 chars) — disposition without reason is noise")
    row = {
        "id": url_id(url),
        "url": normalize_url(url),
        "disposition": disposition,
        "reason": reason,
        "project": project,
        "threads": threads or [],
        "source": source,
        "disposed_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def format_triage(rows: list[dict]) -> str:
    """Operator-free reply vocabulary — one line per pointer."""
    lines = ["POINTER-DISPOSITION (external URL triage — answer from this, don't re-derive):"]
    for r in rows:
        disp = r.get("disposition", "?")
        url = r.get("url", "")
        reason = r.get("reason", "")
        threads = r.get("threads") or []
        t = f" threads={threads}" if threads else ""
        lines.append(f"  [{disp}] {url} — {reason}{t}")
    lines.append(
        "Reply vocab: known · in_queue · doesnt_apply · tried · adopted "
        "(or record a new row if pending)."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_lookup = sub.add_parser("lookup", help="Lookup one URL or extract URLs from --text")
    p_lookup.add_argument("url", nargs="?", default="")
    p_lookup.add_argument("--text", default="", help="Free text; extract URLs")
    p_lookup.add_argument("--json", action="store_true")

    p_rec = sub.add_parser("record", help="Append a disposition row")
    p_rec.add_argument("url")
    p_rec.add_argument("--disposition", required=True, choices=[d for d in DISPOSITIONS if d != "pending"])
    p_rec.add_argument("--reason", required=True)
    p_rec.add_argument("--project", default="")
    p_rec.add_argument("--thread", action="append", default=[])
    p_rec.add_argument("--source", default="manual")

    p_list = sub.add_parser("list", help="List ledger rows")
    p_list.add_argument("--project", default="")
    p_list.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "lookup":
        urls = [args.url] if args.url else extract_urls(args.text)
        if not urls:
            print("no URL", file=sys.stderr)
            return 1
        rows = lookup_many(urls)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(format_triage(rows))
        return 0

    if args.cmd == "record":
        row = record(
            args.url,
            args.disposition,
            args.reason,
            project=args.project,
            threads=args.thread,
            source=args.source,
        )
        print(json.dumps(row, indent=2))
        return 0

    if args.cmd == "list":
        rows = _load()
        if args.project:
            rows = [r for r in rows if r.get("project") == args.project]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                print(f"{r.get('disposition'):12} {r.get('url')} — {r.get('reason', '')[:80]}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
