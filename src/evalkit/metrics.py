"""Deterministic checks: cheap, exact and repeatable. Use them wherever a rule can decide."""

import re


def normalize(text: str) -> str:
    """Lowercase, treat ₹ as Rs, drop thousands separators (1,50,000 -> 150000), collapse spaces."""
    text = text.lower().replace("₹", "rs ")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return re.sub(r"\s+", " ", text)


def contains_facts(answer: str, must_include: list[list[str]]) -> bool:
    """Every group must match; a group is a list of acceptable alternatives (e.g. ["25000", "25k"])."""
    norm = normalize(answer)
    return all(any(normalize(alt) in norm for alt in group) for group in must_include)


def refusal_correct(answered: bool, answerable: bool) -> bool:
    """Answer the questions you can, refuse the ones the documents don't cover."""
    return answered == answerable
