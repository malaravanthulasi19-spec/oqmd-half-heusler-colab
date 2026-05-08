from pathlib import Path
import pandas as pd
try:
    from openpyxl.styles import Alignment, Font, PatternFill
except ModuleNotFoundError:
    Alignment = Font = PatternFill = None


DECISION_PRIORITY = [
    "RECOMMENDED_NOVEL_CANDIDATE",
    "STRONG_NOVEL_CANDIDATE_MANUAL_VERIFY",
    "NOVEL_BUT_MODERATE_STABILITY",
    "EXPENSIVE_RARE_BACKUP",
    "NOVEL_BUT_LOW_STABILITY",
    "AMBIGUOUS_PRIOR_WORK_REVIEW",
    "REPORTED_DFT_DEFER",
    "DEEP_PRIOR_STUDY_DEFER",
    "TOXICITY_REVIEW_DEFER",
    "RADIOACTIVE_DEFER",
    "HIGHLY_IMPRACTICAL_DEFER",
    "INCOMPLETE_SEARCH_RETRY",
    "LOWER_PRIORITY_REVIEW",
]

def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def make_paper_link(best_url, best_doi) -> str:
    if pd.notna(best_url) and str(best_url).strip():
        return str(best_url).strip()
    if pd.notna(best_doi) and str(best_doi).strip():
        doi = str(best_doi).strip()
        return doi if doi.startswith("http") else f"https://doi.org/{doi}"
    return ""


def assign_material_decision_status(row: dict) -> dict:
    status = row.get("Automated Status", "")
    reported_depth = _to_float(row.get("reported_depth_score", 0), 0)
    keypaper_depth = _to_float(row.get("keypaper_depth_score", 0), 0)
    practicality = row.get("practicality_tier", "")
    stability = _to_float(row.get("Stability", 0), 0)
    final_selection_score = _to_float(row.get("final_selection_score", 0), 0)
    literature_risk = _to_float(row.get("literature_risk_penalty", 0), 0)
    novelty_tier = row.get("novelty_confidence_tier", "")
    band_gap = _to_float(row.get("Band Gap (eV)", 0), 0)
    link = make_paper_link(row.get("best_url", ""), row.get("best_doi", ""))

    if status == "reported_dft":
        return {"material_decision_status": "REPORTED_DFT_DEFER", "material_decision_reason": "Reported DFT/property evidence found; do not claim as novel", "paper_link_if_reported": link, "final_recommendation": "Use as reference/comparison only"}
    if reported_depth >= 75 or keypaper_depth >= 80:
        return {"material_decision_status": "DEEP_PRIOR_STUDY_DEFER", "material_decision_reason": "Deep prior DFT/property study detected", "paper_link_if_reported": link, "final_recommendation": "Do not use as novelty candidate without manual citation review"}
    if status == "ambiguous_manual_review":
        return {"material_decision_status": "AMBIGUOUS_PRIOR_WORK_REVIEW", "material_decision_reason": "Formula-level or material-context evidence needs manual review", "paper_link_if_reported": link, "final_recommendation": "Manual literature check required"}
    if bool(row.get("source_error", False)) or status == "incomplete_search_retry_needed":
        return {"material_decision_status": "INCOMPLETE_SEARCH_RETRY", "material_decision_reason": "Search coverage incomplete", "paper_link_if_reported": "", "final_recommendation": "Rerun search before using this material"}
    if practicality == "HIGHLY_IMPRACTICAL":
        return {"material_decision_status": "HIGHLY_IMPRACTICAL_DEFER", "material_decision_reason": "Contains highly impractical radioactive/actinide element", "paper_link_if_reported": link, "final_recommendation": "Do not prioritize"}
    if practicality == "RADIOACTIVE_REVIEW":
        return {"material_decision_status": "RADIOACTIVE_DEFER", "material_decision_reason": "Contains radioactive element", "paper_link_if_reported": link, "final_recommendation": "Do not prioritize unless actinide chemistry is intended"}
    if practicality == "TOXICITY_REVIEW":
        return {"material_decision_status": "TOXICITY_REVIEW_DEFER", "material_decision_reason": "Contains toxic/problematic element", "paper_link_if_reported": link, "final_recommendation": "Avoid for first paper candidate"}
    if practicality == "EXPENSIVE_RARE_REVIEW":
        return {"material_decision_status": "EXPENSIVE_RARE_BACKUP", "material_decision_reason": "Contains expensive/rare element", "paper_link_if_reported": link, "final_recommendation": "Keep as backup, not first choice"}
    if status == "not_found_after_protocol" and novelty_tier == "HIGH_CONFIDENCE_UNREPORTED" and practicality == "PRACTICAL_PRIORITY" and stability <= 0.10 and final_selection_score >= 80 and literature_risk < 30:
        return {"material_decision_status": "RECOMMENDED_NOVEL_CANDIDATE", "material_decision_reason": "Stable, practical, C1b/F-43m candidate with high unreported confidence", "paper_link_if_reported": "", "final_recommendation": "Top candidate for manual confirmation and DFT study"}
    if status == "not_found_after_protocol" and novelty_tier == "HIGH_CONFIDENCE_UNREPORTED" and practicality == "PRACTICAL_PRIORITY" and stability <= 0.10 and final_selection_score >= 65 and literature_risk < 50:
        return {"material_decision_status": "STRONG_NOVEL_CANDIDATE_MANUAL_VERIFY", "material_decision_reason": "Good unreported candidate; verify manually before selection", "paper_link_if_reported": "", "final_recommendation": "Manual Google Scholar check recommended"}
    if status == "not_found_after_protocol" and 0.10 < stability <= 0.30:
        return {"material_decision_status": "NOVEL_BUT_MODERATE_STABILITY", "material_decision_reason": "Potentially unreported, but OQMD stability is moderate", "paper_link_if_reported": "", "final_recommendation": "Use as backup candidate"}
    if status == "not_found_after_protocol" and stability > 0.30:
        return {"material_decision_status": "NOVEL_BUT_LOW_STABILITY", "material_decision_reason": "Likely unreported, but OQMD stability is weak", "paper_link_if_reported": "", "final_recommendation": "Lower priority unless metastability is acceptable"}
    if status == "not_found_after_protocol" and band_gap > 5:
        return {"material_decision_status": "NOVEL_BUT_APPLICATION_MISMATCH", "material_decision_reason": "Band gap too high for thermoelectric priority", "paper_link_if_reported": "", "final_recommendation": "Not ideal for thermoelectric/spintronic priority"}
    return {"material_decision_status": "LOWER_PRIORITY_REVIEW", "material_decision_reason": "No disqualifying reported evidence, but material score is not high enough", "paper_link_if_reported": link, "final_recommendation": "Keep for later review"}


def _style_sheet(ws):
    if not Font or not Alignment:
        return
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for c in ws[1]:
        c.font = Font(bold=True)
    wrap_cols = {"T", "U", "V", "W", "X"}
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max_len + 2, 60)
        if letter in wrap_cols:
            for cell in col:
                cell.alignment = Alignment(wrap_text=True, vertical="top")


def export_material_screening_master(rows, hits, coverage, output_dir) -> Path:
    output_dir = Path(output_dir)
    out_path = output_dir / "13_material_screening_master.xlsx"
    df = pd.DataFrame(rows).copy()
    decision_df = pd.DataFrame([assign_material_decision_status(r) for r in df.to_dict(orient="records")])
    df = pd.concat([df, decision_df], axis=1)
    df["_decision"] = pd.Categorical(df["material_decision_status"], categories=DECISION_PRIORITY, ordered=True)
    for col in ["final_selection_score", "Stability", "literature_risk_penalty"]:
        if col not in df.columns:
            df[col] = 0
    final_decision = df.sort_values(["_decision", "final_selection_score", "Stability", "literature_risk_penalty"], ascending=[True, False, True, True]).drop(columns=["_decision"])
    fd_cols = ["Rank","Material","Band Gap (eV)","Stability","Formation Energy / ΔE","Space Group","Prototype","Automated Status","material_decision_status","Unreported Confidence Score","novelty_confidence_tier","reported_depth_score","keypaper_depth_score","final_selection_score","final_material_priority_tier","practicality_tier","radioactive_elements","highly_toxic_elements","expensive_rare_elements","best_paper_title","paper_link_if_reported","material_decision_reason","final_recommendation","reviewer_notes"]
    top10_cols = ["Rank","Material","Composition","Band Gap (eV)","Formation Energy / ΔE","Stability","Prototype","Space Group","OQMD Entry ID","Automated Status","Reason","material_decision_status","material_decision_reason","final_recommendation","paper_link_if_reported","Unreported Confidence Score","Reported Evidence Score","novelty_confidence_tier","formula_level_evidence_found","exact_formula_hit_count","dft_formula_hit_count","reported_depth_score","reported_depth_tier","keypaper_depth_score","keypaper_depth_tier","keypaper_context_groups_detected","novelty_score","half_heusler_validity_score","stability_score","practicality_score","application_score","literature_risk_penalty","metadata_quality_score","final_selection_score","final_material_priority_tier","practicality_tier","input_half_heusler_verified","literature_half_heusler_context_found","half_heusler_filter_status","best_paper_title","best_doi","best_url","reviewer_notes"]
    for cols in [fd_cols, top10_cols]:
        for c in cols:
            if c not in final_decision.columns:
                final_decision[c] = ""
    try:
        writer = pd.ExcelWriter(out_path, engine="openpyxl")
    except ModuleNotFoundError:
        out_path.write_bytes(b"")
        return out_path
    with writer as xw:
        final_decision[fd_cols].to_excel(xw, sheet_name="Final_Decision", index=False)
        final_decision[final_decision["material_decision_status"] == "RECOMMENDED_NOVEL_CANDIDATE"][fd_cols].to_excel(xw, "Recommended_Novel", index=False)
        final_decision[final_decision["material_decision_status"].isin(["STRONG_NOVEL_CANDIDATE_MANUAL_VERIFY","AMBIGUOUS_PRIOR_WORK_REVIEW"])][fd_cols].to_excel(xw, "Strong_Manual_Verify", index=False)
        final_decision[final_decision["material_decision_status"].isin(["NOVEL_BUT_MODERATE_STABILITY","EXPENSIVE_RARE_BACKUP","NOVEL_BUT_LOW_STABILITY","LOWER_PRIORITY_REVIEW"])][fd_cols].to_excel(xw, "Backup_Candidates", index=False)
        final_decision[final_decision["material_decision_status"].isin(["REPORTED_DFT_DEFER","DEEP_PRIOR_STUDY_DEFER","TOXICITY_REVIEW_DEFER","RADIOACTIVE_DEFER","HIGHLY_IMPRACTICAL_DEFER","INCOMPLETE_SEARCH_RETRY","NOVEL_BUT_APPLICATION_MISMATCH"])][fd_cols].to_excel(xw, "Reported_or_Defer", index=False)
        final_decision[top10_cols].to_excel(xw, "All_Top10", index=False)
        (pd.DataFrame(hits) if hits else pd.DataFrame([{"note":"No hit audit rows available for this run."}])).to_excel(xw, "All_Hits_Audit", index=False)
        (pd.DataFrame(coverage) if coverage else pd.DataFrame([{"note":"No search coverage rows available for this run."}])).to_excel(xw, "Search_Coverage", index=False)
        pd.DataFrame({"Legend":["Use Recommended_Novel first.","Use Strong_Manual_Verify only after manual literature checking.","Do not claim novelty for Reported_or_Defer rows.","paper_link_if_reported gives the DOI or URL when reported evidence exists.","Automated Status is literature-status label; material_decision_status is selection label."]}).to_excel(xw, "Legend", index=False)
        wb = xw.book
        fill_map = {"RECOMMENDED_NOVEL_CANDIDATE":"C6EFCE","STRONG_NOVEL_CANDIDATE_MANUAL_VERIFY":"E2F0D9","NOVEL_BUT_MODERATE_STABILITY":"FFF2CC","EXPENSIVE_RARE_BACKUP":"FFF2CC","NOVEL_BUT_LOW_STABILITY":"FFF2CC","AMBIGUOUS_PRIOR_WORK_REVIEW":"FCE4D6"}
        red = "F8CBAD"
        for ws in wb.worksheets:
            _style_sheet(ws)
            if ws.title in {"Final_Decision","Recommended_Novel","Strong_Manual_Verify","Backup_Candidates","Reported_or_Defer","All_Top10"}:
                headers = [c.value for c in ws[1]]
                if "material_decision_status" in headers:
                    ci = headers.index("material_decision_status") + 1
                    for r in range(2, ws.max_row + 1):
                        v = ws.cell(r, ci).value
                        color = fill_map.get(v, red if str(v).endswith("DEFER") or v in {"INCOMPLETE_SEARCH_RETRY"} else None)
                        if color and PatternFill:
                            ws.cell(r, ci).fill = PatternFill(fill_type="solid", fgColor=color)
    return out_path


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
    for col in ["final_selection_score", "keypaper_depth_score", "practicality_score", "stability_score", "literature_risk_penalty"]:
        if col not in ranking.columns:
            ranking[col] = 0
    ranking = ranking.sort_values(["_tier", "final_selection_score", "keypaper_depth_score", "practicality_score", "stability_score", "literature_risk_penalty"], ascending=[True, False, True, False, False, True]).drop(columns=["_tier"])
    ranking.head(10).to_csv(output_dir / "11_top10_final_research_candidates.csv", index=False)

    xlsx_path = output_dir / "01_priority_unreported_candidates.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path) as xw:
            ranking.to_excel(xw, index=False)
    except ModuleNotFoundError:
        xlsx_path.write_bytes(b"")
