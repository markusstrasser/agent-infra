"""Tests for scripts/pointer_disposition.py + URL normalize shared with the hook."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from pointer_disposition import (  # noqa: E402
    extract_urls,
    format_triage,
    lookup,
    lookup_many,
    normalize_url,
    record,
    url_id,
)


def test_normalize_collapses_github_blob():
    blob = (
        "https://github.com/agno-agi/agno/blob/main/cookbook/"
        "data_labeling/_05_text_pairwise_preference/dpo_jury.py"
    )
    raw = (
        "https://raw.githubusercontent.com/agno-agi/agno/main/cookbook/"
        "data_labeling/_05_text_pairwise_preference/dpo_jury.py"
    )
    assert normalize_url(blob) == normalize_url(raw)
    assert normalize_url(blob).endswith("dpo_jury.py")
    assert "/blob/" not in normalize_url(blob)


def test_ledger_hit_agno(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pointer_disposition.LEDGER",
        REPO / "artifacts" / "pointer-dispositions" / "ledger.jsonl",
    )
    monkeypatch.setattr(
        "pointer_disposition.OUT_DIR",
        REPO / "artifacts" / "pointer-dispositions",
    )
    blob = (
        "https://github.com/agno-agi/agno/blob/main/cookbook/"
        "data_labeling/_05_text_pairwise_preference/dpo_jury.py"
    )
    row = lookup(blob)
    assert row is not None
    assert row["disposition"] == "doesnt_apply"
    assert "oracle" in row["reason"].lower() or "exact" in row["reason"].lower()


def test_pending_for_unknown():
    rows = lookup_many(["https://example.com/never-seen-pointer-xyz"])
    assert rows[0]["disposition"] == "pending"


def test_record_roundtrip(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr("pointer_disposition.LEDGER", ledger)
    monkeypatch.setattr("pointer_disposition.OUT_DIR", tmp_path)
    url = "https://github.com/acme/demo/blob/main/foo.py"
    row = record(url, "tried", "ran probe, null result on held-out", project="arc-agi")
    assert row["id"] == url_id(url)
    assert lookup(url)["disposition"] == "tried"


def test_format_triage_vocab():
    text = format_triage([{
        "url": "https://example.com/x",
        "disposition": "doesnt_apply",
        "reason": "wrong substrate",
        "threads": ["t1"],
    }])
    assert "[doesnt_apply]" in text
    assert "known" in text and "adopted" in text


def test_extract_urls_from_prompt():
    prompt = (
        "https://github.com/agno-agi/agno/blob/main/cookbook/"
        "data_labeling/_05_text_pairwise_preference/dpo_jury.py\n\nThis relevant?"
    )
    urls = extract_urls(prompt)
    assert len(urls) == 1
    assert urls[0].endswith("dpo_jury.py")
