"""Pure token-measurement helpers (percentiles, history rows).

Originally extracted from token-baseline.py (deleted 2026-06-13, no live caller);
kept because tests/test_token_reduction.py contract-tests this logic.
"""

from __future__ import annotations


def percentile(data, p):
    """Nearest-rank percentile (0-indexed floor); empty input → 0."""
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s) - 1)]
