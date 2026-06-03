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

This is a BUILD/REVIEW-time tool. Agents do NOT query it as a runtime retrieval
layer (the veto guarantee). See .claude/plans/4d40085a-recursive-session-learning-loop.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FM_FILE = REPO / "agent-failure-modes.md"
EVIDENCE_LOG = Path.home() / ".claude" / "fm-evidence.jsonl"

_FMID = re.compile(r"FM-ID\s*:\s*([a-z0-9][a-z0-9_.:/-]+)", re.IGNORECASE)
_FIELD = re.compile(
    r"^\s*(?:#|<!--|//)?\s*(signature|target_surface|status|evidence_count)\s*:\s*(.+?)\s*(?:-->)?\s*$",
    re.IGNORECASE,
)
_HEADING = re.compile(r"^#{2,4}\s+(.*)$")


def _ok(m): print(f"  ✓ {m}")
def _warn(m): print(f"  ! {m}")
def _fail(m): print(f"  ✗ {m}")


def parse_blocks(path: Path = FM_FILE) -> list[dict]:
    """Scan the FM file for FM-ID blocks. Returns one dict per block."""
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
                lines[i] = f"{indent}evidence_count: {cur + delta}\n"
                FM_FILE.write_text("".join(lines), encoding="utf-8")
                return True
    return False


def cmd_attach(args) -> int:
    blocks = parse_blocks()
    if not _find(blocks, args.id):
        _fail(f"unknown FM-ID: {args.id} — mint it first (with --merges) or fix the id")
        return 1
    EVIDENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "fm_id": args.id,
        "session": args.session,
        "quote": args.quote,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
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
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
