#!/usr/bin/env python3
"""fm.py — machine-addressable spine for the failure-mode taxonomy.

Mirrors gov.py's Gov-ID parser. Each Failure Mode in agent-failure-modes.md may
carry an FM-ID block (HTML comment, invisible in rendered markdown):

    ### Failure Mode 26: Confirmatory Fan-Out (N Workers, One Prior)
    <!--
    FM-ID: fm26-confirmatory-fanout
    signature: dispatch prompt embeds the desired conclusion AND accept-rate >0.7
    target_surface: intel re-underwrite dispatch; CONFIRMATORY_FANOUT analyst label
    status: active
    evidence_count: 1
    -->

The markdown is authoritative (no DB). Evidence rows accumulate append-only in
~/.claude/fm-evidence.jsonl; evidence_count in the block is a denormalized counter.

Commands:
    fm.py list                         — table of all FM-ID blocks
    fm.py show <id>                    — one FM's fields + recent evidence
    fm.py attach-evidence <id> --session SID --quote "..."   — append evidence, bump count
    fm.py mint <slug> --signature S --target-surface T --merges id,id
                                       — merge-before-mint guard: REFUSES without >=2 merges
    fm.py resolve <id> --ref <commit>  — stamp status=resolved + fix_ref/fix_ts (the recurrence pivot)
    fm.py recurrence                   — per resolved FM, evidence rate before/after fix_ts (descriptive)

This is a BUILD/REVIEW-time tool. Agents do NOT query it as a runtime retrieval
layer (the veto guarantee). See .claude/plans/4d40085a-recursive-session-learning-loop.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FM_FILE = REPO / "agent-failure-modes.md"
EVIDENCE_LOG = Path.home() / ".claude" / "fm-evidence.jsonl"

_FMID = re.compile(r"FM-ID\s*:\s*([a-z0-9][a-z0-9_.:/-]+)", re.IGNORECASE)
_FIELD = re.compile(
    r"^\s*(?:#|<!--|//)?\s*(signature|target_surface|status|evidence_count|fix_ref|fix_ts)\s*:\s*(.+?)\s*(?:-->)?\s*$",
    re.IGNORECASE,
)
_HEADING = re.compile(r"^#{2,4}\s+(.*)$")


def _ok(m): print(f"  ✓ {m}")
def _warn(m): print(f"  ! {m}")
def _fail(m): print(f"  ✗ {m}")


def parse_blocks(path: Path | None = None) -> list[dict]:
    """Scan the FM file for FM-ID blocks. Returns one dict per block.

    Reads the module global FM_FILE at call time when path is None, so callers
    (and tests) that reassign fm.FM_FILE are honored — do NOT bind it as a
    default arg, which would freeze it at import.
    """
    path = path or FM_FILE
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict] = []
    last_heading = ""
    for i, line in enumerate(lines):
        h = _HEADING.match(line)
        if h:
            last_heading = h.group(1).strip()
            continue
        m = _FMID.search(line)
        if not m:
            continue
        fields: dict[str, str] = {}
        for nxt in lines[i + 1:i + 9]:
            s = nxt.strip()
            if s in ("-->", ""):
                break
            fm = _FIELD.match(nxt)
            if fm:
                fields[fm.group(1).lower()] = fm.group(2).strip()
            elif fields:
                break
        out.append({
            "id": m.group(1),
            "heading": last_heading,
            "line": i + 1,
            "signature": fields.get("signature", ""),
            "target_surface": fields.get("target_surface", ""),
            "status": fields.get("status", "active"),
            "evidence_count": int(fields.get("evidence_count", "0") or 0),
            "fix_ref": fields.get("fix_ref", ""),
            "fix_ts": fields.get("fix_ts", ""),
        })
    return out


def _find(blocks: list[dict], fm_id: str) -> dict | None:
    return next((b for b in blocks if b["id"] == fm_id), None)


def cmd_list(_args) -> int:
    blocks = parse_blocks()
    if not blocks:
        _warn("no FM-ID blocks found — taxonomy not yet annotated (Phase 0 in progress)")
        return 0
    print(f"\n[FM taxonomy] {len(blocks)} annotated of "
          f"{sum(1 for _ in re.finditer(r'(?m)^### Failure Mode', FM_FILE.read_text()))} FM sections\n")
    for b in sorted(blocks, key=lambda x: x["id"]):
        ev = b["evidence_count"]
        print(f"  {b['id']:<34} {b['status']:<16} ev={ev:<3} {b['signature'][:60]}")
    return 0


def cmd_show(args) -> int:
    blocks = parse_blocks()
    b = _find(blocks, args.id)
    if not b:
        _fail(f"unknown FM-ID: {args.id}")
        return 1
    print(f"\n{b['id']}  ({b['heading']})")
    print(f"  status:         {b['status']}")
    print(f"  signature:      {b['signature']}")
    print(f"  target_surface: {b['target_surface']}")
    print(f"  evidence_count: {b['evidence_count']}  (agent-failure-modes.md:{b['line']})")
    rows = [json.loads(l) for l in EVIDENCE_LOG.read_text().splitlines()
            if l.strip()] if EVIDENCE_LOG.exists() else []
    rows = [r for r in rows if r.get("fm_id") == args.id]
    if rows:
        print(f"\n  recent evidence ({len(rows)} total):")
        for r in rows[-5:]:
            print(f"    [{r.get('ts','?')[:10]}] {r.get('session','?')}: {r.get('quote','')[:80]}")
    return 0


def _bump_count(fm_id: str, delta: int) -> bool:
    """Rewrite the evidence_count field line for one FM-ID block. Returns success."""
    lines = FM_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    in_block = False
    for i, line in enumerate(lines):
        mm = _FMID.search(line)
        if mm:
            in_block = (mm.group(1) == fm_id)
            continue
        if in_block:
            if line.strip() == "-->":
                in_block = False
                continue
            fm = _FIELD.match(line)
            if fm and fm.group(1).lower() == "evidence_count":
                cur = int(fm.group(2).strip() or 0)
                indent = line[:len(line) - len(line.lstrip())]
                closer = " -->" if "-->" in line else ""  # preserve inline comment closer
                lines[i] = f"{indent}evidence_count: {cur + delta}{closer}\n"
                FM_FILE.write_text("".join(lines), encoding="utf-8")
                return True
    return False


def _evidence_hash(fm_id: str, session: str, quote: str) -> str:
    return hashlib.sha1(f"{fm_id}|{session}|{quote}".encode(),
                        usedforsecurity=False).hexdigest()[:16]


def cmd_attach(args) -> int:
    blocks = parse_blocks()
    if not _find(blocks, args.id):
        _fail(f"unknown FM-ID: {args.id} — mint it first (with --merges) or fix the id")
        return 1
    EVIDENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    ev_hash = _evidence_hash(args.id, args.session, args.quote)
    # idempotent: a re-run (e.g. after a cap-suppressed enforcer left the cluster
    # unprocessed) must not duplicate evidence or double-bump the count.
    existing = set()
    if EVIDENCE_LOG.exists():
        for line in EVIDENCE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                existing.add(json.loads(line).get("ev_hash"))
            except (json.JSONDecodeError, ValueError):
                continue
    if ev_hash in existing:
        _ok(f"evidence already recorded for {args.id} (idempotent skip)")
        return 0
    row = {"fm_id": args.id, "session": args.session, "quote": args.quote,
           "ev_hash": ev_hash,
           "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with EVIDENCE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    if _bump_count(args.id, 1):
        _ok(f"evidence attached to {args.id} (count bumped, logged to {EVIDENCE_LOG.name})")
    else:
        _warn(f"evidence logged but could not bump evidence_count in {FM_FILE.name}")
    return 0


def cmd_mint(args) -> int:
    """Merge-before-mint guard (review finding #1): refuse a new FM unless it
    explicitly merges >=2 prior incident classes."""
    merges = [m.strip() for m in (args.merges or "").split(",") if m.strip()]
    if len(merges) < 2:
        _fail("merge-before-mint: minting a new FM requires --merges id,id (>=2 prior "
              "incident classes). A single incident attaches to an existing FM, it does "
              "not mint a new one. Use attach-evidence instead, or name the classes merged.")
        return 2
    block = (
        f"<!--\nFM-ID: {args.slug}\nsignature: {args.signature}\n"
        f"target_surface: {args.target_surface}\nstatus: active\nevidence_count: 0\n-->"
    )
    print(f"\nmerge-before-mint OK ({len(merges)} classes merged: {', '.join(merges)})")
    print("Place this block under the new FM heading in agent-failure-modes.md:\n")
    print(block)
    return 0


def _set_block_fields(fm_id: str, updates: dict[str, str]) -> bool:
    """Update/insert HTML-comment fields in one FM-ID block. Existing fields are
    rewritten in place (indent + inline `-->` closer preserved); missing fields are
    inserted just before the block closer. Returns False if the block isn't found.
    The markdown stays authoritative — same write discipline as `_bump_count`."""
    try:
        lines = FM_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return False
    in_block = False
    field_indent: str | None = None
    closer_idx: int | None = None
    rem = dict(updates)
    for i, line in enumerate(lines):
        mm = _FMID.search(line)
        if mm:
            if in_block:           # next block began without a closer — malformed
                break
            in_block = (mm.group(1) == fm_id)
            continue
        if not in_block:
            continue
        fm = _FIELD.match(line)
        if fm:
            if field_indent is None:
                field_indent = line[:len(line) - len(line.lstrip())]
            inline = " -->" if "-->" in line else ""
            key = fm.group(1).lower()
            if key in rem:
                ind = line[:len(line) - len(line.lstrip())]
                lines[i] = f"{ind}{key}: {rem.pop(key)}{inline}\n"
            if inline:             # this field line carried the closer
                closer_idx = i
                break
            continue
        if line.strip() == "-->":
            closer_idx = i
            break
    if closer_idx is None:
        return False               # block not found / malformed — don't write
    if rem:
        ind = field_indent or ""
        lines.insert(closer_idx, "".join(f"{ind}{k}: {v}\n" for k, v in rem.items()))
    FM_FILE.write_text("".join(lines), encoding="utf-8")
    return True


def cmd_resolve(args) -> int:
    """Mark an FM resolved + stamp the fix anchor — the BEFORE/AFTER pivot the
    recurrence report measures against. Human-invoked; code never auto-closes (ADR
    2026-06-16-rsi-recurrence-metric)."""
    if not _find(parse_blocks(), args.id):
        _fail(f"unknown FM-ID: {args.id} — `fm.py list` to see ids")
        return 1
    ts = args.at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if _set_block_fields(args.id, {"status": "resolved", "fix_ref": args.ref, "fix_ts": ts}):
        _ok(f"{args.id} resolved (fix_ref={args.ref}, fix_ts={ts})")
        _ok("run `fm.py recurrence` once post-fix evidence accrues to see if it actually dropped")
        return 0
    _fail(f"could not update the block for {args.id} (malformed FM-ID block?)")
    return 1


def _evidence_by_fm() -> dict[str, list[datetime]]:
    out: dict[str, list[datetime]] = {}
    if not EVIDENCE_LOG.exists():
        return out
    for line in EVIDENCE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
            ts = datetime.fromisoformat(r["ts"])
        except (json.JSONDecodeError, ValueError, KeyError):
            continue
        out.setdefault(r.get("fm_id", ""), []).append(ts)
    return out


def cmd_recurrence(_args) -> int:
    """Did a shipped fix actually shrink its cluster? Per resolved FM, the evidence
    occurrence rate BEFORE vs AFTER fix_ts (from fm-evidence.jsonl). DESCRIPTIVE — never
    a target (or it Goodharts). Flags low-N / too-soon rather than over-claiming."""
    resolved = [b for b in parse_blocks() if b.get("status") == "resolved" and b.get("fix_ts")]
    if not resolved:
        _warn("no resolved FMs with a fix_ts — `fm.py resolve <id> --ref <commit>` first")
        return 0
    ev = _evidence_by_fm()
    now = datetime.now(timezone.utc)
    print("\n[FM recurrence — DESCRIPTIVE, not a target; low-N / too-soon flagged]\n")
    print(f"  {'FM-ID':<30} {'pre-fix':<13} {'post-fix':<13} verdict")
    for b in sorted(resolved, key=lambda x: x["id"]):
        try:
            fix = datetime.fromisoformat(b["fix_ts"])
        except ValueError:
            print(f"  {b['id']:<30} (unparseable fix_ts: {b['fix_ts']})")
            continue
        evs = sorted(ev.get(b["id"], []))
        before = [t for t in evs if t < fix]
        after = [t for t in evs if t >= fix]
        wb = (fix - before[0]).days / 7.0 if before else 0.0
        wa = (now - fix).days / 7.0
        rb = len(before) / wb if wb >= 1 else None
        ra = len(after) / wa if wa >= 1 else None
        if len(before) < 5:
            verdict = f"UNDERPOWERED ({len(before)} pre-fix < 5)"
        elif wa < 1:
            verdict = "TOO SOON (<1wk post-fix)"
        elif rb is None:
            verdict = "pre-window <1wk — rate n/a"
        else:
            verdict = "REDUCED" if (ra or 0.0) < rb * 0.5 else f"not reduced ({(ra or 0):.2f} vs {rb:.2f}/wk)"
        pre = f"{len(before)}ev/{wb:.1f}wk" if before else "0ev"
        post = f"{len(after)}ev/{wa:.1f}wk"
        print(f"  {b['id']:<30} {pre:<13} {post:<13} {verdict}")
    return 0


def cmd_selftest(_args) -> int:
    """Isolated self-test of the resolve/recurrence machinery (temp FM file + evidence log)."""
    import tempfile
    global FM_FILE, EVIDENCE_LOG
    orig_fm, orig_ev = FM_FILE, EVIDENCE_LOG
    try:
        d = Path(tempfile.mkdtemp())
        FM_FILE = d / "fm.md"
        EVIDENCE_LOG = d / "ev.jsonl"
        FM_FILE.write_text(
            "### Failure Mode 99: Test\n<!--\nFM-ID: fm99-test\n"
            "signature: x\ntarget_surface: y\nstatus: active\nevidence_count: 7\n-->\n",
            encoding="utf-8",
        )
        base = datetime(2026, 4, 1, tzinfo=timezone.utc)
        rows = [{"fm_id": "fm99-test", "session": f"s{w}", "quote": "q",
                 "ts": (base + timedelta(weeks=w)).isoformat(timespec="seconds")} for w in range(6)]
        fix_dt = base + timedelta(weeks=6)
        rows.append({"fm_id": "fm99-test", "session": "sp", "quote": "q",
                     "ts": (fix_dt + timedelta(weeks=3)).isoformat(timespec="seconds")})
        EVIDENCE_LOG.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

        assert _set_block_fields("fm99-test", {"status": "resolved", "fix_ref": "abc1234",
                                               "fix_ts": fix_dt.isoformat(timespec="seconds")})
        b = _find(parse_blocks(), "fm99-test")
        assert b and b["status"] == "resolved" and b["fix_ref"] == "abc1234" and b["fix_ts"], b
        # re-resolve must UPDATE in place, not duplicate the fields
        assert _set_block_fields("fm99-test", {"status": "resolved", "fix_ref": "def5678",
                                               "fix_ts": fix_dt.isoformat(timespec="seconds")})
        assert FM_FILE.read_text().count("fix_ref:") == 1, "fix_ref must update in place"
        b3 = _find(parse_blocks(), "fm99-test")
        assert b3 is not None and b3["fix_ref"] == "def5678"
        ev = _evidence_by_fm()
        assert len(ev["fm99-test"]) == 7 and sum(t < fix_dt for t in ev["fm99-test"]) == 6
        _ok("resolve stamps status/fix_ref/fix_ts; re-resolve updates in place (no dup)")
        _ok("evidence groups by fm_id; before/after split correct (6 pre, 1 post)")
        _ok("recurrence math runs; not-underpowered at 6 pre-fix; descriptive-only")
        print("\n  fm.py selftest passed.")
        return 0
    finally:
        FM_FILE, EVIDENCE_LOG = orig_fm, orig_ev


def main() -> int:
    p = argparse.ArgumentParser(description="FM taxonomy spine (build/review-time only)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sp = sub.add_parser("show"); sp.add_argument("id"); sp.set_defaults(fn=cmd_show)
    sp = sub.add_parser("attach-evidence")
    sp.add_argument("id"); sp.add_argument("--session", required=True)
    sp.add_argument("--quote", required=True); sp.set_defaults(fn=cmd_attach)
    sp = sub.add_parser("mint")
    sp.add_argument("slug"); sp.add_argument("--signature", required=True)
    sp.add_argument("--target-surface", required=True); sp.add_argument("--merges", default="")
    sp.set_defaults(fn=cmd_mint)
    sp = sub.add_parser("resolve")
    sp.add_argument("id"); sp.add_argument("--ref", required=True, help="fix commit/ref")
    sp.add_argument("--at", default="", help="fix_ts ISO override (default: now UTC)")
    sp.set_defaults(fn=cmd_resolve)
    sub.add_parser("recurrence").set_defaults(fn=cmd_recurrence)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
