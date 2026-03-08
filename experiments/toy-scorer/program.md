# Toy Scorer Optimization

You are optimizing a text relevance scorer. The scorer takes a query and a document
and returns a relevance score (0.0 to 1.0).

The eval harness tests the scorer against labeled query-document pairs and measures
accuracy (percentage of pairs where the scorer's ranking matches the ground truth).

## What you can change

- `scorer.py` — the scoring function. Currently uses simple keyword overlap.
  You can change the algorithm entirely: TF-IDF, BM25, fuzzy matching,
  semantic similarity heuristics, n-gram overlap, etc.

## What you cannot change

- `eval.py` — the evaluation harness (read-only)
- `test_cases.json` — the test data (read-only)

## Goal

Maximize accuracy. The baseline keyword overlap scorer gets ~50-60%.
Good approaches should reach 70-80%+.

## Tips

- Look at the test cases to understand the scoring patterns
- Simple improvements (case normalization, stopword removal) can help a lot
- More sophisticated approaches (BM25, weighted term frequency) can help more
- Don't over-engineer — if accuracy improves with simpler code, that's a win
