"""Pure, importable helpers for token-baseline.py.

token-baseline.py is hyphenated (a runnable script), so its pure logic can't be
imported for unit testing. This module holds that testable logic; the script
imports from here.
"""

from __future__ import annotations


def percentile(data, p):
    """Nearest-rank percentile (0-indexed floor); empty input → 0."""
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s) - 1)]
