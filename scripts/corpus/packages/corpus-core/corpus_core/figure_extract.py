"""On-demand figure-DATA extraction → `figure_extraction` annotations.

Marker saves figure crops (`_page_N_Figure_M.jpeg`) and the caption (text layer),
but it does NOT read a chart's plotted DATA or a diagram's relations. This module
runs a vision model over a source's figure crops and records the extracted,
type-dispatched representation as a `figure_extraction` annotation (output_uri
sidecar), so figures become first-class, claim-extractable evidence.

It is ON-DEMAND — the orchestrator invokes it for critical papers, NOT a default
re-parse of the whole corpus (vision calls cost; most figures never get read).

Representation is dispatched on figure type (operator design 2026-06-01):
    data_chart  → markdown table (the plotted data; lossless, claim-extractable)
    diagram     → node →edge→ node list (relational; a table would force-fit)
    image_only  → caption + description (micrograph/gel/photo: no extractable data)
    other       → caption + notes
ALWAYS a one-line caption — the cheap relevance signal the read-loop surfaces
(deep representation in the payload; simple inference reads the caption first).

The figure extraction rides the existing annotation primitive: content-addressed,
append-only, attributable (which model read it), replayable, and surfaced by
`active_annotations_for_source` with zero new read-path wiring.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel

from . import store
from .annotate import annotate
from .identity import sha256_hex

DEFAULT_VISION_MODEL = "gemini-3-flash-preview"
FIGURE_SCOPE = "figure_extraction"
FIGURE_ACTOR = f"urn:agent:model:{DEFAULT_VISION_MODEL}"

# marker names figure crops `_page_<n>_Figure_<m>.jpeg`; `_Picture_` crops are
# logos/headshots/icons (skip them — not data-bearing figures).
_FIGURE_CROP = re.compile(r"_Figure_\d+\.(jpe?g|png)$", re.IGNORECASE)


# --- structured vision output (type-dispatched) ---------------------------


class FigureTable(BaseModel):
    columns: list[str]
    rows: list[list[str]]


class FigureRelation(BaseModel):
    src: str
    edge: str
    dst: str


class FigureExtraction(BaseModel):
    """One figure's extracted content. `table` is populated only for data_chart,
    `relations` only for diagram; both null for image_only/other."""

    figure_type: Literal["data_chart", "diagram", "image_only", "other"]
    caption: str
    table: Optional[FigureTable]
    relations: Optional[list[FigureRelation]]
    notes: Optional[str]


_PROMPT = (
    "You extract structured content from a single scientific figure image, faithfully.\n"
    "- Classify figure_type: data_chart (bar/line/scatter/box), diagram "
    "(pathway/flowchart/schematic with parts and relations), image_only "
    "(micrograph/gel/blot/photo with no extractable data), or other.\n"
    "- ALWAYS write a one-line `caption` stating what the figure shows.\n"
    "- data_chart: fill `table` with the plotted data. Read PRINTED value labels "
    "exactly. If a series has no printed labels, estimate from the axis and say "
    "'estimated from axis' in `notes`. Do not invent precision. Leave `relations` null.\n"
    "- diagram: fill `relations` with (src, edge, dst) triples capturing the arrows/"
    "relationships shown. Leave `table` null.\n"
    "- image_only/other: leave `table` and `relations` null; describe what is shown "
    "in `notes`.\n"
    "Never fabricate numbers or relationships not present in the image."
)


def _client():
    try:
        from google import genai
    except ImportError as e:  # pragma: no cover - environment guard
        raise RuntimeError(
            "figure_extract requires google-genai (install the 'llm-fallback' extra)"
        ) from e
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set; figure extraction needs the Gemini API")
    return genai.Client(api_key=key)


def _mime_for(path_or_name: str) -> str:
    return "image/png" if path_or_name.lower().endswith(".png") else "image/jpeg"


def extract_figure(
    image_bytes: bytes,
    *,
    mime_type: str = "image/jpeg",
    caption_hint: str | None = None,
    model: str = DEFAULT_VISION_MODEL,
) -> FigureExtraction:
    """Run the vision model over one figure crop → a typed FigureExtraction.

    `caption_hint` (the document's printed caption, if known) improves typing and
    labeling but is not required.
    """
    from google.genai import types

    client = _client()
    prompt = _PROMPT
    if caption_hint:
        prompt = f"{_PROMPT}\n\nThe document's printed caption for this figure is:\n{caption_hint}"
    r = client.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FigureExtraction,
        ),
    )
    if getattr(r, "parsed", None) is not None:
        return r.parsed  # type: ignore[return-value]
    return FigureExtraction(**json.loads(r.text))


# --- rendering (type-dispatched markdown) ---------------------------------


def render_markdown(ext: FigureExtraction) -> str:
    """Render an extraction to the sidecar markdown the consumer reads.

    data_chart → markdown table; diagram → node→edge list; else caption+notes.
    The first line is a machine-readable type marker; the caption is bold so an
    agent skimming gets the gist before parsing the payload.
    """
    lines = [f"<!-- figure_type={ext.figure_type} -->", f"**{ext.caption}**", ""]
    if ext.figure_type == "data_chart" and ext.table and ext.table.columns:
        cols = ext.table.columns
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join("---" for _ in cols) + " |")
        for row in ext.table.rows:
            cells = [str(c) for c in row]
            cells = (cells + [""] * len(cols))[: len(cols)]  # pad/truncate to width
            lines.append("| " + " | ".join(cells) + " |")
    elif ext.figure_type == "diagram" and ext.relations:
        for rel in ext.relations:
            lines.append(f"- {rel.src} —{rel.edge}→ {rel.dst}")
    if ext.notes:
        lines += ["", f"_{ext.notes}_"]
    return "\n".join(lines).rstrip() + "\n"


# --- crop discovery + source-level extraction -----------------------------


def iter_figure_crops(record: store.PaperRecord) -> list[Path]:
    """Figure crops in the source's ACTIVE parse (skips `_Picture_` logos)."""
    active = record.parsed_dir_active()
    if active is None:
        return []
    return sorted(p for p in active.iterdir() if _FIGURE_CROP.search(p.name))


def extract_source_figures(
    source_id: str,
    *,
    actor_id: str = FIGURE_ACTOR,
    model: str = DEFAULT_VISION_MODEL,
    write: bool = True,
) -> list[dict[str, Any]]:
    """Extract every figure crop in a source's active parse → figure_extraction
    annotations (sidecar at `<source>/figures/<crop_stem>.md`).

    On-demand: the orchestrator calls this for a critical paper. Returns a summary
    per crop. Idempotent on identical extraction output (same output_hash → the
    annotation write no-ops). A materially different re-extraction appends a new
    attestation (append-only); superseding the prior is a future refinement.
    """
    rec = store.get(source_id)
    crops = iter_figure_crops(rec)
    figdir = rec.path / "figures"
    out: list[dict[str, Any]] = []
    for crop in crops:
        img = crop.read_bytes()
        ext = extract_figure(img, mime_type=_mime_for(crop.name), model=model)
        md = render_markdown(ext)
        stem = crop.stem
        out_uri = f"corpus://{source_id}/figures/{stem}.md"
        out_hash = sha256_hex(md)
        ann_id = None
        if write:
            figdir.mkdir(parents=True, exist_ok=True)
            (figdir / f"{stem}.md").write_text(md, encoding="utf-8")
            ann_id = annotate(
                source_id,
                repo="agent-infra",
                actor_type="model",
                actor_id=actor_id,
                scope=FIGURE_SCOPE,
                output_uri=out_uri,
                output_hash=out_hash,
                source_content_hash=sha256_hex(img),  # pin to THIS crop
                tool=model,
            )
        out.append(
            {
                "crop": crop.name,
                "figure_type": ext.figure_type,
                "caption": ext.caption,
                "output_uri": out_uri,
                "annotation_id": ann_id,
            }
        )
    return out


# --- CLI: `corpus figures <source_id>` ------------------------------------


def add_cli(subparsers) -> None:
    p = subparsers.add_parser(
        "figures",
        help="On-demand: extract figure DATA from a source's crops → figure_extraction annotations",
    )
    p.add_argument("source_id", help="canonical corpus source_id (doi_…, pmid_…, sha_…)")
    p.add_argument("--model", default=DEFAULT_VISION_MODEL, help="vision model (default: %(default)s)")
    p.add_argument("--no-write", action="store_true",
                   help="extract + print only; do NOT write sidecars or annotations")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p.set_defaults(func=_run)


def _run(args) -> int:
    results = extract_source_figures(
        args.source_id, model=args.model, write=not args.no_write
    )
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    if not results:
        print(f"  no figure crops in active parse of {args.source_id}")
        return 0
    for r in results:
        tag = r["annotation_id"] or ("(dry-run)" if args.no_write else "(no write)")
        print(f"  ✓ {r['crop']:28} {r['figure_type']:11} {tag}")
        print(f"      {r['caption']}")
    print(f"  {len(results)} figure(s) → scope=figure_extraction")
    return 0
