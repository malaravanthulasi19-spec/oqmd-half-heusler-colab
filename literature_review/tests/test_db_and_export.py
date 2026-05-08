import pytest
import pandas as pd
from literature_review.database import connect
from literature_review.checkpoint import is_query_completed, mark_query_completed
from literature_review.export import export_outputs


def test_deduplication_and_completed_query_skip(tmp_path):
    db = tmp_path / "t.sqlite3"
    conn = connect(db)
    mark_query_completed(conn, "BaTbPa", "gate1", "google", "BaTbPa")
    assert is_query_completed(conn, "BaTbPa", "gate1", "google", "BaTbPa")


def test_output_sorting_and_files(tmp_path):
    df = pd.DataFrame([
        {"Automated Status": "not_found_after_protocol", "Unreported Confidence Score": 150},
        {"Automated Status": "not_found_after_protocol", "Unreported Confidence Score": 120},
        {"Automated Status": "reported_dft", "Unreported Confidence Score": 10},
    ])
    export_outputs(df, tmp_path)
    ranked = pd.read_csv(tmp_path / "02_ranked_not_found_after_protocol.csv")
    assert ranked.iloc[0]["Unreported Confidence Score"] >= ranked.iloc[1]["Unreported Confidence Score"]
    assert (tmp_path / "01_priority_unreported_candidates.xlsx").exists()


def test_top10_export_columns_and_sorting(tmp_path):
    df = pd.DataFrame([
        {"Material": "A", "Automated Status": "not_found_after_protocol", "final_material_priority_tier": "HIGH_RESEARCH_PRIORITY", "final_selection_score": 80, "practicality_score": 70, "stability_score": 60, "literature_risk_penalty": 5},
        {"Material": "B", "Automated Status": "not_found_after_protocol", "final_material_priority_tier": "HIGH_RESEARCH_PRIORITY", "final_selection_score": 70, "practicality_score": 60, "stability_score": 50, "literature_risk_penalty": 7},
    ])
    export_outputs(df, tmp_path)
    out = pd.read_csv(tmp_path / "11_top10_final_research_candidates.csv")
    assert out.iloc[0]["Material"] == "A"

OPENPYXL_AVAILABLE = pytest.importorskip("openpyxl", reason="openpyxl required for workbook validation")
from literature_review.export import assign_material_decision_status, make_paper_link, export_material_screening_master, _build_simple_ranked_list, dedupe_dataframe_columns


def _base_row(**kwargs):
    row = {
        "Automated Status": "not_found_after_protocol",
        "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED",
        "practicality_tier": "PRACTICAL_PRIORITY",
        "Stability": 0.05,
        "final_selection_score": 85,
        "literature_risk_penalty": 10,
        "Band Gap (eV)": 1.2,
    }
    row.update(kwargs)
    return row


def test_assign_material_decision_status_rules():
    assert assign_material_decision_status(_base_row())["material_decision_status"] == "RECOMMENDED_NOVEL_CANDIDATE"
    assert assign_material_decision_status(_base_row(Stability=0.15))["material_decision_status"] == "STRONG_NOVEL_CANDIDATE_MANUAL_VERIFY"
    assert assign_material_decision_status(_base_row(Stability=0.35))["material_decision_status"] == "NOVEL_BUT_LOW_STABILITY"
    assert assign_material_decision_status(_base_row(practicality_tier="EXPENSIVE_RARE_REVIEW"))["material_decision_status"] == "EXPENSIVE_RARE_BACKUP"
    assert assign_material_decision_status(_base_row(practicality_tier="TOXICITY_REVIEW"))["material_decision_status"] == "TOXICITY_REVIEW_DEFER"
    reported = assign_material_decision_status(_base_row(**{"Automated Status": "reported_dft", "best_doi": "10.1234/abc"}))
    assert reported["material_decision_status"] == "REPORTED_DFT_DEFER" and reported["paper_link_if_reported"].startswith("https://doi.org/")
    assert assign_material_decision_status(_base_row(reported_depth_score=80))["material_decision_status"] == "DEEP_PRIOR_STUDY_DEFER"
    assert assign_material_decision_status(_base_row(source_error=True))["material_decision_status"] == "INCOMPLETE_SEARCH_RETRY"
    assert assign_material_decision_status(_base_row(Material="TiFeTe"))["material_decision_status"] == "PRIOR_RUN_CONFLICT_MANUAL_REVIEW"


def test_make_paper_link():
    assert make_paper_link("https://x.org", "10.1/a") == "https://x.org"
    assert make_paper_link("", "10.1/a") == "https://doi.org/10.1/a"


def test_master_workbook_created(tmp_path):
    rows = [
        {"Rank": 1, "Material": "ABC", "Automated Status": "not_found_after_protocol", "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED", "practicality_tier": "PRACTICAL_PRIORITY", "Stability": 0.05, "final_selection_score": 85, "literature_risk_penalty": 5, "Band Gap (eV)": 1.1}
    ]
    out = export_material_screening_master(rows, hits=[], coverage=[], output_dir=tmp_path)
    assert out.exists()
    wb = pd.ExcelFile(out)
    required = {"Final_Ranked_List","Final_Decision","Recommended_Novel","Strong_Manual_Verify","Backup_Candidates","Reported_or_Defer","All_Top10","All_Hits_Audit","Search_Coverage","Search_Strategy","Validation_Checks","Legend"}
    assert required.issubset(set(wb.sheet_names))
    assert wb.sheet_names[0] == "Final_Ranked_List"
    final_ranked = pd.read_excel(out, sheet_name="Final_Ranked_List")
    assert list(final_ranked.columns) == ["Final Rank","Material","Unreported Score","Unreported Status","Stability","Stability Grade","Toxicity / Practicality","Band Gap (eV)","Band Gap Grade","Reported Paper Link","Final Decision","Final Reason"]
    assert final_ranked.columns.duplicated().sum() == 0
    final_df = pd.read_excel(out, sheet_name="Final_Decision")
    assert {"material_decision_status", "material_decision_reason", "final_recommendation"}.issubset(set(final_df.columns))
    assert {"literature_status", "evidence_reliability_tier", "unreported_priority_score", "prior_conflict_flag"}.issubset(set(final_df.columns))


def test_sorting_and_conflict_exclusion(tmp_path):
    rows = [
        {"Rank": 1, "Material": "Good", "Automated Status": "not_found_after_protocol", "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED", "practicality_tier": "PRACTICAL_PRIORITY", "Stability": 0.05, "Band Gap (eV)": 1.0, "formula_level_evidence_found": False, "exact_formula_hit_count": 0, "dft_formula_hit_count": 0, "google_scholar_checked": True, "openalex_checked": True, "semantic_scholar_checked": True},
        {"Rank": 2, "Material": "TiFeTe", "Automated Status": "not_found_after_protocol", "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED", "practicality_tier": "PRACTICAL_PRIORITY", "Stability": 0.05, "Band Gap (eV)": 1.0, "formula_level_evidence_found": False, "exact_formula_hit_count": 0, "dft_formula_hit_count": 0, "google_scholar_checked": True, "openalex_checked": True, "semantic_scholar_checked": True},
        {"Rank": 3, "Material": "BadStability", "Automated Status": "not_found_after_protocol", "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED", "practicality_tier": "PRACTICAL_PRIORITY", "Stability": 0.7, "Band Gap (eV)": 1.0, "formula_level_evidence_found": False, "exact_formula_hit_count": 0, "dft_formula_hit_count": 0, "google_scholar_checked": True, "openalex_checked": True, "semantic_scholar_checked": True},
    ]
    out = export_material_screening_master(rows, hits=[], coverage=[], output_dir=tmp_path)
    fd = pd.read_excel(out, sheet_name="Final_Decision")
    assert fd.iloc[0]["Material"] == "Good"
    rec = pd.read_excel(out, sheet_name="Recommended_Novel")
    assert "TiFeTe" not in set(rec.get("Material", []))


def test_final_ranked_decisions_and_validation(tmp_path):
    rows = [
        {"Material":"NovelGood","literature_status":"HIGH_CONFIDENCE_NOT_FOUND","practicality_tier":"PRACTICAL_PRIORITY","Stability":0.04,"Band Gap (eV)":1.0,"exact_formula_evidence_count":0,"permutation_formula_evidence_count":0,"deep_dft_property_evidence_count":0,"family_level_evidence_count":0},
        {"Material":"Reported","literature_status":"REPORTED_DFT","Stability":0.02,"Band Gap (eV)":1.0,"best_doi":"10.1/x"},
        {"Material":"LowStab","literature_status":"HIGH_CONFIDENCE_NOT_FOUND","practicality_tier":"PRACTICAL_PRIORITY","Stability":0.35,"Band Gap (eV)":1.1},
        {"Material":"ToxicX","literature_status":"HIGH_CONFIDENCE_NOT_FOUND","practicality_tier":"TOXICITY_REVIEW","highly_toxic_elements":"Tl","Stability":0.05,"Band Gap (eV)":1.2},
        {"Material":"RareX","literature_status":"HIGH_CONFIDENCE_NOT_FOUND","practicality_tier":"EXPENSIVE_RARE_REVIEW","expensive_rare_elements":"Pt","Stability":0.05,"Band Gap (eV)":1.3},
        {"Material":"Conflict","literature_status":"HIGH_CONFIDENCE_NOT_FOUND","known_reported_composition_flag":True,"prior_best_doi":"10.2/y","Stability":0.05,"Band Gap (eV)":1.1},
    ]
    out = export_material_screening_master(rows, hits=[], coverage=[], output_dir=tmp_path)
    fr = pd.read_excel(out, sheet_name="Final_Ranked_List")
    assert fr.loc[fr["Material"]=="Reported","Final Decision"].iloc[0] == "REPORTED_REJECT"
    assert fr.loc[fr["Material"]=="Reported","Reported Paper Link"].iloc[0].startswith("https://doi.org/")
    assert fr.loc[fr["Material"]=="Conflict","Final Decision"].iloc[0] != "BEST_NOVEL_CANDIDATE"
    assert fr.loc[fr["Material"]=="NovelGood","Final Decision"].iloc[0] == "BEST_NOVEL_CANDIDATE"
    assert fr.loc[fr["Material"]=="LowStab","Final Decision"].iloc[0] == "LOW_STABILITY_REJECT"
    assert fr.loc[fr["Material"]=="ToxicX","Final Decision"].iloc[0] == "TOXICITY_REJECT"
    assert fr.loc[fr["Material"]=="RareX","Final Decision"].iloc[0] == "BACKUP_ONLY"
    assert fr.loc[fr["Material"]=="NovelGood","Band Gap Grade"].iloc[0] == "IDEAL"
    vc = pd.read_excel(out, sheet_name="Validation_Checks")
    assert set(["number of BEST_NOVEL_CANDIDATE rows","number of GOOD_NOVEL_CANDIDATE rows","number of MANUAL_REVIEW_REQUIRED rows","number of BACKUP_ONLY rows","number of REPORTED_REJECT rows"]).issubset(set(vc["check"]))


def test_duplicate_columns_helpers_and_sheets(tmp_path):
    rows = [{
        "Rank": 1,
        "Material": "ABC",
        "Band Gap (eV)": 1.1,
        "Stability": 0.05,
        "Automated Status": "not_found_after_protocol",
        "novelty_confidence_tier": "HIGH_CONFIDENCE_UNREPORTED",
        "practicality_tier": "PRACTICAL_PRIORITY",
        "material_decision_status": "RECOMMENDED_NOVEL_CANDIDATE",
        "material_decision_reason": "preexisting",
        "final_recommendation": "preexisting",
    }]
    out = export_material_screening_master(rows, hits=[], coverage=[], output_dir=tmp_path)
    wb = pd.ExcelFile(out)
    for sheet in ["Final_Ranked_List", "Final_Decision", "All_Top10"]:
        sh = pd.read_excel(out, sheet_name=sheet)
        assert sh.columns.duplicated().sum() == 0


def test_build_simple_ranked_list_handles_duplicate_cols():
    base = pd.DataFrame([
        {"Material": "Dup", "Stability": 0.05, "Band Gap (eV)": 1.0, "practicality_tier": "PRACTICAL_PRIORITY", "literature_status": "HIGH_CONFIDENCE_NOT_FOUND"}
    ])
    dup = pd.concat([base, base[["Stability", "Band Gap (eV)"]]], axis=1)
    out = _build_simple_ranked_list(dup)
    assert out.columns.duplicated().sum() == 0
    assert out.loc[0, "Band Gap Grade"] == "IDEAL"
    assert out.loc[0, "Stability Grade"] == "EXCELLENT"


def test_dedupe_dataframe_columns_removes_duplicates():
    df = pd.DataFrame([[1,2]], columns=["A","A"])
    deduped = dedupe_dataframe_columns(df)
    assert list(deduped.columns) == ["A"]

