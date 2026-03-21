#!/usr/bin/env python3
"""Ingest intel entity files and thesis checks into the knowledge substrate.

Parses YAML frontmatter from entity files to extract:
- Entity conviction state (assertion)
- Conviction journal entries (assertions with evidence links)
- Thesis checks (artifacts)
- Dependency edges between them

Deterministic — no LLM calls. Uses existing structured frontmatter.

Usage:
    uv run python3 substrate/ingest_intel.py [--dry-run]
"""

import argparse
import re
import sys
from pathlib import Path

# Shared frontmatter parser
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from config import extract_frontmatter  # noqa: E402

from substrate.core import KnowledgeDB

INTEL_ROOT = Path.home() / "Projects" / "intel"
ENTITIES_DIR = INTEL_ROOT / "analysis" / "entities"
THESIS_DIR = INTEL_ROOT / "analysis" / "investments" / "thesis_checks"
DB_PATH = Path.home() / ".claude" / "knowledge" / "intel.db"


def ingest_entities(db: KnowledgeDB, dry_run: bool) -> dict:
    """Ingest entity files. Returns stats."""
    stats = {"entities": 0, "journal_entries": 0, "evidence_links": 0, "skipped": 0}

    for entity_file in sorted(ENTITIES_DIR.glob("*.md")):
        fm = extract_frontmatter(entity_file)
        if not fm or "ticker" not in fm:
            stats["skipped"] += 1
            continue

        ticker = fm["ticker"]
        conviction = fm.get("conviction", "UNKNOWN")
        last_reviewed = fm.get("last_reviewed", "unknown")

        # Register entity conviction as assertion
        entity_id = f"{ticker.lower()}-conviction"
        if not dry_run:
            db.register_assertion(
                entity_id, type="conviction",
                status="active",
                title=f"{ticker} conviction: {conviction} (reviewed {last_reviewed})",
                source_file=str(entity_file.relative_to(INTEL_ROOT)),
                payload={
                    "ticker": ticker,
                    "conviction": conviction,
                    "last_reviewed": str(last_reviewed),
                    "coverage": fm.get("coverage", {}),
                },
            )
        stats["entities"] += 1
        print(f"  {ticker}: conviction={conviction}, reviewed={last_reviewed}")

        # Process conviction journal entries
        journal = fm.get("conviction_journal", [])
        if not journal:
            continue

        for i, entry in enumerate(journal):
            entry_id = f"{ticker.lower()}-journal-{entry.get('date', i)}"
            evidence_ref = entry.get("evidence", "")

            if not dry_run:
                # Register journal entry as assertion
                db.register_assertion(
                    entry_id, type="conviction_update",
                    status="active",
                    title=f"{ticker} {entry.get('prior','?')}→{entry.get('posterior','?')}: {entry.get('trigger', 'no trigger')}",
                    source_file=str(entity_file.relative_to(INTEL_ROOT)),
                    payload={
                        "ticker": ticker,
                        "date": str(entry.get("date", "")),
                        "prior": entry.get("prior"),
                        "posterior": entry.get("posterior"),
                        "trigger": entry.get("trigger"),
                        "scenarios": entry.get("scenarios_snapshot"),
                        "action": entry.get("action"),
                        "instrument": entry.get("instrument"),
                        "kl_div": entry.get("kl_div"),
                    },
                )

                # Link journal entry to entity conviction
                db.add_relation(entity_id, entry_id, "derived_from")

            stats["journal_entries"] += 1

            # Register evidence if it's a file reference
            if evidence_ref and not evidence_ref.startswith("http"):
                ev_id = f"ev-{ticker.lower()}-{Path(evidence_ref).stem}"
                if not dry_run:
                    db.register_evidence(
                        ev_id, type="thesis_check",
                        source=f"file:{evidence_ref}",
                        title=f"{ticker} thesis check: {Path(evidence_ref).stem}",
                    )
                    db.add_relation(entry_id, ev_id, "supported_by")
                stats["evidence_links"] += 1

            elif evidence_ref and evidence_ref.startswith("http"):
                ev_id = f"ev-{ticker.lower()}-url-{i}"
                grade = ""
                # Extract source grade if present (e.g., "[A1]")
                grade_match = re.search(r'\[([A-F][1-6])\]', evidence_ref)
                if grade_match:
                    grade = grade_match.group(1)
                    evidence_ref = evidence_ref[:grade_match.start()].strip()

                if not dry_run:
                    db.register_evidence(
                        ev_id, type="external_source",
                        source=f"url:{evidence_ref}",
                        title=f"{ticker} external evidence",
                        source_grade=grade or None,
                    )
                    db.add_relation(entry_id, ev_id, "supported_by")
                stats["evidence_links"] += 1

    return stats


def ingest_thesis_checks(db: KnowledgeDB, dry_run: bool) -> dict:
    """Ingest thesis check documents as artifacts."""
    stats = {"thesis_checks": 0}

    for thesis_file in sorted(THESIS_DIR.glob("*.md")):
        stem = thesis_file.stem  # e.g., "hims_2026-02-25"
        parts = stem.rsplit("_", 1)
        ticker = parts[0].upper() if parts else stem.upper()
        date = parts[1] if len(parts) > 1 else "unknown"

        artifact_id = f"thesis-check-{stem}"
        title_line = thesis_file.read_text().splitlines()[0] if thesis_file.stat().st_size > 0 else ""
        title = title_line.lstrip("#").strip() if title_line.startswith("#") else f"{ticker} thesis check {date}"

        if not dry_run:
            db.register_artifact(
                artifact_id, type="thesis_check",
                path=str(thesis_file.relative_to(INTEL_ROOT)),
                title=title,
                payload={"ticker": ticker, "date": date},
            )

            # Link to entity conviction if it exists
            entity_id = f"{ticker.lower()}-conviction"
            entity = db.get(entity_id)
            if entity:
                db.add_relation(entity_id, artifact_id, "derived_from")

        stats["thesis_checks"] += 1
        print(f"  {artifact_id}: {title[:60]}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest intel entities into substrate")
    parser.add_argument("--dry-run", action="store_true", help="Report without modifying DB")
    args = parser.parse_args()

    print(f"Intel substrate ingestion ({'dry run' if args.dry_run else 'live'})")
    print(f"  Entities: {ENTITIES_DIR}")
    print(f"  Thesis checks: {THESIS_DIR}")
    print(f"  DB: {DB_PATH}")
    print()

    db = KnowledgeDB(DB_PATH)

    print("=== Entity files ===")
    entity_stats = ingest_entities(db, args.dry_run)

    print("\n=== Thesis checks ===")
    thesis_stats = ingest_thesis_checks(db, args.dry_run)

    print(f"\n=== Summary ===")
    print(f"  Entities: {entity_stats['entities']} (skipped: {entity_stats['skipped']})")
    print(f"  Journal entries: {entity_stats['journal_entries']}")
    print(f"  Evidence links: {entity_stats['evidence_links']}")
    print(f"  Thesis checks: {thesis_stats['thesis_checks']}")

    if not args.dry_run:
        s = db.stats()
        print(f"\n=== DB totals ===")
        for k, v in s.items():
            print(f"  {k}: {v}")

    db.close()


if __name__ == "__main__":
    main()
