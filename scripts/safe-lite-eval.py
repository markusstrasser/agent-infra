#!/usr/bin/env python3
"""SAFE-lite Eval — factual precision measurement.

Implements a simplified version of the SAFE (Search-Augmented Factual Evaluation)
methodology from Google DeepMind (NeurIPS 2024). Decomposes research outputs into
atomic claims, verifies each via web search, and judges support.

Default backend: Exa /answer (single-call structured verification).
Legacy backend: Exa search + Claude Haiku judge (2-step, higher cost).

Usage: uv run python3 scripts/safe-lite-eval.py [--project meta] [--n 5]
                                                 [--verbose] [--dry-run]
                                                 [--no-cache] [--legacy]
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from config import METRICS_FILE, PROJECT_ROOTS, RESEARCH_DIRS

# Per-claim JSONL log for detailed analysis
CLAIM_LOG = Path.home() / ".claude" / "safe-lite-claims.jsonl"


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


# --- Exa /answer backend (default) ---

def _get_exa_client():
    """Get Exa client. Returns None if no API key available."""
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        for mcp_path in [
            Path.home() / "Projects" / "meta" / ".mcp.json",
            Path.home() / ".mcp.json",
        ]:
            if mcp_path.exists():
                try:
                    with open(mcp_path) as f:
                        config = json.load(f)
                    for server in config.get("mcpServers", {}).values():
                        url = server.get("url", "")
                        if "exaApiKey=" in url:
                            api_key = url.split("exaApiKey=")[1].split("&")[0]
                            break
                except (json.JSONDecodeError, OSError):
                    continue
            if api_key:
                break

    if not api_key:
        return None

    from exa_py import Exa
    return Exa(api_key=api_key)


VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["supported", "contradicted", "insufficient"],
        },
        "evidence_summary": {
            "type": "string",
        },
        "confidence": {
            "type": "number",
        },
    },
    "required": ["verdict", "evidence_summary", "confidence"],
}


def exa_answer_verify(claim: str, exa, *, no_cache: bool = False) -> dict:
    """Verify a claim via Exa /answer with structured output. Single API call."""
    start = time.monotonic()
    try:
        response = exa.answer(
            f"Is this claim true or false? Evaluate the evidence: {claim}",
            text=True,
            output_schema=VERIFICATION_SCHEMA,
        )
    except Exception as e:
        return {
            "judgment": "insufficient",
            "evidence_count": 0,
            "cost_dollars": None,
            "latency_ms": round((time.monotonic() - start) * 1000),
            "schema_valid": False,
            "error": str(e),
        }
    latency_ms = round((time.monotonic() - start) * 1000)

    answer = response.answer
    if isinstance(answer, dict):
        verdict = answer.get("verdict", "insufficient")
        schema_valid = True
    elif isinstance(answer, str):
        verdict = "insufficient"
        schema_valid = False
    else:
        verdict = "insufficient"
        schema_valid = False

    # Normalize verdict to match legacy labels
    if verdict == "supported":
        judgment = "supported"
    elif verdict == "contradicted":
        judgment = "contradicted"
    else:
        judgment = "unclear"  # "insufficient" → "unclear" for backward compat

    cost_dollars = None
    if response.cost_dollars:
        cost_dollars = response.cost_dollars.total

    return {
        "judgment": judgment,
        "evidence_count": len(response.citations or []),
        "cost_dollars": cost_dollars,
        "latency_ms": latency_ms,
        "schema_valid": schema_valid,
    }


# --- Legacy backend (search + judge) ---

def search_claim(claim: str, exa) -> list[dict]:
    """Search for evidence about a claim using Exa search_and_contents."""
    try:
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


def legacy_verify(claim: str, exa) -> dict:
    """Legacy 2-step verification: Exa search + Claude Haiku judge."""
    start = time.monotonic()
    evidence = search_claim(claim, exa)
    judgment = judge_claim(claim, evidence)
    latency_ms = round((time.monotonic() - start) * 1000)
    return {
        "judgment": judgment,
        "evidence_count": len(evidence),
        "cost_dollars": None,  # Can't track across Exa search + Anthropic
        "latency_ms": latency_ms,
        "schema_valid": None,
    }


# --- Eval logic ---

def eval_file(
    path: Path,
    exa,
    *,
    verbose: bool = False,
    dry_run: bool = False,
    legacy: bool = False,
    no_cache: bool = False,
    project: str = "",
) -> dict | None:
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
    total_cost = 0.0
    total_latency = 0

    for claim in claims[:20]:  # Cap at 20 claims per file
        if verbose:
            print(f"    Checking: {claim[:70]}...")

        if legacy:
            result = legacy_verify(claim, exa)
        else:
            result = exa_answer_verify(claim, exa, no_cache=no_cache)

        judgment = result["judgment"]
        results[judgment] += 1

        if result.get("cost_dollars"):
            total_cost += result["cost_dollars"]
        total_latency += result.get("latency_ms", 0)

        detail = {
            "claim": claim,
            "judgment": judgment,
            "evidence_count": result["evidence_count"],
        }
        if result.get("cost_dollars"):
            detail["cost_dollars"] = result["cost_dollars"]
        if result.get("latency_ms"):
            detail["latency_ms"] = result["latency_ms"]
        if result.get("schema_valid") is not None:
            detail["schema_valid"] = result["schema_valid"]

        claim_details.append(detail)

        # Per-claim JSONL log
        claim_log_entry = {
            "ts": datetime.now().isoformat(),
            "project": project,
            "file": path.name,
            "backend": "legacy" if legacy else "exa_answer",
            **detail,
        }
        try:
            with open(CLAIM_LOG, "a") as f:
                f.write(json.dumps(claim_log_entry) + "\n")
        except OSError:
            pass

        if verbose:
            cost_str = f" ${result['cost_dollars']:.4f}" if result.get("cost_dollars") else ""
            latency_str = f" {result['latency_ms']}ms" if result.get("latency_ms") else ""
            schema_str = ""
            if result.get("schema_valid") is not None:
                schema_str = " schema:ok" if result["schema_valid"] else " schema:FAIL"
            print(f"      → {judgment} ({result['evidence_count']} sources{cost_str}{latency_str}{schema_str})")

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
        "total_cost": total_cost,
        "total_latency_ms": total_latency,
        "details": claim_details,
    }


def main():
    project = "meta"
    n = 5
    verbose = False
    dry_run = False
    legacy = False
    no_cache = False

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
    if "--legacy" in args:
        legacy = True
    if "--no-cache" in args:
        no_cache = True

    if project not in PROJECT_ROOTS:
        print(f"Unknown project: {project}")
        print(f"Valid: {', '.join(PROJECT_ROOTS.keys())}")
        return

    backend_label = "legacy (search+judge)" if legacy else "exa /answer"
    print(f"{'=' * 55}")
    print(f"  SAFE-lite Eval — {project} [{backend_label}]")
    print(f"{'=' * 55}")
    if no_cache:
        print("  [no-cache mode — fresh API calls]")
    print()

    exa = _get_exa_client()
    if exa is None:
        print("  ERROR: No Exa API key found. Set EXA_API_KEY or configure .mcp.json.")
        return

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
            eval_file(f, exa, verbose=verbose, dry_run=True)
        return

    file_results = []
    for path in files:
        result = eval_file(
            path, exa,
            verbose=verbose,
            legacy=legacy,
            no_cache=no_cache,
            project=project,
        )
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
    total_cost = sum(r.get("total_cost", 0) for r in file_results)
    total_latency = sum(r.get("total_latency_ms", 0) for r in file_results)
    total_claims_checked = sum(r["checked"] for r in file_results)

    print()
    print(f"  {'=' * 45}")
    print("  Results:")
    print(f"  {'=' * 45}")
    print(f"  Backend:            {backend_label}")
    print(f"  Files evaluated:    {len(file_results)}")
    print(f"  Total claims:       {sum(r['claims'] for r in file_results)}")
    print(f"  Claims checked:     {total_claims_checked}")
    print(f"  Supported:          {total_supported}")
    print(f"  Contradicted:       {total_contradicted}")
    print(f"  Unclear:            {total_unclear}")
    if overall_precision is not None:
        print(f"  Factual precision:  {overall_precision:.1%}")
    else:
        print("  Factual precision:  N/A (no judged claims)")
    if total_cost > 0:
        print(f"  Total cost:         ${total_cost:.4f}")
        if total_claims_checked:
            print(f"  Cost/claim:         ${total_cost / total_claims_checked:.4f}")
    if total_latency > 0 and total_claims_checked:
        print(f"  Avg latency/claim:  {total_latency // total_claims_checked}ms")
    print()

    # Per-file breakdown
    print("  Per file:")
    for r in file_results:
        fname = Path(r["file"]).name
        p = f"{r['precision']:.0%}" if r["precision"] is not None else "N/A"
        print(f"    {fname:<40} {r['checked']:>2} claims  {p} precision")
    print()

    # Schema compliance (exa /answer only)
    if not legacy:
        all_details = [d for r in file_results for d in r["details"]]
        schema_ok = sum(1 for d in all_details if d.get("schema_valid") is True)
        schema_fail = sum(1 for d in all_details if d.get("schema_valid") is False)
        if schema_ok + schema_fail > 0:
            pct = schema_ok / (schema_ok + schema_fail)
            print(f"  Schema compliance:  {pct:.0%} ({schema_ok}/{schema_ok + schema_fail})")
            print()

    # Log metrics
    metric = {
        "ts": datetime.now().isoformat(),
        "metric": "safe_lite_eval",
        "project": project,
        "backend": "legacy" if legacy else "exa_answer",
        "no_cache": no_cache,
        "files_evaluated": len(file_results),
        "total_claims": sum(r["claims"] for r in file_results),
        "claims_checked": total_claims_checked,
        "supported": total_supported,
        "contradicted": total_contradicted,
        "unclear": total_unclear,
        "factual_precision": round(overall_precision, 4) if overall_precision is not None else None,
        "total_cost": round(total_cost, 6) if total_cost > 0 else None,
        "avg_latency_ms": total_latency // total_claims_checked if total_claims_checked else None,
    }
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metric) + "\n")
    print(f"  Logged to {METRICS_FILE}")
    if CLAIM_LOG.exists():
        print(f"  Per-claim log: {CLAIM_LOG}")


if __name__ == "__main__":
    main()
