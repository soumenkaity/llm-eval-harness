import math

from evalkit.stats import bootstrap_ci, cohen_kappa, mcnemar_exact, paired_bootstrap, percentile


def test_mcnemar_counts_only_disagreements():
    a = [True] * 30 + [False] * 4
    b = [True] * 24 + [False] * 6 + [False] * 4  # B lost 6 cases A passed, gained none
    r = mcnemar_exact(a, b)
    assert (r["a_only"], r["b_only"]) == (6, 0)
    assert math.isclose(r["p_value"], 2 / 2**6)  # 6 coin flips all landing the same way


def test_mcnemar_balanced_disagreements_are_not_significant():
    a = [True, True, False, False, True]
    b = [False, False, True, True, True]
    assert mcnemar_exact(a, b)["p_value"] == 1.0
    assert mcnemar_exact([True], [True])["p_value"] == 1.0


def test_bootstrap_ci_brackets_the_mean():
    vals = [1.0] * 28 + [0.0] * 6
    lo, hi = bootstrap_ci(vals)
    assert lo < 28 / 34 < hi
    assert bootstrap_ci([1.0] * 10) == (1.0, 1.0)


def test_paired_bootstrap_difference():
    r = paired_bootstrap([1, 1, 1, 1], [1, 0, 1, 0])
    assert r["diff"] == -0.5 and r["ci"][1] <= 0


def test_kappa():
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    # A judge that always says "good" agrees 75% of the time here, but adds nothing beyond chance
    assert cohen_kappa([True, True, True, False], [True, True, True, True]) == 0.0


def test_percentile():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
