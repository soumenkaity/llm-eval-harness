"""Statistics for small evaluation sets, using only the standard library.

With 30-40 test cases a single pass rate is noisy: 30/34 vs 28/34 can easily be luck. So every rate
gets a confidence interval, and A/B comparisons use *paired* tests, because both systems answered
the same questions and per-question differences are far less noisy than comparing two totals.
"""

import math
import random
from statistics import mean


def bootstrap_ci(values: list[float], iters: int = 10_000, level: float = 0.95, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap: resample the cases with replacement and see how much the mean moves."""
    if not values:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(iters))
    lo = means[int((1 - level) / 2 * iters)]
    hi = means[min(iters - 1, int((1 + level) / 2 * iters))]
    return (lo, hi)


def paired_bootstrap(a: list[float], b: list[float], iters: int = 10_000, level: float = 0.95, seed: int = 0) -> dict:
    """Mean of (b - a) over the same cases, with a bootstrap CI for that difference."""
    assert len(a) == len(b), "paired samples must have the same length"
    diffs = [y - x for x, y in zip(a, b)]
    lo, hi = bootstrap_ci(diffs, iters, level, seed)
    return {"diff": mean(diffs) if diffs else math.nan, "ci": (lo, hi)}


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    """Exact McNemar test for paired pass/fail results.

    Only the cases where the two systems disagree carry information: `a_only` (A passed, B failed)
    and `b_only`. If the systems were equally good, each disagreement would be a fair coin flip, so
    the p-value is a two-sided binomial test on those counts.
    """
    a_only = sum(x and not y for x, y in zip(a, b))
    b_only = sum(y and not x for x, y in zip(a, b))
    n = a_only + b_only
    if n == 0:
        return {"a_only": 0, "b_only": 0, "p_value": 1.0}
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return {"a_only": a_only, "b_only": b_only, "p_value": min(1.0, 2 * tail)}


def cohen_kappa(truth: list[bool], pred: list[bool]) -> float:
    """Agreement between two raters beyond what chance alone would give (1 = perfect, 0 = chance)."""
    n = len(truth)
    if n == 0:
        return math.nan
    observed = sum(t == p for t, p in zip(truth, pred)) / n
    pt, pp = sum(truth) / n, sum(pred) / n
    expected = pt * pp + (1 - pt) * (1 - pp)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    s = sorted(values)
    idx = (len(s) - 1) * q
    lo, hi = math.floor(idx), math.ceil(idx)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)
