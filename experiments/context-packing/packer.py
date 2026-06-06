"""Small context-packing policy for autoresearch experiments."""

from __future__ import annotations


def pack(case: dict, budget: int = 5) -> list[str]:
    prompt = str(case.get("prompt", "")).lower()
    project = str(case.get("project", "")).lower()
    changed = " ".join(case.get("changed_paths", [])).lower()
    blob = f"{prompt} {project} {changed}"

    scored: list[tuple[int, str]] = []

    def add(score: int, item: str) -> None:
        scored.append((score, item))

    if any(term in blob for term in ("claim", "verdict", "evidence", "source", "doi", "grounded")):
        add(10, "claim-bench")
        add(8, "source-grading")
    if any(term in blob for term in ("hook", "trigger", "block", "advisory", "threshold")):
        add(10, "hook-telemetry")
        add(8, "hook-governance")
    if any(term in blob for term in ("context", "memory", "pack", "loaded", "token budget")):
        add(10, "context-budget")
        add(7, "memory-summary")
    if any(term in blob for term in ("skill", "routing", "router")):
        add(10, "skill-routing")
    if any(term in blob for term in ("autoresearch", "recursive", "rsi", "self-improvement", "eval")):
        add(9, "autoresearch")
        add(7, "locked-evals")
    if any(term in blob for term in ("intel", "workup", "ticker", "portfolio")):
        add(9, "intel-rules")
    if any(term in blob for term in ("genomics", "variant", "vcf", "clinvar")):
        add(9, "genomics-rules")

    if not scored:
        add(1, "repo-map")

    best: dict[str, int] = {}
    for score, item in scored:
        best[item] = max(score, best.get(item, 0))
    return [item for _, item in sorted((-score, item) for item, score in best.items())[:budget]]
