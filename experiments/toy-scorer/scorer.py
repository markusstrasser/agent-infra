"""Text relevance scorer. This is the file the agent optimizes."""


def score(query: str, document: str) -> float:
    """Score relevance of document to query. Returns 0.0 to 1.0."""
    # Baseline: simple keyword overlap
    query_words = set(query.lower().split())
    doc_words = set(document.lower().split())

    if not query_words:
        return 0.0

    overlap = len(query_words & doc_words)
    return overlap / len(query_words)
