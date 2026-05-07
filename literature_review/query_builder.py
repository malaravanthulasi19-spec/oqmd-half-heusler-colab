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
