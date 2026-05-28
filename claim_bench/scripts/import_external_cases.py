#!/usr/bin/env python3
"""Import public-benchmark gold cases from ~/Projects/evals into claim_bench/cases/.

Fixes the n=8 underpowering exposed by the 2026-05-28 Opus 4.8/4.7 A/B (rankings
flipped on 1 case → no statistical power). Source: evals/data/processed/
selected_cases_v0.jsonl (26 seeds from 7 public datasets).

The hard part is label normalization: the 26 seeds carry RAW per-dataset labels
(13 distinct schemas). We map ONLY where the mapping is unambiguous and the task
is genuinely 5-class claim verification. Anything unmapped is SKIPPED AND LOGGED
— never silently coerced (a wrong gold label is worse than a missing case; cf.
case 006 fooling both models in the A/B).

Run:  cd ~/Projects/agent-infra/claim_bench && uv run python3 scripts/import_external_cases.py
      (add --write to actually write files; default is dry-run report)
"""
import json, sys, re
from pathlib import Path

SRC = Path.home() / "Projects/evals/data/processed/selected_cases_v0.jsonl"
OUT = Path(__file__).resolve().parent.parent / "cases"
WRITE = "--write" in sys.argv

# (source_dataset, lowercased_stripped_gold_verdict) -> claim_bench 5-class verdict.
# Only unambiguous, claim-verification-appropriate mappings. Documented per dataset.
LABEL_MAP = {
    # AVeriTeC (Schlichtkrull et al. 2023): 4-way veracity over real fact-checks.
    ("AVeriTeC", "refuted"): "contradicted",
    ("AVeriTeC", "supported"): "supported",
    ("AVeriTeC", "conflicting evidence/cherrypicking"): "mixed",
    ("AVeriTeC", "not enough evidence"): "insufficient_evidence",
    # ClaimDB: DB-query claims; labels already align with our enum.
    ("ClaimDB", "supported"): "supported",
    ("ClaimDB", "entailed"): "supported",  # DB evidence entails the claim
    ("ClaimDB", "contradicted"): "contradicted",
    ("ClaimDB", "not enough info"): "insufficient_evidence",
    # HoVer (Jiang et al. 2020): multi-hop Wikipedia, binary by construction.
    ("HoVer", "supported"): "supported",
    ("HoVer", "not_supported"): "contradicted",
    # MSVEC: scientific-misinformation veracity.
    ("MSVEC", "true"): "supported",
    ("MSVEC", "false"): "contradicted",
    # SoMe misinformation: gold = veracity of the claim itself.
    ("SoMe:misinformation_detection", "true"): "supported",
    ("SoMe:misinformation_detection", "false"): "contradicted",
}
# Datasets whose task is NOT 5-class claim verification → exclude wholesale.
EXCLUDE_DATASETS = {"DeepSearchQA"}  # gold = "answer_set" (deep-research QA, not a verdict)

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:24]

rows = [json.loads(l) for l in open(SRC)]
mapped, excluded, unmapped = [], [], []
seen_ids = set()
for i, r in enumerate(rows):
    ds = r["source_dataset"]
    raw = str(r.get("gold_verdict", "")).strip()
    key = (ds, raw.lower())
    if ds in EXCLUDE_DATASETS:
        excluded.append((ds, raw, r["claim"][:60])); continue
    if key not in LABEL_MAP:
        unmapped.append((ds, raw, r["claim"][:60])); continue
    verdict = LABEL_MAP[key]
    tid = f"ext_{slug(ds)}_{i:02d}"
    while tid in seen_ids:
        tid += "x"
    seen_ids.add(tid)
    raw_ref = r.get("raw_ref")
    gold_sources = []
    if isinstance(raw_ref, str) and raw_ref.startswith("http"):
        gold_sources = [raw_ref]
    elif isinstance(raw_ref, list):
        gold_sources = [x for x in raw_ref if isinstance(x, str)]
    mapped.append({
        "task_id": tid,
        "claim_text": r["claim"],
        "domain": ds,
        "claim_type": "imported",
        "verifiability": "verifiable" if verdict != "not_verifiable" else "not_verifiable",
        "gold_verdict": verdict,
        "gold_sources": gold_sources,
        "gold_contradict_sources": [],
        "distractor_sources": [],
        "difficulty": "unknown",
        "notes": f"Imported from {ds} (raw label {raw!r}). "
                 f"evidence_summary: {str(r.get('evidence_summary',''))[:200]}",
    })

# ---- report ----
from collections import Counter
print(f"source: {SRC}  ({len(rows)} seeds)")
print(f"\nMAPPED: {len(mapped)}")
print("  verdict dist:", dict(Counter(m['gold_verdict'] for m in mapped)))
print("  by dataset:  ", dict(Counter(m['domain'] for m in mapped)))
print(f"\nEXCLUDED (non-verdict task): {len(excluded)}")
for ds, raw, c in excluded: print(f"  [{ds}] {raw!r}  {c!r}")
print(f"\nUNMAPPED (ambiguous label, skipped not guessed): {len(unmapped)}")
for ds, raw, c in unmapped: print(f"  [{ds}] {raw!r}  {c!r}")

if WRITE:
    n = 0
    for m in mapped:
        p = OUT / f"{m['task_id']}.json"
        p.write_text(json.dumps(m, indent=2, ensure_ascii=False))
        n += 1
    print(f"\nWROTE {n} case files to {OUT}")
else:
    print(f"\n(dry run — pass --write to emit {len(mapped)} files to {OUT})")
