from literature_review.keypaper_filters import detect_keypaper_context, compute_keypaper_depth_score


def test_detect_all_keypaper_groups():
    text = "TiNiSn half-Heusler C1b F-43m formation energy OQMD elastic constants C11 C12 C44 Born-Huang phonon dispersion electronic band structure DOS spin polarization ferromagnetic Slater-Pauling thermoelectric Seebeck ZT BoltzTrap2 DFT VASP GIBBS2"
    d = detect_keypaper_context(text)
    assert d["has_keypaper_structure_context"]
    assert d["has_keypaper_stability_context"]
    assert d["has_keypaper_mechanical_context"]
    assert d["has_keypaper_phonon_context"]
    assert d["has_keypaper_electronic_context"]
    assert d["has_keypaper_magnetic_spintronic_context"]
    assert d["has_keypaper_thermoelectric_context"]
    assert d["has_keypaper_method_context"]


def test_keypaper_depth_penalties():
    deep = compute_keypaper_depth_score({"formula_level_evidence_found": True, **{f"has_keypaper_{g}_context": True for g in ["structure","stability","mechanical","phonon","electronic","magnetic_spintronic","thermoelectric","method"]}})
    assert deep["keypaper_depth_tier"] == "DEEP_KEYPAPER_STYLE_STUDY"
    weak = compute_keypaper_depth_score({"formula_level_evidence_found": False, "has_keypaper_structure_context": True, "evidence_tier": "TIER_1_ELEMENT_SYSTEM_WEAK", "false_positive_flag": True})
    assert weak["keypaper_depth_score"] == 0
