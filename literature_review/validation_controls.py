from __future__ import annotations

from pathlib import Path
import pandas as pd

from .pipeline import run


POSITIVE_CONTROL_FORMULAS = [
    "NiTiSn",
    "TiNiSn",
    "ZrNiSn",
    "HfNiSn",
    "CoTiSb",
    "FeVSb",
    "NbFeSb",
    "ZrCoSb",
    "ScNiSb",
    "YNiSb",
]


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
    pd.DataFrame(
        [{"Material": formula, "Expected Label": "reported_positive_control"} for formula in POSITIVE_CONTROL_FORMULAS]
    ).to_csv(validation_input, index=False)

    run(
        top_n=len(POSITIVE_CONTROL_FORMULAS),
        input_csv=validation_input,
        db_path=db_path,
        output_dir=output_dir,
        enable_crossref=enable_crossref,
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
    validation.insert(1, "Expected Label", "reported_positive_control")

    formula_evidence = validation["formula_level_evidence_found"].astype(bool)
    dft_evidence = validation["dft_formula_hit_count"].fillna(0).astype(int) > 0
    not_found = validation["Automated Status"].eq("not_found_after_protocol")

    validation["pass_fail"] = "FAIL"
    validation.loc[formula_evidence & dft_evidence & ~not_found, "pass_fail"] = "PASS"

    validation["reason"] = "Formula-level evidence missing"
    validation.loc[formula_evidence & ~dft_evidence & ~not_found, "reason"] = (
        "Formula-level evidence found but no DFT/first-principles/electronic-structure context"
    )
    validation.loc[formula_evidence & dft_evidence & ~not_found, "reason"] = "Positive control recovered with formula-level + DFT context"
    validation.loc[not_found, "reason"] = "Known reported material classified as not_found_after_protocol"

    export_path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(export_path, index=False)
    return validation
