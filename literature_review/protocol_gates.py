from .formula_variants import build_variants
from .query_builder import gate1_queries, gate2_queries, gate3_queries, gate4_queries


def staged_queries(formula: str, strong_dft_found: bool = False):
    v = build_variants(formula)
    out = {
        "gate1": gate1_queries(v),
        "gate2": gate2_queries(v),
        "gate3": gate3_queries(v),
        "gate4": [] if strong_dft_found else gate4_queries(v),
    }
    return out
