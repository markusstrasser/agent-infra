#!/usr/bin/env python3
"""archive_raw_logs.py — relocate OLD raw agent session logs to external storage.

The agentlogs indexer cost is O(all raw files): every 2h it globs + stats the
ENTIRE session corpus (~9k files across claude/codex/cursor) to find what changed
— even though unchanged files are cheap-skipped from re-reading. As the corpus
grows the enumeration alone blows the --max-run-seconds=600 budget (exit 75,
'HARD run deadline exceeded'), and the raw logs (~8 GB) crowd a tight main disk.

The DB (agentlogs.db) is DERIVED — it already holds every indexed session, so
moving an already-indexed raw file does NOT lose queryable data, and the indexer
re-globs discover_sources() each run so a moved file is simply not re-discovered
(no error). This relocates raw files older than --keep-days to the external SSD,
preserving structure + mtime, REVERSIBLY (--restore reads the manifest).

This is NOT `agentlogs prune` — that deletes DB rows (searchable history). This
touches only raw files on disk and keeps the DB fully intact.

  dry-run (default):  uv run python3 scripts/archive_raw_logs.py
  apply:              uv run python3 scripts/archive_raw_logs.py --apply
  one vendor:         uv run python3 scripts/archive_raw_logs.py --vendor claude --apply
  restore:            uv run python3 scripts/archive_raw_logs.py --restore --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

HOME = Path.home()
DEFAULT_DEST = Path("/Volumes/2TBPNY/agentlogs-archive")
DEFAULT_KEEP_DAYS = 14
MANIFEST_NAME = "archive-manifest.jsonl"

# vendor -> (base dir, glob the agentlogs adapter uses to discover sources).
# Matching the adapter glob EXACTLY means we archive precisely the indexer's
# enumeration set — nothing it doesn't scan, so the per-run cost actually drops.
VENDORS: dict[str, tuple[Path, str]] = {
    "claude": (HOME / ".claude" / "projects", "**/*.jsonl"),
    "codex":  (HOME / ".codex" / "sessions", "**/*.jsonl"),
    "cursor": (HOME / ".cursor" / "projects", "*/agent-transcripts/*/*.jsonl"),
}


def _ok(m): print(f"  ✓ {m}")
def _fail(m): print(f"  ✗ {m}")
def _header(s): print(f"\n[{s}]")


def _human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.1f}{unit}"
        f /= 1024
    return f"{f:.1f}TB"


def _preflight(dest: Path, need_bytes: int) -> bool:
    """disk-preflight rule: dest mounted + free >= 1.5x payload, else abort."""
    mount = dest
    while not mount.exists() and mount != mount.parent:
        mount = mount.parent
    if not str(mount).startswith("/Volumes/") and dest.anchor == "/Volumes":
        _fail(f"external volume not mounted: {dest} (is the SSD plugged in?)")
        return False
    try:
        usage = shutil.disk_usage(mount)
    except OSError as e:
        _fail(f"cannot stat dest volume {mount}: {e}")
        return False
    need = int(need_bytes * 1.5)
    if usage.free < need:
        _fail(f"dest={dest} free={_human(usage.free)} need={_human(need)} (1.5x payload) — abort")
        return False
    _ok(f"preflight: dest={dest} free={_human(usage.free)} need={_human(need)}")
    return True


def _candidates(vendor: str, keep_days: float) -> list[Path]:
    base, pattern = VENDORS[vendor]
    if not base.is_dir():
        return []
    cutoff = time.time() - keep_days * 86400
    out = []
    for p in base.glob(pattern):
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                out.append(p)
        except OSError:
            continue
    return out


def _archive_vendor(vendor: str, keep_days: float, dest: Path, apply: bool,
                    manifest_fh) -> tuple[int, int]:
    base, _ = VENDORS[vendor]
    files = _candidates(vendor, keep_days)
    moved, bytes_moved = 0, 0
    for src in files:
        rel = src.relative_to(base)
        dst = dest / vendor / rel
        try:
            size = src.stat().st_size
            mtime = src.stat().st_mtime
        except OSError:
            continue
        if not apply:
            moved += 1
            bytes_moved += size
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Idempotent: if an equal-size copy already exists, treat as archived.
        if not (dst.exists() and dst.stat().st_size == size):
            shutil.copy2(src, dst)  # copy2 preserves mtime — restore stays indexer-correct
            if dst.stat().st_size != size:
                _fail(f"size mismatch after copy, NOT removing src: {src}")
                dst.unlink(missing_ok=True)
                continue
        src.unlink()
        manifest_fh.write(json.dumps({
            "ts": time.time(), "vendor": vendor,
            "src": str(src), "dst": str(dst), "size": size, "mtime": mtime,
        }) + "\n")
        manifest_fh.flush()
        moved += 1
        bytes_moved += size
    return moved, bytes_moved


def _restore(dest: Path, apply: bool, vendor_filter: str | None) -> int:
    manifest = dest / MANIFEST_NAME
    if not manifest.exists():
        _fail(f"no manifest at {manifest} — nothing to restore")
        return 1
    restored = 0
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if vendor_filter and rec["vendor"] != vendor_filter:
            continue
        dst, src = Path(rec["dst"]), Path(rec["src"])
        if not dst.exists():
            continue
        if src.exists():  # already back (or a newer session reused the path) — don't clobber
            continue
        if apply:
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, src)
        restored += 1
    print(f"\n{'restored' if apply else 'would restore'} {restored} files from {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep-days", type=float, default=DEFAULT_KEEP_DAYS,
                    help=f"keep raw files newer than N days on main disk (default {DEFAULT_KEEP_DAYS})")
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST, help=f"archive root (default {DEFAULT_DEST})")
    ap.add_argument("--vendor", choices=[*VENDORS, "all"], default="all")
    ap.add_argument("--apply", action="store_true", help="actually move (default: dry-run)")
    ap.add_argument("--restore", action="store_true", help="copy archived files back from the manifest")
    args = ap.parse_args()

    vendors = list(VENDORS) if args.vendor == "all" else [args.vendor]

    if args.restore:
        return _restore(args.dest, args.apply, None if args.vendor == "all" else args.vendor)

    _header(f"{'ARCHIVE' if args.apply else 'DRY-RUN'} raw logs older than {args.keep_days}d → {args.dest}")
    plan = {v: _candidates(v, args.keep_days) for v in vendors}
    payload = sum(sum(p.stat().st_size for p in fs if p.exists()) for fs in plan.values())
    for v, fs in plan.items():
        vb = sum(p.stat().st_size for p in fs if p.exists())
        print(f"  {v:8} {len(fs):>5} files  {_human(vb)}")
    print(f"  {'TOTAL':8} {sum(len(fs) for fs in plan.values()):>5} files  {_human(payload)}")
    if payload == 0:
        _ok("nothing older than the threshold — noop")
        return 0

    if not args.apply:
        print("\n(dry-run — re-run with --apply to move)")
        return 0

    if not _preflight(args.dest, payload):
        return 1
    args.dest.mkdir(parents=True, exist_ok=True)
    total_files, total_bytes = 0, 0
    with (args.dest / MANIFEST_NAME).open("a") as mf:
        for v in vendors:
            n, b = _archive_vendor(v, args.keep_days, args.dest, True, mf)
            _ok(f"{v}: archived {n} files ({_human(b)})")
            total_files += n
            total_bytes += b
    _ok(f"done: {total_files} files, {_human(total_bytes)} reclaimed → {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
