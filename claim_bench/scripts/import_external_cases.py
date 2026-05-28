#!/usr/bin/env python3
"""Import public-benchmark gold cases from ~/Projects/evals into claim_bench/cases/.

Fixes the n=8 underpowering exposed by the 2026-05-28 Opus 4.8/4.7 A/B. Pulls from
both the 26 vetted selected seeds and the 66-case candidate backlog.

Label normalization is the hard part (raw per-dataset schemas). We map ONLY where
unambiguous and the task is genuinely 5-class claim verification. Everything else
is SKIPPED AND LOGGED, never coerced (a wrong gold label is worse than a missing
case). Candidate cases are deduped against the selected set by claim text.

Run:  cd ~/Projects/agent-infra/claim_bench && uv run python3 scripts/import_external_cases.py [--write]
"""
import json, sys, re
from pathlib import Path

EVALS = Path.home() / "Projects/evals/data/processed"
SOURCES = [  # (file, task_id_prefix)
    (EVALS / "selected_cases_v0.jsonl", "ext"),
    (EVALS / "candidate_cases.jsonl", "extc"),
]
OUT = Path(__file__).resolve().parent.parent / "cases"
WRITE = "--write" in sys.argv

# (source_dataset, lowercased gold_verdict) -> claim_bench 5-class verdict.
LABEL_MAP = {
    ("AVeriTeC", "refuted"): "contradicted", ("AVeriTeC", "supported"): "supported",
    ("AVeriTeC", "conflicting evidence/cherrypicking"): "mixed",
    ("AVeriTeC", "not enough evidence"): "insufficient_evidence",
    ("ClaimDB", "supported"): "supported", ("ClaimDB", "entailed"): "supported",
    ("ClaimDB", "contradicted"): "contradicted", ("ClaimDB", "not enough info"): "insufficient_evidence",
    ("HoVer", "supported"): "supported", ("HoVer", "not_supported"): "contradicted",
    ("MSVEC", "true"): "supported", ("MSVEC", "false"): "contradicted",
    ("SoMe:misinformation_detection", "true"): "supported",
    ("SoMe:misinformation_detection", "false"): "contradicted",
    # SciFact (Wadden et al. 2020): scientific-claim verification.
    ("SciFact", "supported"): "supported", ("SciFact", "support"): "supported",
    ("SciFact", "contradicted"): "contradicted", ("SciFact", "refuted"): "contradicted",
    ("SciFact", "contradict"): "contradicted",
    ("SciFact", "not enough info"): "insufficient_evidence", ("SciFact", "noinfo"): "insufficient_evidence",
}
# Datasets whose task is NOT 5-class web-retrieval claim verification -> exclude.
#  DeepSearchQA: gold = answer_set (deep-research QA, not a verdict).
#  ClaimDB: BIRD text-to-SQL claims tied to a PRIVATE database (bird_id); gold
#    verdicts are relative to a SQL DB the retrieval harness can't access, so the
#    model correctly abstains but is scored wrong. Audit 2026-05-28 — removed.
#  HoVer/MSVEC/SoMe: removed after a cross-model (Gemini) audit 2026-05-28 —
#    HoVer = synthetic multi-hop trivia templates, UNFIT and at least one wrong
#    gold (hover_08: "Cunningham won more Pulitzers than Plath" labeled supported,
#    both won exactly 1 → contradicted); MSVEC = mojibake-corrupted + question/
#    paragraph framings, not clean claims; SoMe = weak, non-self-contained
#    ("this year" without a date). Only AVeriTeC (professionally adjudicated
#    fact-checks) survives import; the rest of the corpus is hand-built/authored.
EXCLUDE_DATASETS = {"DeepSearchQA", "ClaimDB", "HoVer", "MSVEC", "SoMe:misinformation_detection"}
EXCLUDE_DATASET_PREFIXES = ("Web-Bench",)  # browsecomp/gaia/seal/webwalker — gold is an `answer`

# Specific AVeriTeC cases dropped after the GPT-5.5 cross-model audit (2026-05-28):
#  - "Nigeria performed poorly in SDGs": BOTH Gemini and GPT flag "performed
#    poorly" as vague/evaluative without a defined metric (mislabeled vs supported).
#  - Georgia COVID stats: unclosed quotation + date-dependent counts -> brittle gold.
SKIP_CLAIM_SUBSTRINGS = ("Nigeria performed poorly", "almost 100,000 more COVID-19 cases")

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:20]
def norm_claim(s): return re.sub(r"\s+", " ", (s or "").strip().lower())[:200]

mapped, excluded, unmapped = [], [], []
seen_ids, seen_claims = set(), set()

for path, prefix in SOURCES:
    if not path.exists():
        print(f"!! missing {path}"); continue
    for i, r in enumerate(json.loads(l) for l in open(path)):
        ds = r.get("source_dataset") or "unknown"
        raw = str(r.get("gold_verdict", "")).strip()
        claim = r.get("claim", "")
        nc = norm_claim(claim)
        if ds in EXCLUDE_DATASETS or ds.startswith(EXCLUDE_DATASET_PREFIXES):
            excluded.append((prefix, ds, raw, claim[:55])); continue
        if any(sub in claim for sub in SKIP_CLAIM_SUBSTRINGS):
            excluded.append((prefix, ds, raw, claim[:55])); continue
        if (ds, raw.lower()) not in LABEL_MAP:
            unmapped.append((prefix, ds, raw, claim[:55])); continue
        if nc in seen_claims:   # dedup candidate vs selected
            continue
        seen_claims.add(nc)
        verdict = LABEL_MAP[(ds, raw.lower())]
        tid = f"{prefix}_{slug(ds)}_{i:02d}"
        while tid in seen_ids: tid += "x"
        seen_ids.add(tid)
        rr = r.get("raw_ref")
        gold_sources = [rr] if isinstance(rr, str) and rr.startswith("http") else (
            [x for x in rr if isinstance(x, str)] if isinstance(rr, list) else [])
        mapped.append({
            "task_id": tid, "claim_text": claim, "domain": ds, "claim_type": "imported",
            "verifiability": "verifiable", "gold_verdict": verdict,
            "gold_sources": gold_sources, "gold_contradict_sources": [], "distractor_sources": [],
            "difficulty": "unknown",
            "notes": f"Imported from {ds} ({prefix}, raw label {raw!r}). "
                     f"evidence_summary: {str(r.get('evidence_summary',''))[:180]}",
        })

from collections import Counter
print(f"MAPPED: {len(mapped)}")
print("  verdict dist:", dict(Counter(m['gold_verdict'] for m in mapped)))
print("  by dataset:  ", dict(Counter(m['domain'] for m in mapped)))
print(f"\nEXCLUDED (non-verdict task): {len(excluded)}  (datasets: {dict(Counter(e[1] for e in excluded))})")
print(f"UNMAPPED (ambiguous label, skipped not guessed): {len(unmapped)}  (labels: {dict(Counter((e[1],e[2]) for e in unmapped))})")

if WRITE:
    # clear prior ext_/extc_ imports so re-runs are idempotent
    for old in list(OUT.glob("ext_*.json")) + list(OUT.glob("extc_*.json")):
        old.unlink()
    for m in mapped:
        (OUT / f"{m['task_id']}.json").write_text(json.dumps(m, indent=2, ensure_ascii=False))
    print(f"\nWROTE {len(mapped)} files to {OUT}")
else:
    print(f"\n(dry run — pass --write to emit {len(mapped)} files)")
