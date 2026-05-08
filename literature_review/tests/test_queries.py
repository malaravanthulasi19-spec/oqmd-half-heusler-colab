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
    joined = " | ".join(sum(prof.values(), []))
    for term in ["Born-Huang criteria", "C11 C12 C44", "phonon dispersion", "DOS", "density of states", "spin polarization", "Seebeck coefficient", "ZT", "zT", "Slack model", "AIMD", "ALAMODE", "BoltzTrap2", "GIBBS2"]:
        assert term in joined
