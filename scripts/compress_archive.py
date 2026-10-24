#!/usr/bin/env python3
"""compress_archive.py — APFS-transparent-compress the raw session logs on the archive volume.

The raw jsonl under /Volumes/2TBPNY/agentlogs-archive/{claude,codex,cursor} is the only copy of
sessions older than the live window, and it sits uncompressed (~46 GB, LZFSE gets ~4x). APFS
transparent compression keeps every reader working unchanged (rg, session_roles.py,
operator_prompts_export.py); a .zst rewrite would not.

Never compress in place: afsctool truncates the data fork before it sets the compressed flag, and
a kill in that window leaves an empty file (2026-10-24: one cursor transcript zeroed; rebuilt
byte-exact from the 07-05 DB snapshot). Each file is copied to a sibling temp, the temp is
compressed and its sha256 checked against the original, then os.replace swaps it in. An
interruption at any point leaves the original intact and at most one stray temp, which the next
run deletes.

Callers hold the archive lock (scripts/archive_lock.sh) so the archiver is never copying a file
this rewrites.

  dry-run (default):  uv run python3 scripts/compress_archive.py
  apply:              uv run python3 scripts/compress_archive.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_ROOT = Path("/Volumes/2TBPNY/agentlogs-archive")
VENDORS = ("claude", "codex", "cursor")
TMP_SUFFIX = ".afsc-tmp"
MIN_BYTES = 8192  # below one compression chunk the saving is noise


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _compressed(st: os.stat_result) -> bool:
    return bool(st.st_flags & stat.UF_COMPRESSED)


def compress_one(src: Path) -> int:
    """Return bytes saved on disk (0 when the copy didn't compress). Raises on a hash mismatch."""
    tmp = src.with_name(f".{src.name}{TMP_SUFFIX}")
    st = src.stat()
    try:
        subprocess.run(["cp", "-p", str(src), str(tmp)], check=True)
        subprocess.run(["afsctool", "-c", "-T", "LZFSE", str(tmp)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tst = tmp.stat()
        if not _compressed(tst):
            return 0
        if tst.st_size != st.st_size or _sha(tmp) != _sha(src):
            raise RuntimeError(f"hash mismatch after compression: {src}")
        os.utime(tmp, ns=(st.st_atime_ns, st.st_mtime_ns))
        os.replace(tmp, src)
        return st.st_blocks * 512 - tst.st_blocks * 512
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.root.is_dir():
        print(f"FAIL: archive root not mounted: {args.root}", file=sys.stderr)
        return 1

    todo: list[Path] = []
    stray = 0
    for vendor in VENDORS:
        for path in (args.root / vendor).rglob("*"):
            if path.name.endswith(TMP_SUFFIX):
                stray += 1
                if args.apply:
                    path.unlink(missing_ok=True)
                continue
            if not path.is_file() or path.is_symlink() or path.name == ".DS_Store":
                continue
            st = path.stat()
            if st.st_size >= MIN_BYTES and not _compressed(st):
                todo.append(path)
    raw = sum(p.stat().st_size for p in todo)
    print(f"{len(todo)} uncompressed files, {raw / 1e9:.2f} GB logical; {stray} stray temps"
          f"{' removed' if args.apply and stray else ''}")
    if not args.apply:
        return 0

    saved = done = skipped = 0
    t0 = time.monotonic()
    for i, path in enumerate(todo, 1):
        got = compress_one(path)
        saved += got
        done += got > 0
        skipped += got == 0
        if i % 500 == 0 or i == len(todo):
            print(f"[{time.monotonic() - t0:6.0f}s] {i}/{len(todo)} files, {saved / 1e9:.2f} GB saved", flush=True)
    print(f"compressed {done}, left as-is {skipped}, saved {saved / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
