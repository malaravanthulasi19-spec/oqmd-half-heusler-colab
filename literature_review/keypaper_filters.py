from __future__ import annotations

from .evidence_scoring import contains_any

STRUCTURE_KEYWORDS = ["half-Heusler", "half Heusler", "HH alloy", "HH alloys", "HH compound", "C1b", "MgAgAs", "F-43m", "space group 216", "face-centered cubic", "FCC", "XYZ", "Wyckoff positions", "lattice parameter", "structural optimization", "equilibrium geometry", "Birch-Murnaghan"]
STABILITY_KEYWORDS = ["formation energy", "negative formation energy", "stability value", "energy above hull", "OQMD", "thermodynamic stability", "structural stability", "synthesizable", "stable FCC materials", "minimum energy", "ground-state energy"]
MECHANICAL_KEYWORDS = ["mechanical stability", "elastic constants", "C11", "C12", "C44", "Born-Huang criteria", "Born and Huang criteria", "bulk modulus", "shear modulus", "Young's modulus", "Pugh's ratio", "Cauchy pressure", "Poisson's ratio", "Vickers hardness", "anisotropy factor", "Kleinman parameter", "ductile", "malleable"]
PHONON_KEYWORDS = ["phonon dispersion", "dynamical stability", "negative phonon frequency", "imaginary frequency", "absence of negative phonon frequencies", "acoustic modes", "optical modes", "phonon-phonon interaction", "lattice vibrations", "thermal stability"]
ELECTRONIC_KEYWORDS = ["electronic band structure", "band diagram", "DOS", "density of states", "total DOS", "partial DOS", "orbital contribution", "spin-up", "spin-down", "Fermi level", "VBM", "CBM", "band gap", "indirect band gap"]
MAGNETIC_SPINTRONIC_KEYWORDS = ["half-metal", "half-metallic", "half-metallicity", "100% spin polarization", "spin polarization", "ferromagnetic", "ferromagnetic ordering", "magnetic moment", "Slater-Pauling rule", "spintronic", "spintronics", "spin injector", "spin valve", "MRAM"]
THERMOELECTRIC_KEYWORDS = ["thermoelectric", "thermoelectric properties", "thermoelectric performance", "room-temperature thermoelectric", "thermoelectric device", "thermoelectric generator", "TEG", "Seebeck coefficient", "electrical conductivity", "thermal conductivity", "electronic thermal conductivity", "lattice thermal conductivity", "total thermal conductivity", "power factor", "figure of merit", "ZT", "zT", "Boltzmann transport", "constant relaxation time approximation", "CRTA", "deformation potential theory", "DPT", "relaxation time", "effective mass", "deformation potential constant", "Slack equation", "Slack model", "AIMD", "ALAMODE", "low lattice thermal conductivity", "high Seebeck coefficient", "high electrical conductivity"]
METHOD_KEYWORDS = ["DFT", "Density Functional Theory", "first principles", "first-principles", "ab initio", "FP-LAPW", "WIEN2k", "Quantum Espresso", "VASP", "GGA", "PBE", "TB-mBJ", "mBJ", "HSE06", "PAW", "SCF", "Kohn-Sham", "BoltzTrap", "BoltzTrap2", "GIBBS2", "quasi-harmonic approximation"]

GROUPS = {
    "structure": STRUCTURE_KEYWORDS,
    "stability": STABILITY_KEYWORDS,
    "mechanical": MECHANICAL_KEYWORDS,
    "phonon": PHONON_KEYWORDS,
    "electronic": ELECTRONIC_KEYWORDS,
    "magnetic_spintronic": MAGNETIC_SPINTRONIC_KEYWORDS,
    "thermoelectric": THERMOELECTRIC_KEYWORDS,
    "method": METHOD_KEYWORDS,
}


def detect_keypaper_context(text: str) -> dict:
    out = {}
    for name, kws in GROUPS.items():
        count = sum(1 for k in kws if contains_any(text, [k]))
        out[f"has_keypaper_{name}_context"] = count > 0
        out[f"keypaper_{name}_keyword_count"] = count
    return out


def compute_keypaper_depth_score(row_or_hit: dict) -> dict:
    s = 0
    formula = bool(row_or_hit.get("formula_level_evidence_found"))
    if formula:
        s += 10
    group_names = ["structure", "stability", "mechanical", "phonon", "electronic", "magnetic_spintronic", "thermoelectric", "method"]
    weights = {"thermoelectric": 15}
    present = 0
    for g in group_names:
        if row_or_hit.get(f"has_keypaper_{g}_context"):
            present += 1
            s += weights.get(g, 10)
    if present >= 7:
        s += 15
    elif present >= 5:
        s += 10
    if not formula:
        s -= 40
    if row_or_hit.get("false_positive_flag"):
        s -= 50
    if row_or_hit.get("evidence_tier") == "TIER_1_ELEMENT_SYSTEM_WEAK":
        s -= 30
    s = max(0, min(100, s))
    if s >= 80:
        tier = "DEEP_KEYPAPER_STYLE_STUDY"
        warn = "deep key-paper-style DFT/property study detected; do not claim novelty without manual citation check"
    elif s >= 60:
        tier = "STRONG_DFT_PROPERTY_STUDY"
        warn = "strong DFT/property evidence detected; verify before novelty claim"
    elif s >= 40:
        tier = "PARTIAL_DFT_PROPERTY_STUDY"
        warn = "partial DFT/property evidence detected; manual review recommended"
    elif s >= 20:
        tier = "FORMULA_OR_BASIC_CONTEXT_ONLY"
        warn = ""
    else:
        tier = "SHALLOW_OR_NO_RELEVANT_EVIDENCE"
        warn = ""
    return {
        "keypaper_depth_score": s,
        "keypaper_depth_tier": tier,
        "keypaper_context_groups_detected": present,
        "keypaper_manual_warning": warn,
    }
