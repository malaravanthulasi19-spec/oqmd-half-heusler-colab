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
from literature_review.export import assign_material_decision_status, make_paper_link, export_material_screening_master


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
    required = {"Final_Decision","Recommended_Novel","Strong_Manual_Verify","Backup_Candidates","Reported_or_Defer","All_Top10","All_Hits_Audit","Search_Coverage","Legend"}
    assert required.issubset(set(wb.sheet_names))
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
