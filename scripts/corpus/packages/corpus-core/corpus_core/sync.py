"""Best-effort bootstrap from upstream — NOT a backup mechanism.

`corpus sync --from manifest.json` reads a manifest of expected papers and
attempts to fetch any missing ones via DOI/PMID resolution. Upstream sources
go missing (paywalls, 404, content drift) — durable backup is filesystem-level
(Time Machine, rsync). Documented in SCHEMA.md.

Manifest format:
    {
      "papers": [
        {"paper_id": "doi_10_xxxx_yyy", "doi": "10.xxxx/yyy", "pdf_sha256": "..."},
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import store as ps


def sync_from_manifest(manifest_path: Path, *, dry_run: bool = False) -> dict:
    manifest = json.loads(Path(manifest_path).read_text())
    entries = manifest.get("papers", [])
    missing: list[dict] = []
    present: list[str] = []
    for entry in entries:
        paper_id = entry.get("paper_id")
        if paper_id and ps.exists(paper_id):
            present.append(paper_id)
        else:
            missing.append(entry)

    print(f"  ▸ manifest entries: {len(entries)}")
    print(f"  ▸ present:          {len(present)}")
    print(f"  ▸ missing:          {len(missing)}")

    if dry_run or not missing:
        return {"present": present, "missing_count": len(missing)}

    # Real implementation would invoke research-mcp's download_paper here.
    print("  ! sync requires `research-mcp` integration; not implemented in Phase 1.")
    print("  ! This is best-effort bootstrap, not backup. Use Time Machine / rsync.")
    return {"present": present, "missing": missing, "fetched": 0}


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("sync", help="Bootstrap missing papers from upstream (best-effort)")
    p.add_argument("--from", dest="manifest", required=True, help="Path to manifest.json")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_sync)


def _cmd_sync(args) -> int:
    sync_from_manifest(Path(args.manifest), dry_run=args.dry_run)
    return 0
