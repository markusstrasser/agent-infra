#!/usr/bin/env python3
"""Ingest selve research memos and entity files into the knowledge substrate.

Parses:
- YAML frontmatter from research memos and entity files
- Decision Claims tables from memo contract-compliant memos
- Entity page claims with inline citations

Deterministic — no LLM calls.

Usage:
    uv run python3 substrate/ingest_selve.py [--dry-run]
"""

import argparse
import re
from pathlib import Path

import yaml

from substrate.core import KnowledgeDB

SELVE_ROOT = Path.home() / "Projects" / "selve"
RESEARCH_DIR = SELVE_ROOT / "docs" / "research"
ENTITIES_DIR = SELVE_ROOT / "docs" / "entities"
DB_PATH = Path.home() / ".claude" / "knowledge" / "selve.db"


def extract_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text()
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None


def extract_decision_claims(path: Path) -> list[dict]:
    """Extract Decision Claims table rows from a memo."""
    text = path.read_text()
    claims = []

    # Find the Decision Claims table
    m = re.search(r'##\s*Decision Claims.*?\n\n?(\|.*?\n)+', text, re.IGNORECASE)
    if not m:
        return claims

    table_text = m.group(0)
    lines = table_text.strip().split('\n')

    # Find header row and separator
    header_idx = None
    for i, line in enumerate(lines):
        if '|' in line and 'Claim' in line:
            header_idx = i
            break

    if header_idx is None:
        return claims

    # Parse data rows (skip header and separator)
    for line in lines[header_idx + 2:]:
        if not line.strip().startswith('|'):
            break
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) >= 6:
            claim_text = cells[0].strip()
            if not claim_text or claim_text == '---':
                continue
            claims.append({
                "claim": claim_text,
                "direction": cells[1].strip() if len(cells) > 1 else "",
                "evidence_grade": cells[2].strip() if len(cells) > 2 else "",
                "population_match": cells[3].strip() if len(cells) > 3 else "",
                "citation_ids": cells[4].strip() if len(cells) > 4 else "",
                "status": cells[5].strip().strip('`') if len(cells) > 5 else "",
            })

    return claims


def slugify(text: str, max_len: int = 50) -> str:
    """Convert text to a kebab-case slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text.strip())
    return text[:max_len].rstrip('-')


def ingest_research_memos(db: KnowledgeDB, dry_run: bool) -> dict:
    """Ingest research memos as artifacts + extract Decision Claims."""
    stats = {"memos": 0, "claims": 0, "citations": 0, "skipped": 0}

    skip_files = {"_MEMO_TEMPLATE.md", "MEMO_CONTRACT.md", "README.md"}

    for memo_file in sorted(RESEARCH_DIR.glob("*.md")):
        if memo_file.name in skip_files:
            stats["skipped"] += 1
            continue

        fm = extract_frontmatter(memo_file)
        stem = memo_file.stem
        rel_path = str(memo_file.relative_to(SELVE_ROOT))

        # Register memo as artifact
        memo_id = f"memo-{stem}"
        title = fm.get("title", stem.replace("_", " ").replace("-", " ").title()) if fm else stem
        if isinstance(title, str) and len(title) > 100:
            title = title[:97] + "..."

        if not dry_run:
            db.register_artifact(
                memo_id, type="research_memo",
                path=rel_path,
                title=title,
                payload={
                    "date": str(fm.get("date", "")) if fm else "",
                    "tags": fm.get("tags", []) if fm else [],
                    "status": fm.get("status", "") if fm else "",
                },
            )
        stats["memos"] += 1

        # Extract Decision Claims
        claims = extract_decision_claims(memo_file)
        for i, claim in enumerate(claims):
            claim_id = f"claim-{stem}-{i}"
            if not dry_run:
                # Map status strings
                status = claim.get("status", "active")
                if status in ("verified", "confirmed"):
                    status = "verified"
                elif status in ("uncertain", "unverified"):
                    status = "active"
                elif status in ("contradicted", "refuted"):
                    status = "invalidated"

                db.register_assertion(
                    claim_id, type="decision_claim",
                    status=status,
                    title=claim["claim"][:120],
                    source_file=rel_path,
                    payload={
                        "direction": claim.get("direction", ""),
                        "evidence_grade": claim.get("evidence_grade", ""),
                        "population_match": claim.get("population_match", ""),
                        "citation_ids": claim.get("citation_ids", ""),
                    },
                )
                # Link claim to memo
                db.add_relation(claim_id, memo_id, "derived_from")

            stats["claims"] += 1

            # Register cited evidence
            citation_str = claim.get("citation_ids", "")
            if citation_str:
                for cid in re.split(r'[,;]\s*', citation_str):
                    cid = cid.strip()
                    if not cid:
                        continue
                    ev_id = f"ev-{slugify(cid, 40)}"
                    source_type = "doi" if cid.startswith("10.") else "pmid" if cid.startswith("PMC") or cid.isdigit() else "reference"

                    if not dry_run:
                        db.register_evidence(
                            ev_id, type="paper",
                            source=f"{source_type}:{cid}",
                            title=cid,
                        )
                        db.add_relation(claim_id, ev_id, "supported_by")

                    stats["citations"] += 1

        if claims:
            print(f"  {stem}: {len(claims)} claims")
        else:
            print(f"  {stem}: (no decision claims table)")

    return stats


def ingest_entities(db: KnowledgeDB, dry_run: bool) -> dict:
    """Ingest entity files."""
    stats = {"entities": 0, "skipped": 0}

    for entity_file in sorted(ENTITIES_DIR.rglob("*.md")):
        if entity_file.name == "README.md":
            stats["skipped"] += 1
            continue

        fm = extract_frontmatter(entity_file)
        stem = entity_file.stem
        rel_path = str(entity_file.relative_to(SELVE_ROOT))
        subdir = entity_file.parent.name  # genes, self, companies, etc.

        title = fm.get("title", stem) if fm else stem
        if isinstance(title, str) and len(title) > 100:
            title = title[:97] + "..."

        entity_id = f"entity-{subdir}-{stem.lower()}"

        if not dry_run:
            db.register_artifact(
                entity_id, type=f"entity_{subdir}",
                path=rel_path,
                title=title,
                payload={
                    "last_reviewed": str(fm.get("last_reviewed", "")) if fm else "",
                    "coverage": fm.get("coverage", []) if fm else [],
                    "verification": fm.get("verification", "") if fm else "",
                    "derived_from": fm.get("derived_from", []) if fm else [],
                },
            )

            # If entity has derived_from, link to source memos
            if fm and "derived_from" in fm:
                for source in fm["derived_from"]:
                    source_stem = Path(source).stem
                    source_id = f"memo-{source_stem}"
                    # Only link if source exists in DB
                    if db.get(source_id):
                        db.add_relation(entity_id, source_id, "derived_from")

        stats["entities"] += 1
        print(f"  [{subdir}] {stem}: {title[:60]}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest selve docs into substrate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Selve substrate ingestion ({'dry run' if args.dry_run else 'live'})")
    print(f"  Research: {RESEARCH_DIR}")
    print(f"  Entities: {ENTITIES_DIR}")
    print(f"  DB: {DB_PATH}")
    print()

    db = KnowledgeDB(DB_PATH)

    print("=== Research memos ===")
    memo_stats = ingest_research_memos(db, args.dry_run)

    print("\n=== Entity files ===")
    entity_stats = ingest_entities(db, args.dry_run)

    print(f"\n=== Summary ===")
    print(f"  Memos: {memo_stats['memos']} (skipped: {memo_stats['skipped']})")
    print(f"  Decision claims extracted: {memo_stats['claims']}")
    print(f"  Citation evidence links: {memo_stats['citations']}")
    print(f"  Entity files: {entity_stats['entities']} (skipped: {entity_stats['skipped']})")

    if not args.dry_run:
        s = db.stats()
        print(f"\n=== DB totals ===")
        for k, v in s.items():
            print(f"  {k}: {v}")

    db.close()


if __name__ == "__main__":
    main()
