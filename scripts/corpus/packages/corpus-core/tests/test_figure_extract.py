"""Figure-extraction tests. The live vision call is validated empirically (manual
runs over real figures); these cover the pure logic + the storage/annotation path
with a monkeypatched extractor (no network, no API key)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_core import figure_extract as fx
from corpus_core.figure_extract import FigureExtraction, FigureRelation, FigureTable


# --- render_markdown: type-dispatched representation ---


def test_render_data_chart_is_markdown_table():
    ext = FigureExtraction(
        figure_type="data_chart", caption="Allele frequencies",
        table=FigureTable(columns=["Population", "C", "A*"],
                          rows=[["World", "73.8", "26.2"], ["African", "63.2", "36.8"]]),
        relations=None, notes="percent",
    )
    md = fx.render_markdown(ext)
    assert "<!-- figure_type=data_chart -->" in md
    assert "**Allele frequencies**" in md
    assert "| Population | C | A* |" in md
    assert "| World | 73.8 | 26.2 |" in md
    assert "| African | 63.2 | 36.8 |" in md
    assert "_percent_" in md


def test_render_diagram_is_edge_list():
    ext = FigureExtraction(
        figure_type="diagram", caption="Stress pathway", table=None,
        relations=[FigureRelation(src="CRH", edge="activates", dst="CRHR1"),
                   FigureRelation(src="CRHR1", edge="increases", dst="FAAH")],
        notes=None,
    )
    md = fx.render_markdown(ext)
    assert "- CRH —activates→ CRHR1" in md
    assert "- CRHR1 —increases→ FAAH" in md
    assert "|" not in md  # no table for a diagram


def test_render_image_only_is_caption_plus_notes():
    ext = FigureExtraction(
        figure_type="image_only", caption="Western blot", table=None,
        relations=None, notes="Band at ~55 kDa in lanes 2-4",
    )
    md = fx.render_markdown(ext)
    assert "**Western blot**" in md
    assert "Band at ~55 kDa" in md
    assert "|" not in md


def test_render_pads_short_rows_to_column_width():
    ext = FigureExtraction(
        figure_type="data_chart", caption="x",
        table=FigureTable(columns=["a", "b", "c"], rows=[["1", "2"]]),
        relations=None, notes=None,
    )
    md = fx.render_markdown(ext)
    assert "| 1 | 2 |  |" in md  # third cell padded empty, not dropped


# --- crop discovery: figures only, not logos ---


def _make_source(corpus_root: Path, source_id: str, crop_names: list[str]):
    from corpus_core import store
    parse = corpus_root / source_id / "parsed.test-parser"
    parse.mkdir(parents=True)
    for name in crop_names:
        (parse / name).write_bytes(b"\xff\xd8\xff\xe0fakejpeg")
    (corpus_root / source_id / "metadata.json").write_text("{}")
    return store.get(source_id)


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    return root


def test_iter_figure_crops_skips_pictures(corpus_root):
    rec = _make_source(corpus_root, "sha_" + "a" * 16, [
        "_page_0_Picture_1.jpeg",       # logo — skip
        "_page_2_Figure_1.jpeg",        # figure — keep
        "_page_5_Figure_2.jpeg",        # figure — keep
        "page.md",                       # not an image
    ])
    crops = fx.iter_figure_crops(rec)
    names = {c.name for c in crops}
    assert names == {"_page_2_Figure_1.jpeg", "_page_5_Figure_2.jpeg"}


# --- storage path: sidecar + figure_extraction annotation ---


def test_extract_source_figures_writes_sidecar_and_annotation(corpus_root, monkeypatch):
    source_id = "sha_" + "b" * 16
    _make_source(corpus_root, source_id, ["_page_5_Figure_2.jpeg"])

    canned = FigureExtraction(
        figure_type="data_chart", caption="Allele freqs",
        table=FigureTable(columns=["Pop", "C"], rows=[["World", "73.8"]]),
        relations=None, notes=None,
    )
    monkeypatch.setattr(fx, "extract_figure", lambda *a, **k: canned)

    out = fx.extract_source_figures(source_id)
    assert len(out) == 1
    assert out[0]["figure_type"] == "data_chart"
    assert out[0]["annotation_id"].startswith("ann_")
    assert out[0]["output_uri"] == f"corpus://{source_id}/figures/_page_5_Figure_2.md"

    # sidecar written with the rendered table
    sidecar = corpus_root / source_id / "figures" / "_page_5_Figure_2.md"
    assert sidecar.exists()
    assert "| Pop | C |" in sidecar.read_text()

    # figure_extraction annotation appended to the ledger
    lines = [json.loads(x) for x in
             (corpus_root / source_id / "annotations.jsonl").read_text().splitlines() if x.strip()]
    assert len(lines) == 1
    rec = lines[0]
    assert rec["scope"] == "figure_extraction"
    assert rec["agent"]["id"] == fx.FIGURE_ACTOR
    assert rec["result"]["uri"] == f"corpus://{source_id}/figures/_page_5_Figure_2.md"
    assert rec["source_content_hash"]  # pinned to the crop


def test_extract_source_figures_no_write_is_dry_run(corpus_root, monkeypatch):
    source_id = "sha_" + "c" * 16
    _make_source(corpus_root, source_id, ["_page_2_Figure_1.jpeg"])
    canned = FigureExtraction(figure_type="image_only", caption="x", table=None,
                              relations=None, notes=None)
    monkeypatch.setattr(fx, "extract_figure", lambda *a, **k: canned)

    out = fx.extract_source_figures(source_id, write=False)
    assert out[0]["annotation_id"] is None
    assert not (corpus_root / source_id / "figures").exists()
    assert not (corpus_root / source_id / "annotations.jsonl").exists()
