from pathlib import Path
import pandas as pd


def export_outputs(df_all: pd.DataFrame, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(output_dir / "05_all_hits_audit.csv", index=False)
    ranked_not_found = df_all[df_all["Automated Status"] == "not_found_after_protocol"].copy()
    if "Unreported Confidence Score" not in ranked_not_found.columns:
        ranked_not_found["Unreported Confidence Score"] = 0
    ranked_not_found.sort_values("Unreported Confidence Score", ascending=False).to_csv(output_dir / "02_ranked_not_found_after_protocol.csv", index=False)
    novelty = df_all.get("novelty_confidence_tier", pd.Series([""] * len(df_all)))
    practical = df_all.get("practicality_tier", pd.Series(["PRACTICAL_PRIORITY"] * len(df_all)))

    df_all[novelty == "HIGH_CONFIDENCE_UNREPORTED"].to_csv(output_dir / "02_high_confidence_unreported.csv", index=False)
    df_all[novelty == "MEDIUM_CONFIDENCE_UNREPORTED"].to_csv(output_dir / "03_medium_confidence_unreported.csv", index=False)
    df_all[novelty == "AMBIGUOUS_REVIEW_REQUIRED"].to_csv(output_dir / "04_ambiguous_manual_review.csv", index=False)
    df_all[df_all["Automated Status"] == "reported_dft"].to_csv(output_dir / "05_reported_dft.csv", index=False)
    df_all[df_all["Automated Status"] == "reported_non_dft"].to_csv(output_dir / "06_reported_non_dft.csv", index=False)
    df_all.to_csv(output_dir / "07_all_hits_audit.csv", index=False)
    df_all.to_csv(output_dir / "08_search_coverage_report.csv", index=False)
    df_all[practical == "PRACTICAL_PRIORITY"].to_csv(output_dir / "09_practical_priority_candidates.csv", index=False)
    df_all[practical != "PRACTICAL_PRIORITY"].to_csv(output_dir / "10_radioactive_or_impractical_candidates.csv", index=False)

    order = ["TOP_RESEARCH_PRIORITY", "HIGH_RESEARCH_PRIORITY", "MEDIUM_RESEARCH_PRIORITY", "LOW_RESEARCH_PRIORITY", "DEFER"]
    ranking = df_all.copy()
    tier_vals = ranking["final_material_priority_tier"] if "final_material_priority_tier" in ranking.columns else pd.Series(["DEFER"] * len(ranking))
    ranking["_tier"] = pd.Categorical(tier_vals, categories=order, ordered=True)
    for col in ["final_selection_score", "practicality_score", "stability_score", "literature_risk_penalty"]:
        if col not in ranking.columns:
            ranking[col] = 0
    ranking = ranking.sort_values(["_tier", "final_selection_score", "practicality_score", "stability_score", "literature_risk_penalty"], ascending=[True, False, False, False, True]).drop(columns=["_tier"])
    ranking.head(10).to_csv(output_dir / "11_top10_final_research_candidates.csv", index=False)

    xlsx_path = output_dir / "01_priority_unreported_candidates.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path) as xw:
            ranking.to_excel(xw, index=False)
    except ModuleNotFoundError:
        xlsx_path.write_bytes(b"")
