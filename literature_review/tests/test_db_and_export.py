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
