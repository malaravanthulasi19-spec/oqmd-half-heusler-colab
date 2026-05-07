from literature_review.formula_variants import build_variants
from literature_review.query_builder import gate1_queries, gate2_queries, gate3_queries


def test_staged_query_generation():
    v = build_variants("BaTbPa")
    assert len(gate1_queries(v)) == 3
    assert any("DFT" in q for q in gate2_queries(v))
    assert any("C1b" in q for q in gate3_queries(v))
