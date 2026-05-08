from literature_review.formula_variants import build_variants
from literature_review.query_builder import profile_queries
from literature_review.keypaper_filters import detect_keypaper_context, compute_keypaper_depth_score
from literature_review.material_selection_scoring import compute_material_selection_scores


def test_expanded_queries_include_key_terms():
    v = build_variants("FeVSn")
    prof = profile_queries(v, "candidate_screening_expanded")
    q = " | ".join(prof["gate2"] + prof["gate3"])
    for term in ["Born-Huang criteria", "C11 C12 C44", "phonon dispersion", "DOS", "density of states", "spin polarization", "Seebeck coefficient", " ZT", " zT", "Slack model", "AIMD", "ALAMODE", "BoltzTrap2", "GIBBS2"]:
        assert term.strip() in q


def test_keypaper_context_and_depth_penalties():
    txt = "FeVSn half-Heusler C1b F-43m formation energy elastic constants C11 C12 C44 Born-Huang phonon dispersion DOS spin-up spin-down half-metal thermoelectric Seebeck ZT BoltzTrap2 DFT"
    ctx = detect_keypaper_context(txt)
    assert all(ctx[f"has_keypaper_{k}_context"] for k in ["structure","stability","mechanical","phonon","electronic","magnetic_spintronic","thermoelectric","method"])
    deep = compute_keypaper_depth_score({**ctx, "formula_level_evidence_found": True, "false_positive_flag": False, "evidence_tier": "TIER_3_FORMULA_LEVEL"})
    assert deep["keypaper_depth_tier"] == "DEEP_KEYPAPER_STYLE_STUDY"
    weak = compute_keypaper_depth_score({**ctx, "formula_level_evidence_found": False, "false_positive_flag": False, "evidence_tier": "TIER_3_FORMULA_LEVEL"})
    assert weak["keypaper_depth_score"] < deep["keypaper_depth_score"]
    elem = compute_keypaper_depth_score({**ctx, "formula_level_evidence_found": True, "false_positive_flag": False, "evidence_tier": "TIER_1_ELEMENT_SYSTEM_WEAK"})
    fp = compute_keypaper_depth_score({**ctx, "formula_level_evidence_found": True, "false_positive_flag": True, "evidence_tier": "TIER_3_FORMULA_LEVEL"})
    assert elem["keypaper_depth_score"] < deep["keypaper_depth_score"]
    assert fp["keypaper_depth_score"] < deep["keypaper_depth_score"]


def test_keypaper_blocks_top_priority():
    row = {"Material":"TiNiSb","Composition":"TiNiSb","Prototype":"C1b","Space Group":"F-43m","OQMD Entry ID":"1","Band Gap (eV)":1.0,"Stability":0.05,"Formation Energy / ΔE":-0.1,"Automated Status":"not_found_after_protocol","formula_level_evidence_found":False,"exact_formula_hit_count":0,"dft_formula_hit_count":0,"google_scholar_checked":True,"openalex_checked":True,"semantic_scholar_checked":True,"reported_depth_score":0,"keypaper_depth_score":85}
    s = compute_material_selection_scores(row)
    assert s["final_material_priority_tier"] != "TOP_RESEARCH_PRIORITY"
