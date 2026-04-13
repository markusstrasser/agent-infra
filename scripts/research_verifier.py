#!/usr/bin/env python3
"""Generate a companion verification artifact for claim-heavy research memos.

This is intentionally advisory. It extracts the claims table when present and
summarizes:
- source inventory
- verified claims
- claims that remain inferred / frontier / unsourced
- process-state buckets (searched / read / verified / inferred)

Usage:
    uv run python3 scripts/research_verifier.py research/foo.md
    uv run python3 scripts/research_verifier.py research/foo.md --write-companion
"""

from __future__ import annotations

import argparse
import importlib.util
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


SOURCE_TAG_RE = re.compile(r"\[SOURCE:\s*([^\]]+)\]", re.IGNORECASE)
INFERENCE_TAG_RE = re.compile(r"\[(INFERENCE|TRAINING-DATA|UNVERIFIED|PREPRINT)\]", re.IGNORECASE)
ARTIFACT_DIR = Path("artifacts") / "research-verification"


@dataclass
class VerificationArtifact:
    memo_path: Path
    total_claims: int
    status_counts: Counter
    source_inventory: list[str]
    verified_claims: list[dict]
    followup_claims: list[dict]
    inference_tags: list[str]


def load_claims_reader():
    module_path = Path(__file__).with_name("claims-reader.py")
    spec = importlib.util.spec_from_file_location("claims_reader_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load claims-reader from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_sources(raw: str) -> list[str]:
    tagged = [match.strip() for match in SOURCE_TAG_RE.findall(raw)]
    if tagged:
        return tagged
    raw = raw.strip()
    return [raw] if raw else []


def build_artifact(memo_path: Path) -> VerificationArtifact:
    module = load_claims_reader()
    claims = module.extract_claims_from_file(memo_path)
    text = memo_path.read_text(encoding="utf-8", errors="replace")
    source_inventory: set[str] = set()
    verified_claims: list[dict] = []
    followup_claims: list[dict] = []
    status_counts: Counter = Counter()

    for index, claim in enumerate(claims, start=1):
        status = claim.get("status", "unsourced")
        status_counts[status] += 1
        sources = extract_sources(str(claim.get("source", "") or ""))
        source_inventory.update(sources)
        item = {
            "id": index,
            "claim": claim.get("claim", "").strip(),
            "status": status,
            "sources": sources,
            "confidence": claim.get("confidence", "UNKNOWN"),
        }
        if status == "verified":
            verified_claims.append(item)
        elif status in {"unsourced", "frontier", "contested", "retracted"}:
            followup_claims.append(item)

    return VerificationArtifact(
        memo_path=memo_path,
        total_claims=len(claims),
        status_counts=status_counts,
        source_inventory=sorted(source_inventory),
        verified_claims=verified_claims,
        followup_claims=followup_claims,
        inference_tags=sorted(set(INFERENCE_TAG_RE.findall(text))),
    )


def render_artifact(artifact: VerificationArtifact) -> str:
    lines: list[str] = []
    lines.append(f"# Verification Artifact — {artifact.memo_path.name}")
    lines.append("")
    lines.append(f"- Memo: `{artifact.memo_path}`")
    lines.append(f"- Generated: `{datetime.now(UTC).isoformat(timespec='seconds')}`")
    lines.append(f"- Total claims: `{artifact.total_claims}`")
    lines.append("")
    lines.append("## Status Summary")
    if artifact.status_counts:
        for status, count in sorted(artifact.status_counts.items()):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- No claims table detected.")
    lines.append("")
    lines.append("## Process-State Artifact")
    lines.append("- `searched`: all unique cited sources seen in the claims table")
    if artifact.source_inventory:
        for source in artifact.source_inventory:
            lines.append(f"  - {source}")
    else:
        lines.append("  - none detected")
    lines.append("- `read`: sources attached to verified claims")
    read_sources = sorted(
        {
            source
            for claim in artifact.verified_claims
            for source in claim["sources"]
        }
    )
    if read_sources:
        for source in read_sources:
            lines.append(f"  - {source}")
    else:
        lines.append("  - none detected")
    lines.append("- `verified`: claims marked VERIFIED")
    if artifact.verified_claims:
        for claim in artifact.verified_claims:
            lines.append(f"  - C{claim['id']}: {claim['claim']}")
    else:
        lines.append("  - none")
    lines.append("- `inferred`: claims still unsourced/frontier/contested/retracted plus memo-level inference tags")
    if artifact.followup_claims:
        for claim in artifact.followup_claims:
            lines.append(f"  - C{claim['id']} [{claim['status']}]: {claim['claim']}")
    elif artifact.inference_tags:
        for tag in artifact.inference_tags:
            lines.append(f"  - [{tag}]")
    else:
        lines.append("  - none")
    lines.append("")
    lines.append("## Follow-Up Candidates")
    if artifact.followup_claims:
        for claim in artifact.followup_claims:
            source_str = ", ".join(claim["sources"]) if claim["sources"] else "no source field"
            lines.append(
                f"- C{claim['id']} `{claim['status']}` `{claim['confidence']}` — {claim['claim']} "
                f"(sources: {source_str})"
            )
    else:
        lines.append("- No unresolved claim rows detected.")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This artifact is advisory. It does not prove that a source quote supports a claim.")
    lines.append("- Its purpose is to make the verify stage explicit and auditable before synthesis is treated as done.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memo", help="Research memo path")
    parser.add_argument("--write-companion", action="store_true", help="Write a companion artifact file")
    parser.add_argument(
        "--artifact-dir",
        default=str(ARTIFACT_DIR),
        help="Artifact output directory (used with --write-companion)",
    )
    args = parser.parse_args(argv)

    memo_path = Path(args.memo).resolve()
    artifact = build_artifact(memo_path)
    output = render_artifact(artifact)
    if args.write_companion:
        out_dir = Path(args.artifact_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{memo_path.stem}.verification.md"
        target.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
