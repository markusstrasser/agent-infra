"""Text relevance scorer. This is the file the agent optimizes."""

import math

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


def _stem(word: str) -> str:
    """Minimal suffix stemmer."""
    if word.endswith("izing"):
        return word[:-5] + "ize"
    if word.endswith("ized"):
        return word[:-4] + "ize"
    for suffix in ("ation", "ment", "ness", "ting", "ing", "ies", "ous", "ive", "ers", "ed", "ly", "es", "er", "al", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[:-len(suffix)]
    return word


def _tokenize(text: str) -> set[str]:
    """Lowercase, split, remove stopwords, stem."""
    words = set()
    for w in text.lower().split():
        w = w.strip(".,;:!?\"'()-[]{}|/\\")
        if w and w not in STOPWORDS and len(w) > 1:
            words.add(_stem(w))
    return words


def _word_weight(word: str) -> float:
    """Longer/rarer words are more specific — weight them higher."""
    return math.log(1 + len(word))


def score(query: str, document: str) -> float:
    """Score relevance of document to query. Returns 0.0 to 1.0."""
    q_set = _tokenize(query)
    d_set = _tokenize(document)

    if not q_set:
        return 0.0

    total_weight = sum(_word_weight(qw) for qw in q_set)
    matched_weight = 0.0

    for qw in q_set:
        w = _word_weight(qw)
        if qw in d_set:
            matched_weight += w
        else:
            for dw in d_set:
                if qw in dw or dw in qw:
                    matched_weight += w * 0.5
                    break

    return min(1.0, matched_weight / total_weight)
