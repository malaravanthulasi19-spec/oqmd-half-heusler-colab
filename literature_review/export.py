from pathlib import Path
import pandas as pd


def export_outputs(df_all: pd.DataFrame, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(output_dir / "05_all_hits_audit.csv", index=False)
    df_all[df_all["Automated Status"] == "not_found_after_protocol"].sort_values(
        "Unreported Confidence Score", ascending=False
    ).to_csv(output_dir / "02_ranked_not_found_after_protocol.csv", index=False)
    df_all[df_all["Automated Status"] == "ambiguous_manual_review"].to_csv(
        output_dir / "03_ambiguous_manual_review.csv", index=False
    )
    df_all[df_all["Automated Status"] == "reported_dft"].to_csv(output_dir / "04_reported_dft.csv", index=False)
    df_all.to_csv(output_dir / "06_search_coverage_report.csv", index=False)
    novelty = df_all["novelty_confidence_tier"] if "novelty_confidence_tier" in df_all.columns else pd.Series(["" for _ in range(len(df_all))])
    df_all[novelty == "HIGH_CONFIDENCE_UNREPORTED"].to_csv(output_dir / "02_high_confidence_unreported.csv", index=False)
    df_all[novelty == "MEDIUM_CONFIDENCE_UNREPORTED"].to_csv(output_dir / "03_medium_confidence_unreported.csv", index=False)
    df_all[novelty == "AMBIGUOUS_REVIEW_REQUIRED"].to_csv(output_dir / "04_ambiguous_manual_review.csv", index=False)
    df_all[df_all["Automated Status"] == "reported_non_dft"].to_csv(output_dir / "06_reported_non_dft.csv", index=False)
    df_all.to_csv(output_dir / "07_all_hits_audit.csv", index=False)
    df_all.to_csv(output_dir / "08_search_coverage_report.csv", index=False)
    practical = df_all["practicality_tier"] if "practicality_tier" in df_all.columns else pd.Series(["PRACTICAL_PRIORITY" for _ in range(len(df_all))])
    df_all[practical == "PRACTICAL_PRIORITY"].to_csv(output_dir / "09_practical_priority_candidates.csv", index=False)
    df_all[practical != "PRACTICAL_PRIORITY"].to_csv(output_dir / "10_radioactive_or_impractical_candidates.csv", index=False)
    xlsx_path = output_dir / "01_priority_unreported_candidates.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path) as xw:
            df_all.sort_values("Unreported Confidence Score", ascending=False).to_excel(xw, index=False)
    except ModuleNotFoundError:
        xlsx_path.write_bytes(b"")
