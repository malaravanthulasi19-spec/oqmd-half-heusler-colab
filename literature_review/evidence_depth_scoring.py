from __future__ import annotations


def _contains_any(text: str, terms: list[str]) -> bool:
    t = (text or "").lower()
    return any(term in t for term in terms)


def compute_reported_depth_score(hit_or_row: dict) -> dict:
    text = " ".join(str(hit_or_row.get(k, "") or "") for k in ["title", "snippet", "abstract", "text"])
    text_l = text.lower()

    formula_evidence_score = 0
    if hit_or_row.get("exact_formula_match"):
        formula_evidence_score += 10
    if hit_or_row.get("spaced_formula_match"):
        formula_evidence_score += 8
    if hit_or_row.get("hyphenated_formula_match"):
        formula_evidence_score += 8
    if hit_or_row.get("alloy_doped_formula_match"):
        formula_evidence_score += 8
    if hit_or_row.get("formula_permutation_match"):
        formula_evidence_score += 5

    half_heusler_context_score = 0
    if _contains_any(text_l, ["half-heusler", "half heusler", "hh alloy", "hh compound"]):
        half_heusler_context_score += 10
    if _contains_any(text_l, ["c1b", "mgagas", "f-43m", "space group 216"]):
        half_heusler_context_score += 8

    dft_method_score = 0
    if _contains_any(text_l, ["dft", "density functional theory", "first principles", "first-principles", "ab initio"]):
        dft_method_score += 20
    if _contains_any(text_l, ["wien2k", "quantum espresso", "vasp", "fp-lapw", "gga", "pbe", "tb-mbj", "mbj", "hse06"]):
        dft_method_score += 10

    property_groups_detected = []
    groups = {
        "dos": (["dos", "density of states"], 8),
        "band_structure": (["band structure", "electronic structure", "band gap"], 8),
        "mechanical": (["mechanical stability", "elastic constants", "c11", "c12", "c44", "bulk modulus", "shear modulus", "young's modulus"], 8),
        "phonon": (["phonon dispersion", "dynamical stability", "imaginary frequency", "negative phonon frequency"], 8),
        "optical": (["optical properties"], 8),
        "thermodynamic": (["thermodynamic properties", "gibbs", "debye temperature"], 8),
        "thermoelectric": (["thermoelectric", "seebeck", "zt", "power factor", "thermal conductivity", "boltztrap"], 10),
        "magnetic_spintronic": (["magnetic", "ferromagnetic", "spin polarization", "half-metal", "spintronic"], 8),
    }
    property_depth_score = 0
    for name, (terms, points) in groups.items():
        if _contains_any(text_l, terms):
            property_groups_detected.append(name)
            property_depth_score += points

    if len(property_groups_detected) >= 6:
        property_depth_score += 15
    elif len(property_groups_detected) >= 4:
        property_depth_score += 10

    false_positive_penalty = 0
    if bool(hit_or_row.get("false_positive_flag")):
        false_positive_penalty -= 50
    if hit_or_row.get("evidence_tier") == "TIER_1_ELEMENT_SYSTEM_WEAK":
        false_positive_penalty -= 30
    if not bool(hit_or_row.get("formula_level_evidence_found", False)):
        false_positive_penalty -= 30

    total = formula_evidence_score + half_heusler_context_score + dft_method_score + property_depth_score + false_positive_penalty
    reported_depth_score = max(0, min(100, total))

    if reported_depth_score <= 9:
        tier = "NO_VALID_EVIDENCE"
    elif reported_depth_score <= 29:
        tier = "FORMULA_MENTION_ONLY"
    elif reported_depth_score <= 49:
        tier = "MATERIAL_CONTEXT_REPORTED"
    elif reported_depth_score <= 74:
        tier = "REPORTED_DFT_BASIC"
    else:
        tier = "REPORTED_DFT_DEEP_STUDY"

    manual_warning = ""
    if reported_depth_score >= 75:
        manual_warning = "deep prior DFT/property study detected; do not claim as unreported without manual citation check"
    elif reported_depth_score >= 50:
        manual_warning = "DFT-level report detected; verify manually before novelty claim"
    elif reported_depth_score >= 30:
        manual_warning = "material-level context detected; check citation manually"

    return {
        "reported_depth_score": reported_depth_score,
        "reported_depth_tier": tier,
        "property_groups_detected": ",".join(property_groups_detected),
        "formula_evidence_score": formula_evidence_score,
        "half_heusler_context_score": half_heusler_context_score,
        "dft_method_score": dft_method_score,
        "property_depth_score": property_depth_score,
        "false_positive_penalty": false_positive_penalty,
        "manual_warning": manual_warning,
    }
