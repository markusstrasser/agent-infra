#!/usr/bin/env python3
"""SAFE-lite Eval — factual precision measurement.

Implements a simplified version of the SAFE (Search-Augmented Factual Evaluation)
methodology from Google DeepMind (NeurIPS 2024). Decomposes research outputs into
atomic claims, verifies each via web search, and judges support.

Usage: uv run python3 scripts/safe-lite-eval.py [--project intel|meta|selve|genomics]
                                                 [--n 5] [--verbose] [--dry-run]

Cost estimate: ~$2-5 per run at 5 outputs x ~15 claims x 3 Exa calls.
Run manually weekly/biweekly.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from config import METRICS_FILE, PROJECT_ROOTS, RESEARCH_DIRS


def find_recent_research_files(project: str, n: int) -> list[Path]:
    """Find N most recently modified research files via git log."""
    root = PROJECT_ROOTS.get(project)
    if not root or not root.exists():
        return []

    # Get recently changed research files from git
    research_globs = [f"{d}/**/*.md" for d in RESEARCH_DIRS]
    files = []
    for glob in research_globs:
        full_dir = root / glob.split("/")[0]
        if full_dir.exists():
            found = list(full_dir.rglob("*.md"))
            files.extend(found)

    # Sort by mtime, most recent first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Filter out very small files (< 200 chars — likely stubs)
    files = [f for f in files if f.stat().st_size > 200]

    return files[:n]


def decompose_claims(text: str) -> list[str]:
    """Use Claude to decompose text into atomic verifiable claims."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package required. Install with: uv add anthropic")
        sys.exit(1)

    client = anthropic.Anthropic()

    # Truncate to ~4000 chars to keep cost low
    if len(text) > 4000:
        text = text[:4000] + "\n[...truncated...]"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Extract all verifiable factual claims from this text. A verifiable claim is one that can be checked against external sources — specific numbers, dates, attributions, named entities with properties, cause-effect relationships.

Exclude: opinions, subjective assessments, future predictions, definitions, methodological descriptions, meta-commentary about the document itself.

Return ONLY a JSON array of strings. Each string is one atomic claim.
Example: ["Company X reported $2.5B revenue in Q3 2025", "The MRCR benchmark shows 16.6% accuracy for Flash-Lite"]

Text:
{text}

JSON array:"""
        }],
    )

    result = response.content[0].text.strip()
    # Parse JSON array from response
    try:
        # Find JSON array in response
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            claims = json.loads(match.group())
            return [c for c in claims if isinstance(c, str) and len(c) > 10]
    except json.JSONDecodeError:
        pass

    return []


def search_claim(claim: str) -> list[dict]:
    """Search for evidence about a claim using Exa via MCP."""
    # Use subprocess to call Exa via the MCP server's HTTP endpoint
    # Fallback: use WebSearch via a simple HTTP call
    # Simplest approach: use the Exa Python SDK directly if available,
    # otherwise fall back to a web search command

    try:
        from exa_py import Exa

        api_key = os.environ.get("EXA_API_KEY", "")
        if not api_key:
            # Try to read from .mcp.json
            for mcp_path in [
                Path.home() / "Projects" / "meta" / ".mcp.json",
                Path.home() / ".mcp.json",
            ]:
                if mcp_path.exists():
                    with open(mcp_path) as f:
                        config = json.load(f)
                    for server in config.get("mcpServers", {}).values():
                        url = server.get("url", "")
                        if "exaApiKey=" in url:
                            api_key = url.split("exaApiKey=")[1].split("&")[0]
                            break
                if api_key:
                    break

        if not api_key:
            return []

        exa = Exa(api_key=api_key)
        results = exa.search_and_contents(
            claim,
            num_results=3,
            text={"max_characters": 1000},
        )
        return [
            {
                "title": r.title or "",
                "url": r.url or "",
                "text": (r.text or "")[:500],
            }
            for r in results.results
        ]
    except ImportError:
        return []
    except Exception as e:
        print(f"  WARNING: Search failed for claim: {e}", file=sys.stderr)
        return []


def judge_claim(claim: str, evidence: list[dict]) -> str:
    """Use Claude Haiku to judge if evidence supports the claim."""
    try:
        import anthropic
    except ImportError:
        return "unclear"

    if not evidence:
        return "unclear"

    evidence_text = "\n\n".join(
        f"Source: {e['title']} ({e['url']})\n{e['text']}" for e in evidence
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Does the evidence support this claim?

Claim: {claim}

Evidence:
{evidence_text}

Answer with exactly one word: "supported", "contradicted", or "unclear".
If the evidence partially supports but key details differ, say "contradicted".
If evidence is irrelevant or doesn't address the claim, say "unclear"."""
        }],
    )

    result = response.content[0].text.strip().lower()
    if "supported" in result:
        return "supported"
    elif "contradicted" in result:
        return "contradicted"
    return "unclear"


def eval_file(path: Path, verbose: bool = False, dry_run: bool = False) -> dict | None:
    """Evaluate a single file for factual precision."""
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return None

    if len(text.strip()) < 100:
        return None

    if verbose:
        print(f"\n  Decomposing: {path.name}")

    if dry_run:
        print(f"    [dry-run] Would decompose {len(text)} chars")
        return None

    claims = decompose_claims(text)

    if verbose:
        print(f"    Found {len(claims)} verifiable claims")

    if not claims:
        return {"file": str(path), "claims": 0, "results": {}}

    results = {"supported": 0, "contradicted": 0, "unclear": 0}
    claim_details = []

    for claim in claims[:20]:  # Cap at 20 claims per file
        if verbose:
            print(f"    Checking: {claim[:70]}...")

        evidence = search_claim(claim)
        judgment = judge_claim(claim, evidence)
        results[judgment] += 1

        claim_details.append({
            "claim": claim,
            "judgment": judgment,
            "evidence_count": len(evidence),
        })

        if verbose:
            print(f"      → {judgment} ({len(evidence)} sources)")

    total_judged = results["supported"] + results["contradicted"]
    precision = results["supported"] / total_judged if total_judged > 0 else None

    return {
        "file": str(path),
        "claims": len(claims),
        "checked": len(claim_details),
        "supported": results["supported"],
        "contradicted": results["contradicted"],
        "unclear": results["unclear"],
        "precision": precision,
        "details": claim_details,
    }


def main():
    project = "meta"
    n = 5
    verbose = False
    dry_run = False

    args = sys.argv[1:]
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project = args[idx + 1]
    if "--n" in args:
        idx = args.index("--n")
        if idx + 1 < len(args):
            n = int(args[idx + 1])
    if "--verbose" in args:
        verbose = True
    if "--dry-run" in args:
        dry_run = True

    if project not in PROJECT_ROOTS:
        print(f"Unknown project: {project}")
        print(f"Valid: {', '.join(PROJECT_ROOTS.keys())}")
        return

    print(f"{'=' * 55}")
    print(f"  SAFE-lite Eval — {project}")
    print(f"{'=' * 55}")
    print()

    files = find_recent_research_files(project, n)
    if not files:
        print(f"  No research files found in {project}.")
        return

    print(f"  Evaluating {len(files)} files:")
    for f in files:
        print(f"    {f.name}")
    print()

    if dry_run:
        print("  [dry-run mode — no API calls]")
        for f in files:
            eval_file(f, verbose=verbose, dry_run=True)
        return

    file_results = []
    for path in files:
        result = eval_file(path, verbose=verbose)
        if result and result["claims"] > 0:
            file_results.append(result)

    if not file_results:
        print("  No verifiable claims found.")
        return

    # Aggregate
    total_supported = sum(r["supported"] for r in file_results)
    total_contradicted = sum(r["contradicted"] for r in file_results)
    total_unclear = sum(r["unclear"] for r in file_results)
    total_judged = total_supported + total_contradicted
    overall_precision = total_supported / total_judged if total_judged > 0 else None

    print()
    print(f"  {'=' * 45}")
    print("  Results:")
    print(f"  {'=' * 45}")
    print(f"  Files evaluated:    {len(file_results)}")
    print(f"  Total claims:       {sum(r['claims'] for r in file_results)}")
    print(f"  Claims checked:     {sum(r['checked'] for r in file_results)}")
    print(f"  Supported:          {total_supported}")
    print(f"  Contradicted:       {total_contradicted}")
    print(f"  Unclear:            {total_unclear}")
    if overall_precision is not None:
        print(f"  Factual precision:  {overall_precision:.1%}")
    else:
        print("  Factual precision:  N/A (no judged claims)")
    print()

    # Per-file breakdown
    print("  Per file:")
    for r in file_results:
        fname = Path(r["file"]).name
        p = f"{r['precision']:.0%}" if r["precision"] is not None else "N/A"
        print(f"    {fname:<40} {r['checked']:>2} claims  {p} precision")
    print()

    # Log metrics
    metric = {
        "ts": datetime.now().isoformat(),
        "metric": "safe_lite_eval",
        "project": project,
        "files_evaluated": len(file_results),
        "total_claims": sum(r["claims"] for r in file_results),
        "claims_checked": sum(r["checked"] for r in file_results),
        "supported": total_supported,
        "contradicted": total_contradicted,
        "unclear": total_unclear,
        "factual_precision": round(overall_precision, 4) if overall_precision is not None else None,
    }
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metric) + "\n")
    print(f"  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
