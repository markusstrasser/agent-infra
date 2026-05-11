"""Drop-in conftest.py template for downstream consumers.

Copy to tests/conftest.py in your MCP project (or import directly):

    from corpus_testing.corpus_fixtures import corpus_root  # noqa: F401
    from corpus_testing.annotation_fixtures import make_annotation  # noqa: F401

That gives every test in tests/ access to:

    def test_x(corpus_root):
        ann_id = make_annotation()
        ...

Five lines of conftest, three lines per test.
"""
from corpus_testing.annotation_fixtures import make_annotation  # noqa: F401
from corpus_testing.corpus_fixtures import corpus_root  # noqa: F401
