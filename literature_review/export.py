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
    xlsx_path = output_dir / "01_priority_unreported_candidates.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path) as xw:
            df_all.sort_values("Unreported Confidence Score", ascending=False).to_excel(xw, index=False)
    except ModuleNotFoundError:
        xlsx_path.write_bytes(b"")
