"""Pytest fixtures providing an isolated corpus root per test."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Per-test ~/Projects/corpus/ tmpdir. Sets CORPUS_ROOT.

    Use as: `def test_foo(corpus_root): ...`. After the test, the dir is wiped
    by pytest's tmp_path mechanism.
    """
    root = tmp_path / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    yield root
