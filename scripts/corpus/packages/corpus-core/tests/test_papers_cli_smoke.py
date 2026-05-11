"""`corpus stats` works on an empty store + after one ingest."""
from __future__ import annotations

import io
import sys

from corpus_core import cli, ingest


def test_stats_empty(corpus_root, capsys):
    rc = cli.main(["stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "papers=0" in out


def test_stats_after_ingest(corpus_root, tiny_pdf, capsys):
    ingest.ingest_pdf(tiny_pdf, doi="10.test/smoke", skip_parse=True)
    rc = cli.main(["stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "papers=1" in out
