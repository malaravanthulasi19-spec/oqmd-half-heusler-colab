from __future__ import annotations

from .composition_equivalence import canonical_element_set

KNOWN_REPORTED_MATERIALS = {
    "TiFeTe": {
        "doi": "10.1039/d5cp04054j",
        "url": "https://www.semanticscholar.org/paper/7826de92898541c6712527f0d38ab950b44177d0",
        "reason": "Earlier screening found reported DFT/property evidence",
    }
}



KNOWN_REPORTED_COMPOSITIONS = {
    canonical_element_set("ScCoTe"): {"status": "REPORTED_DFT", "doi": "10.1039/D3CP01478A", "title": "Investigation of the electronic structure, mechanical, and thermoelectric properties of novel semiconductor compounds: XYTe (X = Ti/Sc; Y = Fe/Co)"},
    canonical_element_set("TiFeTe"): {"status": "REPORTED_DFT", "doi": "10.1039/D3CP01478A", "title": "Investigation of the electronic structure, mechanical, and thermoelectric properties of novel semiconductor compounds: XYTe (X = Ti/Sc; Y = Fe/Co)"},
    canonical_element_set("ZrFeTe"): {"status": "REPORTED_DFT", "doi": "10.1007/s11664-023-10369-y", "title": "Stability and Thermoelectric Properties of FeZrTe Alloy"},
    canonical_element_set("ZrTeRu"): {"status": "REPORTED_DFT", "doi": "10.1088/1361-648X/ab9d49", "title": "Intrinsically high thermoelectric figure of merit of half-Heusler ZrRuTe"},
}

def _f(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _b(v):
    return bool(v)


def classify_literature_status(row: dict) -> dict:
    status = row.get("Automated Status", "")
    if status == "reported_dft":
        return {"literature_status": "REPORTED_DFT", "literature_status_reason": "automated reported_dft"}
    if status == "reported_non_dft":
        return {"literature_status": "REPORTED_NON_DFT", "literature_status_reason": "automated reported_non_dft"}
    if _f(row.get("keypaper_depth_score"), 0) >= 80 or _f(row.get("reported_depth_score"), 0) >= 75:
        return {"literature_status": "DEEP_PRIOR_STUDY", "literature_status_reason": "depth score indicates strong prior study"}
    if status == "ambiguous_manual_review":
        return {"literature_status": "AMBIGUOUS_PRIOR_WORK", "literature_status_reason": "automated ambiguous/manual review"}
    if _b(row.get("source_error")) or status == "incomplete_search_retry_needed":
        return {"literature_status": "INCOMPLETE_SEARCH", "literature_status_reason": "source error or incomplete retry required"}
    if _f(row.get("false_positive_count"), 0) > 0 and _f(row.get("valid_evidence_hit_count"), 0) == 0:
        return {"literature_status": "FALSE_POSITIVE_ONLY", "literature_status_reason": "only false-positive hits found"}
    if status == "not_found_after_protocol" and not _b(row.get("formula_level_evidence_found")) and _f(row.get("exact_formula_hit_count"), 0) == 0 and _f(row.get("dft_formula_hit_count"), 0) == 0 and _b(row.get("google_scholar_checked")) and _b(row.get("openalex_checked")):
        return {"literature_status": "HIGH_CONFIDENCE_NOT_FOUND", "literature_status_reason": "not found after complete primary-source checks"}
    if status == "not_found_after_protocol":
        return {"literature_status": "MEDIUM_CONFIDENCE_NOT_FOUND", "literature_status_reason": "not found after protocol, but coverage/evidence weaker"}
    return {"literature_status": "INCOMPLETE_SEARCH", "literature_status_reason": "fallback"}


def load_prior_material_evidence(conn, material: str) -> dict:
    base = {
        "prior_conflict_flag": False,
        "prior_reported_status": "",
        "prior_best_paper_title": "",
        "prior_best_doi": "",
        "prior_best_url": "",
        "prior_exact_formula_hit_count": 0,
        "prior_dft_formula_hit_count": 0,
        "prior_evidence_sources": "",
        "known_reported_composition_flag": False,
    }
    cset = canonical_element_set(material)
    if material in KNOWN_REPORTED_MATERIALS:
        item = KNOWN_REPORTED_MATERIALS[material]
        return {**base, "prior_conflict_flag": True, "prior_reported_status": "KNOWN_REPORTED_OVERRIDE", "known_reported_composition_flag": True, "prior_best_doi": item.get("doi", ""), "prior_best_url": item.get("url", "")}
    if cset in KNOWN_REPORTED_COMPOSITIONS:
        item = KNOWN_REPORTED_COMPOSITIONS[cset]
        doi = item.get("doi", "")
        return {**base, "prior_conflict_flag": True, "known_reported_composition_flag": True, "prior_reported_status": item.get("status", "KNOWN_REPORTED_OVERRIDE"), "prior_best_paper_title": item.get("title", ""), "prior_best_doi": doi, "prior_best_url": f"https://doi.org/{doi}" if doi else ""}
    if conn is None:
        return base
    row = conn.execute("SELECT automated_status, best_matching_paper, doi, url FROM classifications WHERE material=?", (material,)).fetchone()
    if not row:
        return base
    status, title, doi, url = row
    conflict = status in {"reported_dft", "reported_non_dft", "ambiguous_manual_review"}
    src = [x[0] for x in conn.execute("SELECT DISTINCT source FROM hits WHERE material=?", (material,)).fetchall()]
    return {**base, "prior_conflict_flag": bool(conflict), "prior_reported_status": status or "", "prior_best_paper_title": title or "", "prior_best_doi": doi or "", "prior_best_url": url or "", "prior_evidence_sources": "|".join(src)}

