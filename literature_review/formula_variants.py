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
    compact = re.compile(rf"(?<![A-Za-z]){re.escape(variants.compact)}(?![A-Za-z])")
    spaced = re.compile(rf"(?<![A-Za-z]){re.escape(variants.spaced)}(?![A-Za-z])")
    hyphenated = re.compile(rf"(?<![A-Za-z]){re.escape(variants.hyphenated)}(?![A-Za-z])")
    return bool(compact.search(text) or spaced.search(text) or hyphenated.search(text))


def permutation_formula_match(text: str, variants: FormulaVariants) -> bool:
    for p in variants.permutations:
        if re.search(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", text):
            return True
    return False


def loose_element_system_match(text: str, variants: FormulaVariants) -> bool:
    t = text.lower()
    return all(e.lower() in t for e in variants.elements)
