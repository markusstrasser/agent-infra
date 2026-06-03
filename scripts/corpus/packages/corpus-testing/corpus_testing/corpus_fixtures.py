"""Pytest fixtures providing an isolated corpus root per test."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from corpus_core.store import CorpusStore

import pytest


@pytest.fixture
def corpus_root(tmp_path: Path) -> Iterator[Path]:
    """Per-test corpus root path.

    Use as: `def test_foo(corpus_root): ...`. After the test, the dir is wiped
    by pytest's tmp_path mechanism.
    """
    root = tmp_path / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    yield root


@pytest.fixture
def corpus_store(corpus_root: Path) -> CorpusStore:
    return CorpusStore(corpus_root)
