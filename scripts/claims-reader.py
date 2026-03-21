#!/usr/bin/env python3
"""Claims Table Reader — extract structured epistemic data from researcher claims tables.

Parses markdown tables matching the researcher output format:
  | # | Claim | Evidence | Confidence | Source | Status |

Aggregates per-project: sourced_rate, verified_rate, unsourced_rate, frontier_rate.
Logs results to ~/.claude/epistemic-metrics.jsonl.

Usage: uv run python3 scripts/claims-reader.py [--project PROJECT] [--verbose]
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

from config import (
    METRICS_FILE,
    PROJECT_ROOTS,
    PROSE_EXTENSIONS,
    RESEARCH_DIRS,
    log_metric,
)

# Header pattern — any table with a "Claim" column
# Handles standard (6-col), selve genomics (7-col), and minimal (4-col) variants
HEADER_RE = re.compile(r"^\|.*\bClaim\b.*\|", re.IGNORECASE)

# Separator row: |---|---|---|...
SEPARATOR_RE = re.compile(r"^\|[\s\-:]+\|")

# Status normalization map
# Key distinction: "has a citation" (sourced) ≠ "was actually checked" (verified)
STATUS_MAP = {
    "verified": "verified",
    "sourced": "sourced",
    "calculated": "verified",  # CALCULATED implies derivation was shown
    "retracted": "retracted",
    "contested": "contested",
    "unverified": "unsourced",
    "inference": "unsourced",
    "training-data": "unsourced",
    "preprint": "frontier",
    "frontier": "frontier",
}


def normalize_status(raw: str) -> str:
    """Normalize a status field to one of: verified, sourced, unsourced, frontier, retracted, contested."""
    lower = raw.strip().lower()
    # Strip markdown formatting
    lower = lower.replace("**", "").replace("~~", "")
    # Check each known status keyword
    for keyword, normalized in STATUS_MAP.items():
        if keyword in lower:
            return normalized
    # Anything with a URL/DOI/arXiv reference is at least "sourced"
    if re.search(r"arxiv|doi|http|pmid|pmc|source:", raw, re.IGNORECASE):
        return "sourced"
    return "unsourced"


def normalize_confidence(raw: str) -> str:
    """Normalize confidence to HIGH/MEDIUM/LOW."""
    lower = raw.strip().lower().replace("**", "")
    if "high" in lower:
        return "HIGH"
    if "medium" in lower or "med" in lower:
        return "MEDIUM"
    if "low" in lower:
        return "LOW"
    return "UNKNOWN"


def parse_header_columns(header: str) -> dict[str, int]:
    """Parse header row to find column indices by name."""
    cells = [c.strip().lower() for c in header.split("|")]
    # Remove leading/trailing empties
    while cells and not cells[0]:
        cells.pop(0)
    while cells and not cells[-1]:
        cells.pop()
    cols = {}
    for i, cell in enumerate(cells):
        # Normalize column names
        if cell in ("#", "id"):
            cols["number"] = i
        elif "claim" in cell:
            cols["claim"] = i
        elif "evidence" in cell or "direction" in cell:
            cols["evidence"] = i
        elif "confidence" in cell or "evidence grade" in cell:
            cols["confidence"] = i
        elif "source" in cell or "citation" in cell:
            cols["source"] = i
        elif "status" in cell:
            cols["status"] = i
    return cols


def parse_table_row(row: str, col_map: dict[str, int]) -> dict | None:
    """Parse a single table row using column position map."""
    cells = [c.strip() for c in row.split("|")]
    # Remove leading/trailing empties
    while cells and not cells[0]:
        cells.pop(0)
    while cells and not cells[-1]:
        cells.pop()

    def get(name: str) -> str:
        idx = col_map.get(name)
        if idx is not None and idx < len(cells):
            return cells[idx]
        return ""

    claim_text = get("claim")
    # Skip empty or separator-like rows
    if not claim_text or claim_text.startswith("---"):
        return None

    evidence = get("evidence")
    confidence = get("confidence")
    source = get("source")
    status = get("status")

    # If no explicit status column, try to infer from other fields
    if not status and evidence:
        status = evidence  # Some tables pack status info into evidence

    return {
        "claim": claim_text,
        "evidence": evidence,
        "confidence": normalize_confidence(confidence),
        "source": source,
        "status_raw": status,
        "status": normalize_status(status),
    }


# Knowledge-index @claim pattern: <!-- @claim id=X conf=Y status=Z | statement -->
KNOWLEDGE_CLAIM_RE = re.compile(
    r"@claim\s+id=(\S+)\s+(?:conf(?:idence)?=(\S+)\s+)?(?:status=(\S+)\s+)?\|\s*(.+)"
)


def extract_claims_from_knowledge_index(text: str, path: Path) -> list[dict]:
    """Extract claims from <!-- knowledge-index --> blocks."""
    claims = []
    # Find the knowledge-index block
    m = re.search(
        r"<!-- knowledge-index\b(.*?)end-knowledge-index -->", text, re.DOTALL
    )
    if not m:
        return claims

    for line in m.group(1).split("\n"):
        line = line.strip()
        cm = KNOWLEDGE_CLAIM_RE.match(line)
        if cm:
            claim_id, conf, status, statement = cm.groups()
            claims.append({
                "claim": statement.strip(),
                "evidence": "",
                "confidence": normalize_confidence(conf or ""),
                "source": claim_id,
                "status_raw": status or "active",
                "status": normalize_status(status or "active"),
                "file": str(path),
                "source_type": "knowledge_index",
            })
    return claims


def extract_claims_from_file(path: Path) -> list[dict]:
    """Extract all claims from claims tables and knowledge-index blocks in a file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    claims = []

    # Extract from knowledge-index blocks first
    ki_claims = extract_claims_from_knowledge_index(text, path)
    claims.extend(ki_claims)

    # Extract from markdown tables
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        if HEADER_RE.match(line):
            col_map = parse_header_columns(line)
            # Require both Claim and Status columns — this distinguishes
            # researcher claims tables from other tables that happen to
            # have "Claim" in a header (e.g., platform sweep action tables)
            if "claim" not in col_map or "status" not in col_map:
                i += 1
                continue

            # Skip separator row
            i += 1
            if i < len(lines) and SEPARATOR_RE.match(lines[i]):
                i += 1

            # Parse data rows until we hit a non-table line
            while i < len(lines):
                row = lines[i]
                if not row.strip().startswith("|"):
                    break
                if SEPARATOR_RE.match(row):
                    i += 1
                    continue
                claim = parse_table_row(row, col_map)
                if claim:
                    claim["file"] = str(path)
                    claim["source_type"] = "table"
                    claims.append(claim)
                i += 1
        else:
            i += 1

    return claims


def find_prose_files(project_name: str) -> list[Path]:
    """Find prose files in research directories for a project."""
    root = PROJECT_ROOTS.get(project_name)
    if not root or not root.exists():
        return []
    files = []
    for research_dir in RESEARCH_DIRS:
        dir_path = root / research_dir
        if dir_path.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(dir_path.rglob(f"*{ext}"))
    # Also check .model-review directories
    model_review = root / ".model-review"
    if model_review.exists():
        for ext in PROSE_EXTENSIONS:
            files.extend(model_review.rglob(f"*{ext}"))
    return files


def main():
    project_filter = None
    verbose = False

    args = sys.argv[1:]
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project_filter = args[idx + 1]
    if "--verbose" in args:
        verbose = True

    all_claims: dict[str, list[dict]] = defaultdict(list)
    files_with_tables = 0
    files_scanned = 0

    projects = (
        [project_filter] if project_filter else list(PROJECT_ROOTS.keys())
    )

    for project in projects:
        if project not in PROJECT_ROOTS:
            print(f"Unknown project: {project}")
            continue

        files = find_prose_files(project)
        for fpath in files:
            files_scanned += 1
            claims = extract_claims_from_file(fpath)
            if claims:
                files_with_tables += 1
                for c in claims:
                    c["project"] = project
                all_claims[project].extend(claims)

    total_claims = sum(len(v) for v in all_claims.values())

    if total_claims == 0:
        print("No claims tables found.")
        return

    # Aggregate
    print(f"{'=' * 55}")
    print("  Claims Table Reader")
    print(f"{'=' * 55}")
    print()
    print(f"  Files scanned:     {files_scanned}")
    print(f"  Files with tables: {files_with_tables}")
    print(f"  Total claims:      {total_claims}")
    print()

    # Per-project breakdown
    by_project_metrics = {}
    for project in projects:
        claims = all_claims.get(project, [])
        if not claims:
            continue

        n = len(claims)
        verified = sum(1 for c in claims if c["status"] == "verified")
        sourced = sum(1 for c in claims if c["status"] == "sourced")
        unsourced = sum(1 for c in claims if c["status"] == "unsourced")
        frontier = sum(1 for c in claims if c["status"] == "frontier")
        retracted = sum(1 for c in claims if c["status"] == "retracted")
        contested = sum(1 for c in claims if c["status"] == "contested")

        # Rates
        verified_rate = verified / n
        # sourced_rate = has_any_source (verified + sourced + frontier)
        sourced_rate = (verified + sourced + frontier) / n
        unsourced_rate = unsourced / n
        frontier_rate = frontier / n

        # Invariant check: verified_rate ≤ sourced_rate always
        assert verified_rate <= sourced_rate + 1e-9, (
            f"Invariant violated: verified_rate ({verified_rate:.3f}) > "
            f"sourced_rate ({sourced_rate:.3f}) in {project}"
        )

        by_project_metrics[project] = {
            "total": n,
            "verified": verified,
            "sourced": sourced,
            "unsourced": unsourced,
            "frontier": frontier,
            "retracted": retracted,
            "contested": contested,
            "verified_rate": round(verified_rate, 4),
            "sourced_rate": round(sourced_rate, 4),
            "unsourced_rate": round(unsourced_rate, 4),
            "frontier_rate": round(frontier_rate, 4),
        }

        # Confidence distribution
        by_conf = defaultdict(int)
        for c in claims:
            by_conf[c["confidence"]] += 1

        print(f"  {project}:")
        print(f"    Claims:     {n}")
        print(f"    Verified:   {verified} ({verified_rate:.0%})")
        print(f"    Sourced:    {sourced} ({sourced / n:.0%})")
        print(f"    Unsourced:  {unsourced} ({unsourced_rate:.0%})")
        print(f"    Frontier:   {frontier} ({frontier_rate:.0%})")
        if retracted:
            print(f"    Retracted:  {retracted}")
        if contested:
            print(f"    Contested:  {contested}")
        conf_parts = [f"{k}={v}" for k, v in sorted(by_conf.items())]
        print(f"    Confidence: {', '.join(conf_parts)}")
        print()

    if verbose:
        # Show unsourced claims
        unsourced_claims = [
            c
            for claims in all_claims.values()
            for c in claims
            if c["status"] == "unsourced"
        ]
        if unsourced_claims:
            print("  Unsourced claims (sample):")
            for c in unsourced_claims[:15]:
                short = c["claim"][:70]
                print(f"    [{c['project']}] {short}...")
                if verbose:
                    print(f"      file: {c['file']}")
                    print(f"      raw status: {c['status_raw']}")
            if len(unsourced_claims) > 15:
                print(f"    ... and {len(unsourced_claims) - 15} more")
            print()

        # Show retracted claims
        retracted_claims = [
            c
            for claims in all_claims.values()
            for c in claims
            if c["status"] == "retracted"
        ]
        if retracted_claims:
            print("  Retracted claims:")
            for c in retracted_claims:
                short = c["claim"][:70]
                print(f"    [{c['project']}] {short}")
            print()

    # Overall rates
    all_flat = [c for claims in all_claims.values() for c in claims]
    overall_verified = sum(1 for c in all_flat if c["status"] == "verified") / total_claims
    overall_sourced = (
        sum(1 for c in all_flat if c["status"] in ("verified", "sourced", "frontier"))
        / total_claims
    )

    print(f"  Overall verified rate: {overall_verified:.1%}")
    print(f"  Overall sourced rate:  {overall_sourced:.1%}")
    print()

    # Log to metrics file
    log_metric(
        "claims_reader",
        files_scanned=files_scanned,
        files_with_tables=files_with_tables,
        total_claims=total_claims,
        verified_rate=round(overall_verified, 4),
        sourced_rate=round(overall_sourced, 4),
        by_project=by_project_metrics,
    )
    print(f"  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
