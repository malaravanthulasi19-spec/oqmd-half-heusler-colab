from __future__ import annotations

import re


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1","true","yes","y"}


def _to_float(v):
    try:
        if v is None or str(v).strip()=="":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(x, low=0.0, high=100.0):
    return max(low, min(high, x))


def _elements(material: str) -> set[str]:
    return set(re.findall(r"[A-Z][a-z]?", material or ""))


def compute_material_selection_scores(row: dict) -> dict:
    status = str(row.get("Automated Status", "")).strip()
    prototype = str(row.get("Prototype", ""))
    space_group = str(row.get("Space Group", ""))
    material = str(row.get("Material", ""))
    depth = _to_float(row.get("reported_depth_score")) or 0.0
    keypaper_depth = _to_float(row.get("keypaper_depth_score")) or 0.0
    stability = _to_float(row.get("Stability"))
    d_e = _to_float(row.get("Formation Energy / ΔE"))
    band_gap = _to_float(row.get("Band Gap (eV)"))

    novelty = 0
    novelty += 35 if status == "not_found_after_protocol" else 0
    novelty += 25 if not _to_bool(row.get("formula_level_evidence_found")) else 0
    novelty += 15 if (_to_float(row.get("exact_formula_hit_count")) or 0) == 0 else 0
    novelty += 15 if (_to_float(row.get("dft_formula_hit_count")) or 0) == 0 else 0
    novelty += 5 if _to_bool(row.get("google_scholar_checked")) else 0
    novelty += 5 if _to_bool(row.get("openalex_checked")) else 0
    novelty += 5 if _to_bool(row.get("semantic_scholar_checked")) else 0
    novelty -= 60 if status == "reported_dft" else 0
    novelty -= 45 if status == "reported_non_dft" else 0
    novelty -= 35 if status == "ambiguous_manual_review" else 0
    novelty -= 30 if _to_bool(row.get("source_error")) else 0
    novelty -= 50 if depth >= 75 else 30 if depth >= 50 else 0
    novelty -= 45 if keypaper_depth >= 80 else 25 if keypaper_depth >= 60 else 0
    novelty = _clamp(novelty)

    proto_half = any(k in prototype.lower() for k in ["c1b", "halfheusler", "half-heusler", "mgagas"])
    proto_non_half = any(k in prototype.lower() for k in ["full-heusler", "l21", "perovskite", "rocksalt"])
    lit_hh = _to_bool(row.get("literature_half_heusler_context_found"))
    validity = 0
    validity += 40 if proto_half else 0
    validity += 30 if space_group == "F-43m" else 0
    validity += 15 if lit_hh else 0
    validity += 10 if _to_bool(row.get("input_half_heusler_verified")) else 0
    validity += 5 if str(row.get("OQMD Entry ID", "")).strip() else 0
    validity -= 60 if proto_non_half else 0
    validity -= 40 if (space_group != "F-43m" and not lit_hh) else 0
    validity = _clamp(validity)

    stability_score = 0
    if stability is not None:
        stability_score += 40 if stability <= 0.05 else 35 if stability <= 0.10 else 25 if stability <= 0.20 else 10 if stability <= 0.30 else -40
    if d_e is not None:
        stability_score += 30 if d_e < 0 else -20 if d_e > 0 else 0
    elif stability is not None and stability <= 0.10:
        stability_score += 10
    stability_score += 10 if space_group == "F-43m" else 0
    stability_score += 10 if proto_half else 0
    stability_score = _clamp(stability_score)

    elems = _elements(material)
    radioactive_hi = sorted(elems & {"Ac", "Pa", "Np", "Pu"})
    radioactive = sorted(elems & {"U", "Th", "Pm", "Tc"})
    toxic = sorted(elems & {"Hg", "Cd", "Tl", "Pb", "As"})
    expensive = sorted(elems & {"Ir", "Pt", "Rh", "Pd", "Re", "Os", "Ru"})
    lanthanides = elems & {"La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu"}
    actinides = elems & {"Ac","Th","Pa","U","Np","Pu"}

    practicality = 100
    practicality -= 95 if elems & {"Pu", "Np"} else 0
    practicality -= 90 if elems & {"Ac", "Pa"} else 0
    practicality -= 75 if elems & {"U", "Th"} else 0
    practicality -= 65 if elems & {"Pm", "Tc"} else 0
    practicality -= 60 if "Hg" in elems else 0
    practicality -= 50 if elems & {"Cd", "Tl"} else 0
    practicality -= 40 if elems & {"Pb", "As"} else 0
    practicality -= 25 if elems & {"Ir", "Pt", "Rh", "Pd", "Re", "Os"} else 0
    practicality -= 15 if "Ru" in elems else 0
    practicality -= 10 if len(lanthanides) > 1 else 0
    practicality -= 20 if lanthanides and actinides else 0
    practicality += 10 if elems & {"Fe","Co","Ni","Ti","V","Nb","Ta","Zr","Hf","Sn","Sb","Bi"} else 0
    practicality += 10 if stability is not None and stability <= 0.10 else 0
    practicality = _clamp(practicality)

    contains_radio = bool(radioactive_hi or radioactive)
    contains_toxic = bool(toxic)
    contains_exp = bool(expensive)
    if radioactive_hi:
        practicality_tier = "HIGHLY_IMPRACTICAL"
    elif radioactive:
        practicality_tier = "RADIOACTIVE_REVIEW"
    elif toxic:
        practicality_tier = "TOXICITY_REVIEW"
    elif contains_exp:
        practicality_tier = "EXPENSIVE_RARE_REVIEW"
    elif practicality >= 80 and not contains_radio and not contains_toxic:
        practicality_tier = "PRACTICAL_PRIORITY"
    else:
        practicality_tier = "PRACTICAL_PRIORITY"

    app = 0
    if band_gap is not None:
        app += 20 if 0.05 <= band_gap < 1.5 else 15 if 1.5 <= band_gap <= 3.0 else 5 if 3.0 < band_gap <= 5.0 else -30 if band_gap > 5.0 else 0
    for k,w in [("has_thermoelectric_context",15),("has_half_metal_context",20),("has_ferromagnetic_context",15),("has_spintronic_context",10),("has_dft_context",10),("has_phonon_context",10),("has_mechanical_stability_context",10),("has_stability_context",10),("has_keypaper_thermoelectric_context",15),("has_keypaper_magnetic_spintronic_context",15),("has_keypaper_phonon_context",10),("has_keypaper_mechanical_context",10),("has_keypaper_electronic_context",10)]:
        app += w if _to_bool(row.get(k)) else 0
    text = (str(row.get("property_groups_detected", "")) + " " + str(row.get("best_paper_title", ""))).lower()
    if any(t in text for t in ["seebeck","zt","power factor","thermal conductivity"]): app += 10
    if any(t in text for t in ["boltztrap","crta","dpt"]): app += 10
    if any(t in text for t in ["slack","aimd","low thermal conductivity"]): app += 10
    if "spin polar" in text: app += 15
    app = _clamp(app)

    lit_pen = 0
    lit_pen += 80 if depth >= 75 else 0
    lit_pen += 85 if keypaper_depth >= 80 else 45 if keypaper_depth >= 60 else 0
    lit_pen += 60 if status == "reported_dft" else 45 if status == "reported_non_dft" else 35 if status == "ambiguous_manual_review" else 0
    lit_pen += 25 if _to_bool(row.get("formula_level_evidence_found")) else 0
    lit_pen += 20 if (_to_float(row.get("exact_formula_hit_count")) or 0) > 0 else 0
    lit_pen += 20 if (_to_float(row.get("dft_formula_hit_count")) or 0) > 0 else 0
    lit_pen += 15 if str(row.get("best_paper_title", "")).strip() else 0
    lit_pen += 10 if str(row.get("best_doi", "")).strip() else 0
    lit_pen = _clamp(lit_pen)

    meta = 0
    for col, w in [("Material",20),("Composition",15),("Band Gap (eV)",15),("Stability",15),("Formation Energy / ΔE",15),("Prototype",10),("Space Group",10),("OQMD Entry ID",10)]:
        val = row.get(col)
        if val is not None and str(val).strip() != "":
            meta += w
    meta = _clamp(meta)

    final = _clamp(0.25*novelty + 0.20*stability_score + 0.20*practicality + 0.15*validity + 0.15*app + 0.05*meta - 0.25*lit_pen)

    if final < 35 or practicality_tier in {"HIGHLY_IMPRACTICAL","RADIOACTIVE_REVIEW"} or depth >= 75 or keypaper_depth >= 80 or status == "reported_dft":
        tier = "DEFER"
    elif final >= 80 and practicality_tier == "PRACTICAL_PRIORITY" and novelty >= 70 and validity >= 70 and stability_score >= 60 and lit_pen < 30 and stability is not None and stability <= 0.30 and (proto_half or space_group=="F-43m"):
        tier = "TOP_RESEARCH_PRIORITY"
    elif final >= 65 and practicality_tier != "HIGHLY_IMPRACTICAL" and lit_pen < 50:
        tier = "HIGH_RESEARCH_PRIORITY"
    elif final >= 50:
        tier = "MEDIUM_RESEARCH_PRIORITY"
    elif final >= 35:
        tier = "LOW_RESEARCH_PRIORITY"
    else:
        tier = "DEFER"

    reason = "Possible candidate but stability is weak" if stability is not None and stability > 0.30 else "Strong unreported C1b candidate with good stability and practical elements"
    if tier == "DEFER" and status == "reported_dft" or depth >= 75:
        reason = "Reported DFT/deep prior study detected; not a novelty candidate"
    elif tier == "DEFER" and practicality_tier in {"HIGHLY_IMPRACTICAL","RADIOACTIVE_REVIEW"}:
        reason = "Unreported but radioactive/impractical; defer"
    elif _to_bool(row.get("formula_level_evidence_found")) and status == "ambiguous_manual_review":
        reason = "Formula-level literature evidence detected; manual review required"
    elif validity >= 70 and app < 30:
        reason = "C1b/F-43m confirmed but application score is low"

    return {
        "novelty_score": novelty,
        "half_heusler_validity_score": validity,
        "stability_score": stability_score,
        "practicality_score": practicality,
        "application_score": app,
        "literature_risk_penalty": lit_pen,
        "metadata_quality_score": meta,
        "final_selection_score": final,
        "final_material_priority_tier": tier,
        "selection_reason": reason,
        "contains_radioactive_element": contains_radio,
        "radioactive_elements": ",".join(radioactive_hi + radioactive),
        "contains_highly_toxic_element": contains_toxic,
        "highly_toxic_elements": ",".join(toxic),
        "contains_expensive_rare_element": contains_exp,
        "expensive_rare_elements": ",".join(expensive),
        "practicality_tier": practicality_tier,
    }
