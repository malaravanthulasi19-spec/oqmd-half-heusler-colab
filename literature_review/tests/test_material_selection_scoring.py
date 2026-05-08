from literature_review.material_selection_scoring import compute_material_selection_scores
from literature_review.export import export_outputs
import pandas as pd


def _base(**kw):
    d = {
        "Material": "TiNiSb", "Composition": "TiNiSb", "Prototype": "C1b", "Space Group": "F-43m", "OQMD Entry ID": "1",
        "Band Gap (eV)": 1.0, "Stability": 0.05, "Formation Energy / ΔE": -0.1, "Automated Status": "not_found_after_protocol",
        "formula_level_evidence_found": False, "exact_formula_hit_count": 0, "dft_formula_hit_count": 0,
        "google_scholar_checked": True, "openalex_checked": True, "semantic_scholar_checked": True, "reported_depth_score": 0,
    }
    d.update(kw)
    return d


def test_top_priority_candidate():
    s = compute_material_selection_scores(_base())
    assert s["final_material_priority_tier"] == "TOP_RESEARCH_PRIORITY"


def test_defer_cases_and_tiers():
    assert compute_material_selection_scores(_base(Material="UNpSb", **{"Band Gap (eV)": 6.0}))["final_material_priority_tier"] == "DEFER"
    assert compute_material_selection_scores(_base(**{"Automated Status": "reported_dft"}))["final_material_priority_tier"] == "DEFER"
    assert compute_material_selection_scores(_base(reported_depth_score=80))["final_material_priority_tier"] == "DEFER"
    assert compute_material_selection_scores(_base(Stability=0.4))["final_material_priority_tier"] != "TOP_RESEARCH_PRIORITY"
    assert compute_material_selection_scores(_base(Prototype="Perovskite", **{"Space Group": "P-1"}))["final_material_priority_tier"] != "TOP_RESEARCH_PRIORITY"
    assert compute_material_selection_scores(_base(Material="TiCdSb"))["practicality_tier"] == "TOXICITY_REVIEW"
    assert compute_material_selection_scores(_base(Material="TiPtSb"))["practicality_tier"] == "EXPENSIVE_RARE_REVIEW"
    assert compute_material_selection_scores(_base(Material="TiAcSb"))["practicality_tier"] == "HIGHLY_IMPRACTICAL"
    assert compute_material_selection_scores(_base(Material="TiUSb"))["practicality_tier"] == "RADIOACTIVE_REVIEW"
    assert compute_material_selection_scores(_base(Material="TiPbSb"))["practicality_tier"] == "TOXICITY_REVIEW"
    assert compute_material_selection_scores(_base(Material="TiRuSb"))["practicality_tier"] == "EXPENSIVE_RARE_REVIEW"
    assert compute_material_selection_scores(_base(Material="TiUSb"))["final_material_priority_tier"] != "TOP_RESEARCH_PRIORITY"


def test_score_clamped_and_export_columns(tmp_path):
    s = compute_material_selection_scores(_base(reported_depth_score=100, **{"Automated Status": "reported_dft", "Band Gap (eV)": 9.0}))
    assert 0 <= s["final_selection_score"] <= 100
    df = pd.DataFrame([{**_base(), **s}])
    export_outputs(df, tmp_path)
    out = pd.read_csv(tmp_path / "11_top10_final_research_candidates.csv")
    for c in ["novelty_score","half_heusler_validity_score","stability_score","practicality_score","application_score","literature_risk_penalty","metadata_quality_score","final_selection_score","final_material_priority_tier","selection_reason"]:
        assert c in out.columns
