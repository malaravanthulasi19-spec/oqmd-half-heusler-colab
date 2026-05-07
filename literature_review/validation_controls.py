from __future__ import annotations

from pathlib import Path
import pandas as pd

from .pipeline import run
from .benchmark import POSITIVE_CONTROLS, NEGATIVE_CONTROLS


POSITIVE_CONTROL_FORMULAS = POSITIVE_CONTROLS


DEFAULT_VALIDATION_EXPORT = Path(
    "/content/drive/MyDrive/half_heusler_literature_survey/outputs/00_validation_controls.csv"
)


def run_validation_controls(
    db_path: Path,
    output_dir: Path,
    export_path: Path = DEFAULT_VALIDATION_EXPORT,
    enable_crossref: bool = False,
) -> pd.DataFrame:
    """Run positive-control validation on known half-Heusler materials."""
    output_dir = Path(output_dir)
    db_path = Path(db_path)
    export_path = Path(export_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    validation_input = output_dir / "validation_controls_input.csv"
    controls = ([{"Material": f, "Expected Label": "reported_positive_control"} for f in POSITIVE_CONTROL_FORMULAS] +
                [{"Material": x["material"], "Expected Label": "known_false_positive_control"} for x in NEGATIVE_CONTROLS])
    pd.DataFrame(controls).to_csv(validation_input, index=False)

    run(
        top_n=len(controls),
        input_csv=validation_input,
        db_path=db_path,
        output_dir=output_dir,
        enable_crossref=enable_crossref,
        search_profile="validation_recall",
        recall_second_pass=True,
    )

    audit_path = output_dir / "05_all_hits_audit.csv"
    audit = pd.read_csv(audit_path)

    validation = audit[[
        "Material",
        "Automated Status",
        "exact_formula_hit_count",
        "dft_formula_hit_count",
        "formula_level_evidence_found",
        "best_paper_title",
        "best_doi",
        "best_url",
        "Reason",
    ]].copy()
    exp = pd.read_csv(validation_input)
    validation = validation.merge(exp[["Material", "Expected Label"]], on="Material", how="left")

    formula_evidence = validation["formula_level_evidence_found"].astype(bool)
    dft_evidence = validation["dft_formula_hit_count"].fillna(0).astype(int) > 0
    not_found = validation["Automated Status"].eq("not_found_after_protocol")

    validation["pass_fail"] = "FAIL"
    pos = validation["Expected Label"].eq("reported_positive_control")
    neg = ~pos
    validation.loc[pos & formula_evidence & ~not_found, "pass_fail"] = "PASS"
    validation.loc[neg & ~validation["Automated Status"].isin(["reported_dft", "reported_non_dft"]), "pass_fail"] = "PASS"

    validation["reason"] = "Formula-level evidence missing"
    validation.loc[formula_evidence & ~dft_evidence & ~not_found, "reason"] = (
        "Formula-level evidence found but no DFT/first-principles/electronic-structure context"
    )
    validation.loc[formula_evidence & dft_evidence & ~not_found, "reason"] = "Positive control recovered with formula-level + DFT context"
    validation.loc[not_found, "reason"] = "Known reported material classified as not_found_after_protocol"

    export_path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(output_dir / "00_validation_controls.csv", index=False)
    pd.DataFrame().to_csv(output_dir / "00_validation_source_coverage.csv", index=False)
    validation.to_csv(output_dir / "00_validation_hits_audit.csv", index=False)
    validation[validation["pass_fail"] == "FAIL"].assign(likely_failure_mode="UNKNOWN").to_csv(output_dir / "00_validation_failure_diagnosis.csv", index=False)
    summary = {
        "positive_pass_count": int(((validation["Expected Label"] == "reported_positive_control") & (validation["pass_fail"] == "PASS")).sum()),
        "positive_total": int((validation["Expected Label"] == "reported_positive_control").sum()),
        "negative_false_positive_fail_count": int(((validation["Expected Label"] != "reported_positive_control") & (validation["pass_fail"] == "FAIL")).sum()),
    }
    summary["calibration_passed"] = summary["positive_pass_count"] >= 8 and summary["negative_false_positive_fail_count"] == 0
    pd.Series(summary).to_json(output_dir / "00_validation_summary.json")
    validation.to_csv(export_path, index=False)
    return validation[validation["Expected Label"] == "reported_positive_control"].copy()
