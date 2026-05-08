from literature_review.formula_variants import build_variants
from literature_review.query_builder import gate1_queries, gate2_queries, gate3_queries, profile_queries


def test_staged_query_generation():
    v = build_variants("BaTbPa")
    assert len(gate1_queries(v)) == 3
    assert any("DFT" in q for q in gate2_queries(v))
    assert any("C1b" in q for q in gate3_queries(v))


def test_candidate_screening_expanded_queries():
    v = build_variants("TiNiSb")
    prof = profile_queries(v, "candidate_screening_expanded")
    q2 = " | ".join(prof["gate2"])
    q3 = " | ".join(prof["gate3"])
    for term in ["DOS", "density of states", "band structure", "BoltzTrap"]:
        assert term in q2
    for term in ["mechanical stability", "phonon dispersion", "thermoelectric", "Seebeck", "ZT", "zT", "half-metal", "spin polarization", "ferromagnetic", "spintronic"]:
        assert term in q3
