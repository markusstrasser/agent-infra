#!/usr/bin/env python3
"""Statistics core for the search-engine verification eval — stdlib only.

Wilson 95% CI, McNemar exact two-sided, Cohen's kappa. No scipy/sklearn dep so
`uv run python3 stats.py` works anywhere. Self-test in __main__ checks each
against known reference values.

These are the rigor primitives the N=60 Gospel-reader study used
(publishing/research/2026-05-19-engine-reliability-metric.md). Reused verbatim
so engine numbers here are directly comparable to that study's tables.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Interval:
    point: float
    low: float
    high: float

    def __str__(self) -> str:
        return f"{self.point*100:.1f}% [{self.low*100:.1f}, {self.high*100:.1f}]"


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Interval:
    """Wilson score interval for a binomial proportion (default 95%).

    Preferred over normal-approx at small n / extreme p — it never leaves [0,1]
    and has good coverage at the N=60 scale we run at.
    """
    if n == 0:
        return Interval(0.0, 0.0, 1.0)
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return Interval(p, max(0.0, center - half), min(1.0, center + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from discordant counts.

    b = pairs where engine A right & B wrong; c = A wrong & B right.
    Concordant pairs are irrelevant to McNemar. Exact binomial on n=b+c with
    p=0.5 (no continuity-correction guesswork — correct at small discordant n,
    which is exactly where chi-square McNemar misleads).
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # two-sided = 2 * P(X <= k) under Binom(n, 0.5), capped at 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa for two raters over categorical labels.

    Used two ways: between engines (are Exa/Brave independent views or the same
    view?) and inter-rater (judge stability on a re-grade).
    """
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("label lists must be same nonzero length")
    n = len(labels_a)
    cats = sorted(set(labels_a) | set(labels_b))
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    mat = [[0] * k for _ in range(k)]
    for a, b in zip(labels_a, labels_b):
        mat[idx[a]][idx[b]] += 1
    po = sum(mat[i][i] for i in range(k)) / n
    row = [sum(mat[i]) for i in range(k)]
    col = [sum(mat[i][j] for i in range(k)) for j in range(k)]
    pe = sum((row[i] / n) * (col[i] / n) for i in range(k))
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def mcnemar_table(verd_a: list[str], verd_b: list[str], gold: list[str]) -> tuple[int, int, int, int]:
    """Build (a_only_right, b_only_right, both_right, both_wrong) vs gold.

    Returns the discordant counts McNemar needs plus concordants for reporting.
    """
    a_only = b_only = both_r = both_w = 0
    for va, vb, g in zip(verd_a, verd_b, gold):
        ra, rb = va == g, vb == g
        if ra and rb:
            both_r += 1
        elif ra and not rb:
            a_only += 1
        elif rb and not ra:
            b_only += 1
        else:
            both_w += 1
    return a_only, b_only, both_r, both_w


def _selftest() -> None:
    # Wilson: 9/10 -> point 0.9, known interval ~[0.596, 0.982]
    w = wilson_ci(9, 10)
    assert abs(w.point - 0.9) < 1e-9
    assert abs(w.low - 0.5958) < 0.01, w.low
    assert abs(w.high - 0.9821) < 0.01, w.high

    # McNemar: b=9, c=1 -> two-sided exact p ~= 0.02148 (matches memo's perp-vs-exa 0.022)
    p = mcnemar_exact(9, 1)
    assert abs(p - 0.02148) < 1e-4, p
    # symmetric discordant -> p=1.0
    assert abs(mcnemar_exact(5, 5) - 1.0) < 1e-9
    # no discordant -> p=1.0
    assert mcnemar_exact(0, 0) == 1.0

    # Cohen kappa: perfect agreement -> 1.0
    assert abs(cohen_kappa(list("TPFTPF"), list("TPFTPF")) - 1.0) < 1e-9
    # known 2x2: a=[T,T,F,F], b=[T,F,F,F] -> po=0.75, pe=0.5*0.75 + 0.5*0.25 ... compute
    ka = cohen_kappa(["T", "T", "F", "F"], ["T", "F", "F", "F"])
    # po=3/4=0.75; rowT=2,colT=1 -> pe=(2/4)(1/4)+(2/4)(3/4)=0.125+0.375=0.5; k=(0.75-0.5)/0.5=0.5
    assert abs(ka - 0.5) < 1e-9, ka

    # table sanity
    a_only, b_only, both_r, both_w = mcnemar_table(
        ["T", "T", "F"], ["T", "F", "F"], ["T", "T", "T"]
    )
    assert (a_only, b_only, both_r, both_w) == (1, 0, 1, 1), (a_only, b_only, both_r, both_w)

    print("  ✓ wilson_ci    9/10 ->", w)
    print("  ✓ mcnemar      b=9,c=1 -> p =", round(p, 5), "(memo perp-vs-exa: 0.022)")
    print("  ✓ cohen_kappa  known 2x2 -> 0.5; perfect -> 1.0")
    print("  ✓ mcnemar_table discordant/concordant split correct")
    print("\n  All stats primitives validated against reference values.")


if __name__ == "__main__":
    print("[stats.py self-test]")
    _selftest()
