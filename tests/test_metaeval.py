from pathlib import Path

from evalkit.metaeval import UNSUPPORTED_CLAIMS, flip_condition, indian_format, inject_claim, numbers, swap_number

POLICIES = Path(__file__).parent / "fixtures" / "policies.txt"


def test_indian_format():
    assert indian_format(1500000) == "15,00,000"
    assert indian_format(100000) == "1,00,000"
    assert indian_format(25000) == "25,000"


def test_swap_changes_a_reference_number_to_one_not_in_the_context():
    ctx = numbers("Salaried applicants must have a minimum net monthly income of Rs 25,000. Self-employed Rs 40,000.")
    new, old, repl = swap_number("You need at least Rs 25,000 a month [1].", numbers("Rs 25,000"), ctx)
    assert old == "25,000" and repl == "37,500" and new == "You need at least Rs 37,500 a month [1]."
    # citation markers and numbers that are not in the reference are left alone
    assert swap_number("See [1] for details, age 60.", {"1"}, set()) is None


def test_swap_keeps_lakh_grouping():
    new, _, repl = swap_number("Up to Rs 15,00,000.", {"1500000"}, {"50000"})
    assert repl == "22,50,000"


def test_flip_reverses_a_condition():
    new, old, repl = flip_condition("You must be at least 21 years old.")
    assert new == "You must be at most 21 years old." and (old, repl) == ("at least", "at most")
    assert flip_condition("Rs 500 per bounce.") is None


def test_injected_claims_are_really_unsupported():
    """Every invented claim must be absent from the policy documents, or the 'bad' label is wrong."""
    corpus = POLICIES.read_text(encoding="utf-8").lower()
    for marker in ["salary account", "senior citizen", "clean repayment", "documentation fee", "branch",
                   "saturday", "women", "udyam", "gold"]:
        assert marker not in corpus
    assert len(UNSUPPORTED_CLAIMS) == 8
    assert inject_claim("Answer.", "q01") == inject_claim("Answer.", "q01")  # stable per case
