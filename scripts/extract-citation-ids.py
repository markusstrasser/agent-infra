#!/usr/bin/env python3
"""
Extract citation identifiers (DOI / PMID / PMCID / NCT) from research files.

Batch-scans markdown files and reports unique citation IDs found.
Useful for auditing "does this claim have a resolvable ID?"

Usage:
    uv run python3 scripts/extract-citation-ids.py
    uv run python3 scripts/extract-citation-ids.py --target ~/Projects/phenome/docs/research
    uv run python3 scripts/extract-citation-ids.py --target ~/Projects/genomics/docs --output-md artifacts/citations.md

Source: selve/scripts/extract_citation_ids.py
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from config import PROJECT_ROOTS, RESEARCH_DIRS, PROSE_EXTENSIONS
from common import con


# ── Regex patterns ───────────────────────────────────────────

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
PMID_RE = re.compile(r"\bPMID\s*:?\s*`?(\d{6,9})\b`?", re.IGNORECASE)
PMCID_PREFIX_RE = re.compile(r"\bPMC\d{6,9}\b", re.IGNORECASE)
PMC_NUMERIC_RE = re.compile(r"\b(?:PMCID|PMC)\s*:?\s*`?(\d{6,9})\b`?", re.IGNORECASE)
NCT_RE = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)


# ── File discovery ───────────────────────────────────────────

def find_research_files(root: Path) -> list[Path]:
    """Find prose files in research directories under a project root."""
    files = []
    for dir_name in RESEARCH_DIRS:
        search_dir = root / dir_name
        if search_dir.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(search_dir.rglob(f"*{ext}"))
    return sorted(set(files))


def collect_files(target: Path | None) -> list[Path]:
    """Collect files to scan based on CLI args."""
    if target:
        if target.is_file():
            return [target]
        return sorted(p for p in target.rglob("*.md") if p.is_file())

    # Default: scan all project roots
    files = []
    for name, root in PROJECT_ROOTS.items():
        if root.exists():
            files.extend(find_research_files(root))
    return sorted(set(files))


# ── ID extraction ────────────────────────────────────────────

def find_ids(text: str) -> dict[str, set[str]]:
    dois = set(DOI_RE.findall(text))
    pmids = set(m.group(1) for m in PMID_RE.finditer(text))
    pmcids = set(m.group(0).upper() for m in PMCID_PREFIX_RE.finditer(text))
    pmcids |= set(f"PMC{m.group(1)}" for m in PMC_NUMERIC_RE.finditer(text))
    ncts = set(m.group(0) for m in NCT_RE.finditer(text))
    return {"DOI": dois, "PMID": pmids, "PMCID": pmcids, "NCT": ncts}


# ── Main ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract citation identifiers (DOI, PMID, PMCID, NCT) from research files"
    )
    parser.add_argument("--target", type=Path, help="Directory or file to scan (overrides default cross-project scan)")
    parser.add_argument("--output-md", default=None, help="Write a Markdown report to this path")
    args = parser.parse_args()

    files = collect_files(args.target)
    if not files:
        con.fail("No files found to scan")
        return 1

    if args.output_md:
        out_path = Path(args.output_md)
        files = [f for f in files if f != out_path]

    # id_type -> id_value -> list[occurrence]
    occurrences: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for fp in files:
        try:
            lines = fp.read_text(errors="replace").splitlines()
        except Exception as e:
            con.warn(f"Failed to read {fp}: {e}")
            continue

        for i, line in enumerate(lines, start=1):
            ids = find_ids(line)
            for id_type, values in ids.items():
                for value in sorted(values):
                    occurrences[id_type][value].append(f"{fp}:{i}")

    uniques = {k: len(d) for k, d in occurrences.items()}
    total_unique = sum(uniques.values())

    con.header("Citation ID Extraction")
    con.kv("Files scanned", str(len(files)))
    con.kv("Unique IDs", str(total_unique))
    for k in ("DOI", "PMID", "PMCID", "NCT"):
        if uniques.get(k, 0) > 0:
            con.kv(f"  {k}", str(uniques[k]))

    if args.output_md:
        out_path = Path(args.output_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows: list[tuple[str, str, str, str]] = []
        for id_type in ("DOI", "PMID", "PMCID", "NCT"):
            for value in sorted(occurrences.get(id_type, {}).keys()):
                locs = occurrences[id_type][value]
                rows.append((
                    id_type,
                    value,
                    str(len(locs)),
                    ", ".join(locs[:6]) + (" ..." if len(locs) > 6 else ""),
                ))

        md = []
        md.append("# Citation ID Extraction Report\n")
        md.append(f"- Files scanned: {len(files)}")
        md.append(
            "- Unique IDs: "
            + ", ".join(f"{k}={uniques.get(k,0)}" for k in ("DOI", "PMID", "PMCID", "NCT"))
        )
        md.append("")
        md.append("| Type | ID | Occurrences | First locations |")
        md.append("|---|---:|---:|---|")
        for id_type, value, occ_count, first_locs in rows:
            md.append(f"| {id_type} | `{value}` | {occ_count} | {first_locs} |")
        md.append("")

        out_path.write_text("\n".join(md))
        con.ok(f"Wrote report: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
