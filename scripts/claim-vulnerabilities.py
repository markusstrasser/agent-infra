#!/usr/bin/env python3
"""
Claim vulnerability detection across research memos.

Scans research memos for claims that reference discredited paradigms,
vendor sources, stale evidence, animal-only extrapolation, and small-N studies.
Has a curated DISCREDITED_PARADIGMS registry.

Usage:
    uv run python3 scripts/claim-vulnerabilities.py
    uv run python3 scripts/claim-vulnerabilities.py --target ~/Projects/selve/docs/research
    uv run python3 scripts/claim-vulnerabilities.py --memo research/specific.md

Source: selve/scripts/test_claim_vulnerabilities.py
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path

from config import PROJECT_ROOTS, RESEARCH_DIRS, PROSE_EXTENSIONS
from common import con


# ──────────────────────────────────────────────────────────────
# Claim vulnerability registry (curated, extendable)
# ──────────────────────────────────────────────────────────────

DISCREDITED_PARADIGMS = {
    # Genomics
    "5-httlpr": ("candidate gene", "~98% non-replication (Border et al. 2019)"),
    "5httlpr": ("candidate gene", "~98% non-replication (Border et al. 2019)"),
    "serotonin transporter": ("candidate gene", "~98% non-replication (Border et al. 2019)"),
    "comt val158met": ("candidate gene", "Variable replication, context-dependent"),
    "bdnf val66met": ("candidate gene", "Poor replication outside East Asian populations"),
    "drd4": ("candidate gene", "Novelty-seeking association not replicated"),
    "maoa warrior gene": ("candidate gene", "Not replicated, ethical concerns"),
    "oxtr rs53576": ("candidate gene", "Social behavior associations not replicated"),
    # Psychology
    "ego depletion": ("failed replication", "Preregistered RRR failed (Hagger et al. 2016)"),
    "power posing": ("failed replication", "Hormonal effects not replicated (Ranehill 2015)"),
    "social priming": ("failed replication", "Walking speed, professor priming not replicated"),
    "facial feedback": ("failed replication", "Pencil-in-mouth RRR failed (Wagenmakers 2016)"),
    "stereotype threat": ("contested", "Effect sizes shrinking (Flore & Wicherts 2015 meta)"),
    "brain training": ("failed replication", "No transfer effects (Simons 2016), FTC action"),
    "growth mindset": ("contested", "Effect sizes much smaller than initial claims"),
    # Nutrition
    "raspberry ketones": ("no human evidence", "Only animal/in-vitro data, marketed without trials"),
    "garcinia cambogia": ("failed replication", "Meta-analysis shows minimal/no effect (Onakpoya 2011)"),
    "detox cleanse": ("no mechanism", "No physiological basis; liver/kidneys handle detox"),
}

# Vendor claim patterns — source domains that are company marketing
VENDOR_DOMAINS = {
    "elementbiosciences.com", "pacb.com", "nanoporetech.com", "illumina.com",
    "10xgenomics.com", "twistbioscience.com", "ultima-genomics.com",
    "armra.com", "herbalife.com", "thorne.com", "examine.com",
}

# Pricing staleness thresholds (months)
STALENESS_THRESHOLDS = {
    "sequencing": 6,
    "compute": 3,
    "regulatory": 3,
    "device": 12,
    "supplement_price": 12,
}


@dataclass
class ClaimVulnerability:
    memo: str
    claim_text: str
    claim_num: int
    vulnerabilities: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    severity: str = ""  # "VETO" | "WARNING" | "INFO" | "OK"


# ──────────────────────────────────────────────────────────────
# Claim extraction from memo tables
# ──────────────────────────────────────────────────────────────

def extract_claims_table(text: str) -> list[dict]:
    """Extract claims from markdown tables in research memos.

    Looks for tables where first column is numeric (claim #) and second column
    is the claim text. Captures source/evidence and status columns too.
    """
    claims = []
    in_table = False
    headers: list[str] = []

    for line in text.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            in_table = False
            headers = []
            continue

        cols = [c.strip() for c in line.split('|')[1:-1]]
        if not cols or len(cols) < 3:
            continue

        # Skip separator rows
        if all(re.match(r'^[-:]+$', c) for c in cols if c):
            continue

        # Detect header row
        if not in_table:
            headers = [c.lower().strip() for c in cols]
            in_table = True
            continue

        # Only process rows where first column is numeric (claim #)
        first = cols[0].strip()
        if not re.match(r'^\d+$', first) and not re.match(r'^\*\*\d+\*\*$', first):
            # Also accept non-numbered rows if we're in a claims table
            if not any(h in headers for h in ('#', 'claim', 'finding')):
                continue

        # Build claim dict from headers
        claim = {}
        for i, h in enumerate(headers):
            if i < len(cols):
                claim[h] = cols[i]

        # Extract claim text — try multiple column names
        claim_text = ""
        for key in ('claim', 'finding', 'description', 'what', 'supplement'):
            if key in claim and claim[key] and len(claim[key]) > 5:
                claim_text = claim[key]
                break
        # Fallback: second column if it's longer than first
        if not claim_text and len(cols) > 1 and len(cols[1]) > 10:
            claim_text = cols[1]

        if claim_text and len(claim_text) > 10:
            source = claim.get('source', claim.get('evidence', ''))
            status = claim.get('status', '')
            if not source and len(cols) > 4:
                source = cols[4]
            if not status and len(cols) > 5:
                status = cols[5]

            claims.append({
                'text': claim_text[:300],
                'full_row': claim,
                'source': source[:300] if source else "",
                'status': status,
            })

    return claims


# ──────────────────────────────────────────────────────────────
# Vulnerability checks
# ──────────────────────────────────────────────────────────────

def check_discredited_paradigm(claim_text: str) -> tuple[str, str] | None:
    """Check if claim references a known discredited paradigm."""
    text_lower = claim_text.lower()
    for keyword, (category, detail) in DISCREDITED_PARADIGMS.items():
        if keyword in text_lower:
            return category, f"{keyword}: {detail}"
    return None


def check_vendor_source(claim: dict) -> str | None:
    """Check if claim source is a vendor (marketing, not independent)."""
    source = (claim.get('source', '') + " " + str(claim.get('full_row', {}))).lower()
    for domain in VENDOR_DOMAINS:
        if domain in source:
            return f"Source is vendor website: {domain}"
    return None


def check_staleness(claim: dict, memo_date: date | None) -> str | None:
    """Check if claim might be stale based on domain and memo date."""
    if not memo_date:
        return None

    age_months = (date.today() - memo_date).days / 30
    text = claim.get('text', '').lower()

    full_text = (text + " " + str(claim.get('full_row', {}))).lower()
    for domain, threshold in STALENESS_THRESHOLDS.items():
        keywords = {
            "sequencing": ["$/genome", "$/run", "/run", "/genome", "pricing", "cost", "$2,", "$1,", "$200", "$300", "$400", "$100"],
            "compute": ["$/hour", "gpu cost", "compute cost", "modal", "lambda"],
            "regulatory": ["fda", "clia", "cleared", "approved", "regulation", "enforcement", "vacated", "warning letter"],
            "device": ["device cost", "hardware", "instrument price"],
            "supplement_price": ["$/month", "$/mo"],
        }
        if any(kw in full_text for kw in keywords.get(domain, [])):
            if age_months > threshold:
                return f"Potentially stale: {domain} claim from {memo_date} ({age_months:.0f}mo ago, threshold {threshold}mo)"

    return None


def check_animal_extrapolation(claim_text: str) -> str | None:
    """Check for animal/in-vitro evidence being applied to human claims."""
    text_lower = claim_text.lower()
    animal_signals = ["mice", "mouse", "murine", "rat ", "rats ", "rodent",
                      "in vitro", "in-vitro", "cell line", "cell culture",
                      "zebrafish", "drosophila", "c. elegans"]
    human_claims = ["patients", "participants", "clinical", "therapeutic",
                    "dosage", "dose", "supplementation", "treatment"]

    has_animal = any(s in text_lower for s in animal_signals)
    has_human_claim = any(s in text_lower for s in human_claims)

    if has_animal and not has_human_claim:
        return "Animal/in-vitro evidence — check if applied to human claims"
    if has_animal and has_human_claim:
        return "Mixed animal+human language — verify human evidence exists"
    return None


def check_small_n(claim: dict) -> str | None:
    """Check for small sample sizes in quantitative claims."""
    text = claim.get('text', '')
    n_matches = re.findall(r'(?:n\s*=\s*|N\s*=\s*|(\d+)\s*(?:patients|participants|subjects|adults|mice|rats))', text)
    for m in n_matches:
        if m:
            n = int(m)
            if n < 30:
                return f"Very small sample (n={n})"
            elif n < 100:
                return f"Small sample (n={n})"
    return None


def assess_claim(claim: dict, memo_name: str, memo_date: date | None, claim_idx: int) -> ClaimVulnerability:
    """Run all vulnerability checks on a claim."""
    v = ClaimVulnerability(
        memo=memo_name,
        claim_text=claim['text'][:120],
        claim_num=claim_idx,
    )

    # Discredited paradigm
    paradigm = check_discredited_paradigm(claim['text'])
    if paradigm:
        v.vulnerabilities.append("DISCREDITED_PARADIGM")
        v.details.append(f"{paradigm[0]}: {paradigm[1]}")

    # Vendor source
    vendor = check_vendor_source(claim)
    if vendor:
        v.vulnerabilities.append("VENDOR_SOURCE")
        v.details.append(vendor)

    # Staleness
    stale = check_staleness(claim, memo_date)
    if stale:
        v.vulnerabilities.append("POTENTIALLY_STALE")
        v.details.append(stale)

    # Animal extrapolation
    animal = check_animal_extrapolation(claim['text'])
    if animal:
        v.vulnerabilities.append("ANIMAL_EXTRAPOLATION")
        v.details.append(animal)

    # Small n
    small_n = check_small_n(claim)
    if small_n:
        v.vulnerabilities.append("SMALL_N")
        v.details.append(small_n)

    # Severity
    if "DISCREDITED_PARADIGM" in v.vulnerabilities:
        v.severity = "VETO"
    elif any(x in v.vulnerabilities for x in ["ANIMAL_EXTRAPOLATION", "VENDOR_SOURCE"]):
        v.severity = "WARNING"
    elif v.vulnerabilities:
        v.severity = "INFO"
    else:
        v.severity = "OK"

    return v


# ──────────────────────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────────────────────

def extract_memo_date(text: str) -> date | None:
    """Extract date from YAML frontmatter."""
    m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def find_research_files(root: Path) -> list[Path]:
    """Find prose files in research directories under a project root."""
    files = []
    for dir_name in RESEARCH_DIRS:
        search_dir = root / dir_name
        if search_dir.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(search_dir.rglob(f"*{ext}"))
    return sorted(set(files))


def collect_files(target: Path | None, memo: Path | None) -> list[Path]:
    """Collect files to scan based on CLI args."""
    if memo:
        return [memo] if memo.exists() else []

    if target:
        # --target: scan recursively for .md files
        if target.is_file():
            return [target]
        return sorted(p for p in target.rglob("*.md") if p.is_file())

    # Default: scan all project roots
    files = []
    for name, root in PROJECT_ROOTS.items():
        if root.exists():
            files.extend(find_research_files(root))
    return sorted(set(files))


def run_on_memo(path: Path) -> list[ClaimVulnerability]:
    text = path.read_text(errors="replace")
    memo_date = extract_memo_date(text)
    claims = extract_claims_table(text)
    memo_name = path.stem

    results = []
    for i, claim in enumerate(claims, 1):
        v = assess_claim(claim, memo_name, memo_date, i)
        results.append(v)
    return results


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scan research memos for claim vulnerabilities (discredited paradigms, vendor sources, staleness, animal extrapolation, small-N)"
    )
    parser.add_argument("--target", type=Path, help="Directory to scan recursively for .md files (overrides default cross-project scan)")
    parser.add_argument("--memo", type=Path, help="Run on a specific memo file")
    args = parser.parse_args()

    paths = collect_files(args.target, args.memo)
    if not paths:
        con.fail("No files found to scan")
        return 1

    all_results = []
    scanned = 0
    for path in paths:
        if not path.exists():
            continue
        scanned += 1
        results = run_on_memo(path)
        all_results.extend(results)

    # Report
    flagged = [r for r in all_results if r.severity != "OK"]
    vetoes = [r for r in all_results if r.severity == "VETO"]
    warnings = [r for r in all_results if r.severity == "WARNING"]
    infos = [r for r in all_results if r.severity == "INFO"]

    con.header("Claim Vulnerability Scan")
    con.kv("Memos scanned", str(scanned))
    con.kv("Claims found", str(len(all_results)))
    con.kv("Flagged", f"{len(flagged)} ({len(vetoes)} VETO, {len(warnings)} WARNING, {len(infos)} INFO)")
    con.kv("Clean", str(len(all_results) - len(flagged)))

    if flagged:
        rows = []
        for r in flagged:
            vuln = ", ".join(r.vulnerabilities)
            detail = r.details[0][:50] if r.details else ""
            rows.append([r.memo[:38], str(r.claim_num), r.severity, vuln, detail])
        con.table(
            ["Memo", "#", "Severity", "Vulnerability", "Detail"],
            rows,
            widths=[40, 4, 10, 25, 50],
        )

    # Vulnerability type summary
    vuln_counts: dict[str, int] = {}
    for r in flagged:
        for v in r.vulnerabilities:
            vuln_counts[v] = vuln_counts.get(v, 0) + 1
    if vuln_counts:
        print()
        con.header("Vulnerability Types")
        for v, count in sorted(vuln_counts.items(), key=lambda x: -x[1]):
            print(f"    {count}\u00d7 {v}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
