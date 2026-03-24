#!/usr/bin/env python3
"""Find files affected by corrections across projects.

Three layered strategies:
1. Backward cross-ref tracing — inverted index from knowledge-index cross_refs
2. Forward term matching — rg search for stale values
3. Correction scan — find unresolved @correction entries

Report-only: never auto-fixes anything.

Usage:
  propagate-correction.py --from FILE
  propagate-correction.py --terms "99.7th" "GLIMPSE2"
  propagate-correction.py --scan
  propagate-correction.py --scan --projects selve genomics --json
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common.paths import CLAUDE_DIR
from config import KNOWLEDGE_ELIGIBLE_PATTERNS, PROJECT_ROOTS

# Knowledge-index block regex
KI_BLOCK_RE = re.compile(
    r"<!-- knowledge-index\n(.*?)\nend-knowledge-index -->", re.DOTALL
)

# Archive directory names
ARCHIVE_DIRS = {"archive", "_archive"}
ARCHIVE_PATH_SEGMENTS = {"archive/", "_archive/", "docs/audit/"}

# Correction blockquote in prose (not in knowledge-index)
CORRECTION_BLOCKQUOTE_RE = re.compile(
    r"^>\s*\*\*(?:CORRECTION|RETRACTION|REVISED|UPDATE)\b",
    re.MULTILINE,
)

# Strikethrough pattern
STRIKETHROUGH_RE = re.compile(r"~~[^~]+~~")


def is_archive_path(path: Path) -> bool:
    """Check if path is in an archive directory."""
    path_str = str(path)
    return any(seg in path_str for seg in ARCHIVE_PATH_SEGMENTS)


def eligible_files(projects: list[str] | None = None) -> list[tuple[str, Path]]:
    """Yield (project_name, file_path) for all knowledge-eligible files."""
    targets = projects or list(KNOWLEDGE_ELIGIBLE_PATTERNS.keys())
    results = []
    for proj in targets:
        root = PROJECT_ROOTS.get(proj)
        patterns = KNOWLEDGE_ELIGIBLE_PATTERNS.get(proj)
        if not root or not patterns or not root.exists():
            continue
        for pattern in patterns:
            for p in root.glob(pattern):
                if p.is_file():
                    results.append((proj, p))
    return results


def parse_ki_block(text: str) -> dict:
    """Parse a knowledge-index block into structured data."""
    m = KI_BLOCK_RE.search(text)
    if not m:
        return {}
    block_text = m.group(1)
    data = {"raw": block_text, "cross_refs": [], "corrections": []}
    for line in block_text.split("\n"):
        line = line.strip()
        if line.startswith("cross_refs:"):
            refs_str = line[len("cross_refs:"):].strip()
            data["cross_refs"] = [r.strip() for r in refs_str.split(",") if r.strip()]
        elif line.startswith("@correction"):
            data["corrections"].append(line)
    return data


def build_inverted_index(
    files: list[tuple[str, Path]],
) -> dict[str, list[tuple[str, Path]]]:
    """Build {target_ref: [(project, source_file)]} from cross_refs."""
    index: dict[str, list[tuple[str, Path]]] = {}
    for proj, fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        ki = parse_ki_block(text)
        for ref in ki.get("cross_refs", []):
            # Filter self-referential refs
            rel = str(fpath.relative_to(PROJECT_ROOTS[proj]))
            if ref == rel:
                continue
            index.setdefault(ref, []).append((proj, fpath))
    return index


def trace_from_file(
    source_file: Path,
    files: list[tuple[str, Path]],
) -> list[dict]:
    """Strategy 1: backward cross-ref tracing from a corrected file."""
    # Determine the relative path of source within its project
    source_rel = None
    for _, root in PROJECT_ROOTS.items():
        try:
            source_rel = str(source_file.relative_to(root))
            break
        except ValueError:
            continue

    if not source_rel:
        return []

    inv = build_inverted_index(files)
    results = []
    for ref_key, referrers in inv.items():
        if ref_key == source_rel:
            for proj, fpath in referrers:
                results.append(_classify_file(proj, fpath, f"cross-refs {source_rel}"))
    return results


def search_terms(
    terms: list[str],
    projects: list[str] | None = None,
) -> list[dict]:
    """Strategy 2: forward term matching via rg."""
    targets = projects or list(PROJECT_ROOTS.keys())
    results = []
    seen: set[str] = set()

    for term in terms:
        for proj in targets:
            root = PROJECT_ROOTS.get(proj)
            if not root or not root.exists():
                continue
            try:
                proc = subprocess.run(
                    [
                        "rg", "-l", "--no-messages",
                        "--glob", "*.md",
                        "--glob", "!.claude/",
                        term,
                        str(root),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

            for line in proc.stdout.strip().split("\n"):
                if not line:
                    continue
                fpath = Path(line)
                key = str(fpath)
                if key in seen:
                    continue
                seen.add(key)

                # Skip knowledge-index blocks — check if term only appears there
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                text_without_ki = KI_BLOCK_RE.sub("", text)
                if term.replace("\\", "") not in text_without_ki:
                    continue

                results.append(
                    _classify_file(proj, fpath, f"contains '{term}'")
                )
    return results


def scan_corrections(
    files: list[tuple[str, Path]],
    all_files: list[tuple[str, Path]],
) -> list[dict]:
    """Strategy 3: find files with @correction, trace their references."""
    results = []
    seen: set[str] = set()

    for proj, fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        ki = parse_ki_block(text)
        if not ki.get("corrections"):
            continue

        # The corrected file itself
        key = str(fpath)
        if key not in seen:
            seen.add(key)
            results.append(
                _classify_file(proj, fpath, "has @correction")
            )

        # Trace references to this file
        traced = trace_from_file(fpath, all_files)
        for r in traced:
            if r["file"] not in seen:
                seen.add(r["file"])
                r["why"] = f"cross-refs corrected file ({Path(fpath).name})"
                results.append(r)

    return results


def _classify_file(
    project: str,
    fpath: Path,
    why: str,
) -> dict:
    """Classify a flagged file with status."""
    is_archive = is_archive_path(fpath)
    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""

    has_correction_blockquote = bool(CORRECTION_BLOCKQUOTE_RE.search(text))
    has_strikethrough = bool(STRIKETHROUGH_RE.search(text))

    if is_archive:
        status = "ARCHIVE"
    elif has_correction_blockquote:
        status = "OK"
    elif has_strikethrough:
        status = "CORRECTED INLINE"
    else:
        status = "NEEDS REVIEW"

    return {
        "file": str(fpath),
        "project": project,
        "why": why,
        "has_correction": has_correction_blockquote,
        "status": status,
        "is_archive": is_archive,
    }


def find_affected_files(
    source_file: str | Path | None = None,
    terms: list[str] | None = None,
    scan: bool = False,
    projects: list[str] | None = None,
    include_archives: bool = False,
) -> list[dict]:
    """Main entry point. Returns list of affected file dicts.

    Importable by other scripts (e.g., genomics staleness_guard).
    """
    files = eligible_files(projects)
    all_files = eligible_files()  # for cross-project tracing
    results: list[dict] = []

    if source_file:
        source_path = Path(source_file).resolve()
        results.extend(trace_from_file(source_path, all_files))

    if terms:
        results.extend(search_terms(terms, projects))

    if scan:
        results.extend(scan_corrections(files, all_files))

    # Deduplicate by file path, keeping first occurrence
    seen: set[str] = set()
    deduped = []
    for r in results:
        if r["file"] not in seen:
            seen.add(r["file"])
            # Archives always included in output but with ARCHIVE status
            # When include_archives=False, mark them so callers can filter
            if not include_archives and r.get("is_archive"):
                r["status"] = "ARCHIVE"
            deduped.append(r)
    return deduped


def format_table(results: list[dict]) -> str:
    """Format results as markdown table."""
    if not results:
        return "No affected files found."

    lines = [
        "| File | Project | Why Flagged | Has Correction? | Status |",
        "|------|---------|-------------|-----------------|--------|",
    ]
    needs_review = 0
    for r in results:
        # Shorten file path for display
        fpath = r["file"]
        for _, root in PROJECT_ROOTS.items():
            root_str = str(root)
            if fpath.startswith(root_str):
                fpath = fpath[len(root_str) + 1:]
                break
        corr = "yes" if r["has_correction"] else "no"
        lines.append(f"| {fpath} | {r['project']} | {r['why']} | {corr} | {r['status']} |")
        if r["status"] == "NEEDS REVIEW":
            needs_review += 1

    lines.append("")
    total = len(results)
    archive_count = sum(1 for r in results if r["is_archive"])
    lines.append(
        f"**{total} files found** ({needs_review} need review, "
        f"{archive_count} in archive)"
    )
    return "\n".join(lines)


def log_invocation(args: argparse.Namespace) -> None:
    """Log invocation to hook-triggers.jsonl."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "propagate_correction",
            "from": args.source_file,
            "terms": args.terms,
            "scan": args.scan,
            "projects": args.projects,
        }
        log_path = CLAUDE_DIR / "hook-triggers.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Find files affected by corrections across projects."
    )
    parser.add_argument(
        "--from", dest="source_file", help="Trace from a corrected file"
    )
    parser.add_argument(
        "--terms", nargs="+", help="Search for specific stale values"
    )
    parser.add_argument(
        "--scan", action="store_true", help="Find all unresolved corrections"
    )
    parser.add_argument(
        "--projects", nargs="+", help="Filter to specific projects (default: all)"
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Machine-readable JSON output"
    )
    parser.add_argument(
        "--include-archives", action="store_true",
        help="Include archive dirs (default: exclude from NEEDS REVIEW)"
    )
    args = parser.parse_args()

    if not any([args.source_file, args.terms, args.scan]):
        parser.error("At least one of --from, --terms, or --scan is required")

    log_invocation(args)

    results = find_affected_files(
        source_file=args.source_file,
        terms=args.terms,
        scan=args.scan,
        projects=args.projects,
        include_archives=args.include_archives,
    )

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        print(format_table(results))


if __name__ == "__main__":
    main()
