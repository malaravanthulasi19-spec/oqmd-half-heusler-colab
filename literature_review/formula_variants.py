import itertools
import re
from dataclasses import dataclass


@dataclass
class FormulaVariants:
    compact: str
    spaced: str
    hyphenated: str
    permutations: list[str]
    elements: list[str]


def parse_formula(formula: str) -> list[str]:
    return re.findall(r"[A-Z][a-z]?", formula)


def build_variants(formula: str) -> FormulaVariants:
    elements = parse_formula(formula)
    compact = "".join(elements)
    spaced = " ".join(elements)
    hyphenated = "-".join(elements)
    perms = sorted({"".join(p) for p in itertools.permutations(elements)})
    return FormulaVariants(compact, spaced, hyphenated, perms, elements)


def exact_formula_match(text: str, variants: FormulaVariants) -> bool:
    t = text.lower()
    return any(v.lower() in t for v in [variants.compact, variants.spaced, variants.hyphenated])


def permutation_formula_match(text: str, variants: FormulaVariants) -> bool:
    t = text.lower()
    return any(p.lower() in t for p in variants.permutations)


def loose_element_system_match(text: str, variants: FormulaVariants) -> bool:
    t = text.lower()
    return all(e.lower() in t for e in variants.elements)
