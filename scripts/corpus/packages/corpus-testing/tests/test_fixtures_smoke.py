"""Smoke test: corpus-testing fixtures actually work end-to-end."""
from corpus_testing.annotation_fixtures import make_annotation
from corpus_testing.corpus_fixtures import corpus_root  # noqa: F401  (fixture)


def test_corpus_root_isolated(corpus_root):
    assert corpus_root.is_dir()
    assert not list(corpus_root.iterdir())


def test_make_annotation_writes_jsonl(corpus_root):
    ann_id = make_annotation()
    assert ann_id.startswith("ann_")
    assert len(ann_id) == len("ann_") + 16

    jsonl = corpus_root / "doi_10_1234_test" / "annotations.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text().strip().splitlines()
    assert len(lines) == 1


def test_make_annotation_idempotent(corpus_root):
    a1 = make_annotation()
    a2 = make_annotation()
    assert a1 == a2
    jsonl = corpus_root / "doi_10_1234_test" / "annotations.jsonl"
    assert len(jsonl.read_text().strip().splitlines()) == 1
