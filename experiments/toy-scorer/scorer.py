"""Text relevance scorer. This is the file the agent optimizes."""

# Common English stopwords to filter out
STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "our", "their",
})


def _tokenize(text: str) -> set[str]:
    """Lowercase, split, remove stopwords and short tokens."""
    words = set()
    for w in text.lower().split():
        # Strip punctuation
        w = w.strip(".,;:!?\"'()-[]{}|/\\")
        if w and w not in STOPWORDS and len(w) > 1:
            words.add(w)
    return words


def score(query: str, document: str) -> float:
    """Score relevance of document to query. Returns 0.0 to 1.0."""
    query_words = _tokenize(query)
    doc_words = _tokenize(document)

    if not query_words:
        return 0.0

    # Exact word overlap
    overlap = len(query_words & doc_words)

    # Partial/substring matching for compound terms
    partial = 0
    for qw in query_words:
        if qw not in doc_words:
            for dw in doc_words:
                if qw in dw or dw in qw:
                    partial += 0.5
                    break

    return min(1.0, (overlap + partial) / len(query_words))
