from __future__ import annotations

from itertools import permutations
import re

_ELEMENT_RE = re.compile(r"[A-Z][a-z]?")


def parse_formula_elements(formula: str) -> list[str]:
    return _ELEMENT_RE.findall((formula or "").strip())


def canonical_element_set(formula: str) -> str:
    elems = parse_formula_elements(formula)
    return "-".join(sorted(elems))


def formula_permutations(formula: str) -> list[str]:
    elems = parse_formula_elements(formula)
    if len(elems) <= 1:
        return [formula]
    return ["".join(p) for p in permutations(elems)]


def spaced_formula_permutations(formula: str) -> list[str]:
    return [" ".join(parse_formula_elements(p)) for p in formula_permutations(formula)]


def hyphenated_formula_permutations(formula: str) -> list[str]:
    return ["-".join(parse_formula_elements(p)) for p in formula_permutations(formula)]
