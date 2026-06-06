"""`corpus stats` works on an empty store + after one ingest."""
from __future__ import annotations

import json

from corpus_core import cli, ingest


def test_stats_empty(corpus_root, capsys):
    rc = cli.main(["--corpus-root", str(corpus_root), "stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "papers=0" in out


def test_stats_after_ingest(corpus_root, corpus_store, tiny_pdf, capsys):
    ingest.ingest_pdf(corpus_store, tiny_pdf, doi="10.test/smoke", skip_parse=True)
    rc = cli.main(["--corpus-root", str(corpus_root), "stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "papers=1" in out


def test_lookup_by_doi_reports_present(corpus_root, corpus_store, tiny_pdf, capsys):
    ingest.ingest_pdf(
        corpus_store,
        tiny_pdf,
        doi="10.test/lookup",
        pmid="12345678",
        title="Lookup Test",
        skip_parse=True,
    )
    capsys.readouterr()

    rc = cli.main([
        "--corpus-root", str(corpus_root),
        "lookup", "--doi", "10.test/lookup", "--json",
    ])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["present"] is True
    assert payload["source_id"] == "doi_10_test_lookup"
    assert payload["doi"] == "10.test/lookup"
    assert payload["parsed"] is False


def test_lookup_by_pmid_finds_doi_keyed_record(corpus_root, corpus_store, tiny_pdf, capsys):
    ingest.ingest_pdf(
        corpus_store,
        tiny_pdf,
        doi="10.test/pmid-fallback",
        pmid="12345678",
        skip_parse=True,
    )
    capsys.readouterr()

    rc = cli.main([
        "--corpus-root", str(corpus_root),
        "lookup", "--pmid", "12345678", "--json",
    ])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["present"] is True
    assert payload["source_id"] == "doi_10_test_pmid_fallback"


def test_lookup_missing_returns_candidate_id(corpus_root, capsys):
    rc = cli.main([
        "--corpus-root", str(corpus_root),
        "lookup", "--doi", "10.test/missing", "--json",
    ])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"present": False, "source_id": "doi_10_test_missing"}


def test_show_resolves_bare_doi(corpus_root, corpus_store, tiny_pdf, capsys):
    ingest.ingest_pdf(
        corpus_store,
        tiny_pdf,
        doi="10.1234/show-doi",
        title="Show DOI Test",
        skip_parse=True,
    )
    capsys.readouterr()

    rc = cli.main([
        "--corpus-root", str(corpus_root),
        "show", "10.1234/show-doi",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "paper_id:        doi_10_1234_show_doi" in out
    assert "title:           Show DOI Test" in out


def test_show_resolves_prefixed_pmid_to_doi_keyed_record(corpus_root, corpus_store, tiny_pdf, capsys):
    ingest.ingest_pdf(
        corpus_store,
        tiny_pdf,
        doi="10.test/show-pmid",
        pmid="12345678",
        skip_parse=True,
    )
    capsys.readouterr()

    rc = cli.main([
        "--corpus-root", str(corpus_root),
        "show", "pmid:12345678",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "paper_id:        doi_10_test_show_pmid" in out
    assert "pmid:            12345678" in out
