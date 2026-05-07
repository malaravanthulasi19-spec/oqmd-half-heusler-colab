from .constants import GATE2_TERMS, GATE3_TERMS
from .formula_variants import FormulaVariants


def gate1_queries(v: FormulaVariants) -> list[str]:
    return [v.compact, v.spaced, v.hyphenated]


def gate2_queries(v: FormulaVariants) -> list[str]:
    return [f'{v.compact} {term}' for term in GATE2_TERMS]


def gate3_queries(v: FormulaVariants) -> list[str]:
    return [f'{v.compact} {term}' for term in GATE3_TERMS]


def gate4_queries(v: FormulaVariants) -> list[str]:
    return v.permutations


def profile_queries(v: FormulaVariants, profile: str) -> dict[str, list[str]]:
    base = {
        "gate1": [f'"{v.compact}"', f'"{v.spaced}"', f'"{v.hyphenated}"'],
        "gate2": gate2_queries(v),
        "gate3": gate3_queries(v),
    }
    if profile == "validation_recall":
        base["gate2"] += [
            f'"{v.compact}" "half-Heusler alloy"',
            f'"{v.compact}" "half-Heusler compound"',
            f'"{v.compact}" "band structure"',
            f'"{v.compact}" "ab initio"',
            f'"{v.compact}" thermoelectric',
        ]
    return base
