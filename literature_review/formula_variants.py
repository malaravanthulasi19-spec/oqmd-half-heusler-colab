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
    compact_pat = rf"(?<![A-Za-z]){re.escape(variants.compact)}(?![A-Za-z])"
    spaced_pat = rf"(?<![A-Za-z]){'\\s+'.join(re.escape(e) for e in variants.elements)}(?![A-Za-z])"
    hyphen_pat = rf"(?<![A-Za-z]){'-'.join(re.escape(e) for e in variants.elements)}(?![A-Za-z])"
    return any(
        re.search(pat, text) is not None
        for pat in [compact_pat, spaced_pat, hyphen_pat]
    )


def permutation_formula_match(text: str, variants: FormulaVariants) -> bool:
    return any(
        re.search(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", text) is not None
        for p in variants.permutations
    )


def loose_element_system_match(text: str, variants: FormulaVariants) -> bool:
    t = text.lower()
    return all(e.lower() in t for e in variants.elements)
