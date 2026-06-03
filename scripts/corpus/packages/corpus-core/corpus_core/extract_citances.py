"""Phase C of the graph layer — extract normalized citances per paper.

Reads:
  citation_context/{scite,openalex}_response.json    → citances_in.jsonl
  parsed.<parser_id>/page.md + references_resolved.json → citances_out.jsonl

Each row is normalized to the schema in the plan's "Citance, annotation, and
graph layer" section. Stance comes from scite when present; the optional
--enrich-cito flag uses Gemini Flash via llmx to attach finer CiTO sub-property
classifications.

Idempotent on (parsed.sha256, citation_context_event_sha256, references_resolved.sha256).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Optional

from . import store as ps
from .store import CorpusStore


CITO_BASE = "http://purl.org/spar/cito/"
STANCE_TO_CITO = {
    "supporting": f"{CITO_BASE}supports",
    "contrasting": f"{CITO_BASE}disagreesWith",
    "mentioning": f"{CITO_BASE}citesAsRelated",
}

# Match in-text bracketed/parenthesized citations. Marker renders these as
# anchor links `[[12](#page-4-0)]`; the inner `[12]` is matched directly (a
# link-collapse pre-pass was tried and empirically REDUCED recall — don't).
INLINE_CITE = re.compile(r"\[(\d+(?:[,\s\-–]\d+)*)\]")


def _norm_snippet(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _citance_id(snippet: str) -> str:
    return hashlib.sha256(_norm_snippet(snippet).encode("utf-8")).hexdigest()[:16]


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _scite_to_citances_in(scite_payload: dict, target_paper_id: str) -> list[dict]:
    """Convert a scite citation-context response into normalized citances_in rows."""
    out: list[dict] = []
    citations = scite_payload.get("citations") or scite_payload.get("data") or []
    for c in citations:
        snippet = c.get("snippet") or c.get("citation_statement") or c.get("text") or ""
        if not snippet:
            continue
        citing_doi = (c.get("citing_doi") or c.get("sourceDoi") or c.get("source") or "").lower() or None
        citing_paper_id = ps.derive_paper_id(doi=citing_doi) if citing_doi else None
        stance = (c.get("classification") or c.get("stance") or "mentioning").lower()
        if stance not in {"supporting", "contrasting", "mentioning"}:
            stance = "mentioning"
        out.append(
            {
                "citance_id": _citance_id(snippet),
                "citing_paper_id": citing_paper_id,
                "cited_paper_id": target_paper_id,
                "citing_section": c.get("section"),
                "citing_page": c.get("page"),
                "snippet": snippet,
                "context_summary": None,
                "stance_class": stance,
                "stance_cito": STANCE_TO_CITO.get(stance),
                "stance_confidence": float(c.get("confidence") or 0.0),
                "stance_source": "scite",
                "providers": ["scite"],
                "fetched_at": scite_payload.get("fetched_at"),
                "provenance_byte_range": None,
            }
        )
    return out


def _openalex_to_citances_in(openalex_payload: dict, target_paper_id: str) -> list[dict]:
    out: list[dict] = []
    works = openalex_payload.get("results") or openalex_payload.get("works") or []
    for w in works:
        citing_doi = (w.get("doi") or "").replace("https://doi.org/", "").lower() or None
        if not citing_doi:
            continue
        citing_paper_id = ps.derive_paper_id(doi=citing_doi)
        snippet = w.get("citation_context") or w.get("title") or ""
        if not snippet:
            continue
        out.append(
            {
                "citance_id": _citance_id(snippet),
                "citing_paper_id": citing_paper_id,
                "cited_paper_id": target_paper_id,
                "citing_section": None,
                "citing_page": None,
                "snippet": snippet,
                "context_summary": None,
                "stance_class": "mentioning",
                "stance_cito": None,
                "stance_confidence": 0.0,
                "stance_source": "openalex",
                "providers": ["openalex"],
                "fetched_at": openalex_payload.get("fetched_at"),
                "provenance_byte_range": None,
            }
        )
    return out


def _build_citances_out(paper_md: str, refs: dict, citing_paper_id: str) -> list[dict]:
    """Extract per-citance entries by finding inline citations and joining to references_resolved."""
    out: list[dict] = []
    ref_by_label: dict[str, dict] = {}
    for e in refs.get("entries", []):
        ref_by_label[e["ref_label"]] = e
        # Also key by bare number for "5" → "[5]"
        m = re.match(r"\[(\d+)\]", e["ref_label"])
        if m:
            ref_by_label[m.group(1)] = e

    # Walk paper.md, find inline citations, capture surrounding sentence
    sentences = re.split(r"(?<=[.!?])\s+", paper_md)
    for sentence in sentences:
        for m in INLINE_CITE.finditer(sentence):
            for label in re.split(r"[,\s\-–]+", m.group(1)):
                label = label.strip()
                if not label:
                    continue
                ref = ref_by_label.get(label) or ref_by_label.get(f"[{label}]")
                if not ref:
                    continue
                snippet = sentence.strip()
                if len(snippet) > 800:
                    snippet = snippet[:800]
                out.append(
                    {
                        "citance_id": _citance_id(snippet + "|" + label),
                        "citing_paper_id": citing_paper_id,
                        "cited_paper_id": ref.get("resolved_paper_id"),
                        "cited_reference_label": label,
                        "citing_section": None,
                        "citing_page": None,
                        "snippet": snippet,
                        "context_summary": None,
                        "stance_class": "mentioning",
                        "stance_cito": None,
                        "stance_confidence": 0.5,
                        "stance_source": "local_extraction",
                        "providers": ["local"],
                        "fetched_at": ps._now(),
                    }
                )
    return out


def extract_citances(store: CorpusStore, paper_id: str, *, enrich_cito: bool = False) -> dict:
    rec = store.get(paper_id)
    cc_dir = rec.path / "citation_context"

    # citances_in from provider payloads
    citances_in: list[dict] = []
    scite = _load_json(cc_dir / "scite_response.json")
    if scite:
        citances_in.extend(_scite_to_citances_in(scite, paper_id))
    openalex = _load_json(cc_dir / "openalex_response.json")
    if openalex:
        citances_in.extend(_openalex_to_citances_in(openalex, paper_id))

    # citances_out from parsed + references_resolved
    citances_out: list[dict] = []
    refs_path = rec.path / "references_resolved.json"
    parsed_md_path = rec.parsed_markdown_path()
    if refs_path.exists() and parsed_md_path is not None:
        refs = json.loads(refs_path.read_text())
        citances_out = _build_citances_out(
            parsed_md_path.read_text(encoding="utf-8"),
            refs,
            paper_id,
        )

    # Optional CiTO enrichment via llmx Gemini Flash (deferred — not in smoke)
    if enrich_cito:
        try:
            _enrich_with_gemini(citances_in)
            _enrich_with_gemini(citances_out)
        except Exception as exc:  # pragma: no cover
            print(f"  ! CiTO enrichment failed: {exc}", file=sys.stderr)

    # Dedupe by (citance_id, cited_paper_id)
    citances_in = _dedupe(citances_in)
    citances_out = _dedupe(citances_out)

    (rec.path / "citances_in.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in citances_in), encoding="utf-8"
    )
    (rec.path / "citances_out.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in citances_out), encoding="utf-8"
    )

    print(f"  ✓ {paper_id} citances: in={len(citances_in)} out={len(citances_out)}")
    return {"paper_id": paper_id, "citances_in": len(citances_in), "citances_out": len(citances_out)}


def _dedupe(rows: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for r in rows:
        key = (r.get("citance_id"), r.get("citing_paper_id"), r.get("cited_paper_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _enrich_with_gemini(rows: list[dict]) -> None:
    """Placeholder for CiTO sub-property classification via Gemini Flash."""
    # Real implementation would batch via llmx; left out of smoke scope.
    for r in rows:
        if r.get("stance_cito") is None and r.get("stance_class") == "mentioning":
            r["stance_cito"] = STANCE_TO_CITO["mentioning"]


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("extract-citances", help="Extract citances for a paper")
    p.add_argument("--paper-id", required=True)
    p.add_argument("--enrich-cito", action="store_true",
                   help="Use Gemini Flash to attach finer CiTO sub-property labels")
    p.set_defaults(func=lambda args: (extract_citances(args.paper_id, enrich_cito=args.enrich_cito), 0)[1])
