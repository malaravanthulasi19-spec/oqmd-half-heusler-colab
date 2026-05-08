from .constants import GATE2_TERMS, GATE3_TERMS
from .formula_variants import FormulaVariants


def _dedupe_clean(queries: list[str]) -> list[str]:
    seen = set()
    out = []
    for q in queries:
        cleaned = " ".join(str(q).split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out
def gate1_queries(v: FormulaVariants) -> list[str]:
    return [v.compact, v.spaced, v.hyphenated]


def gate2_queries(v: FormulaVariants) -> list[str]:
    return [f'{v.compact} {term}' for term in GATE2_TERMS]


def gate3_queries(v: FormulaVariants) -> list[str]:
    return [f'{v.compact} {term}' for term in GATE3_TERMS]


def gate4_queries(v: FormulaVariants) -> list[str]:
    return v.permutations


def profile_queries(v: FormulaVariants, profile: str) -> dict[str, list[str]]:
    base = {
        "gate1": [f'"{v.compact}"', f'"{v.spaced}"', f'"{v.hyphenated}"'],
        "gate2": gate2_queries(v),
        "gate3": gate3_queries(v),
    }
    if profile == "validation_recall":
        base["gate2"] += [
            f'"{v.compact}" "half-Heusler alloy"', f'"{v.compact}" "half-Heusler compound"',
            f'"{v.compact}" "band structure"', f'"{v.compact}" "ab initio"', f'"{v.compact}" thermoelectric',
        ]
    if profile == "candidate_screening_expanded":
        dft = ["DFT", "density functional theory", "first principles", "first-principles", "ab initio", "FP-LAPW", "WIEN2k", "Quantum Espresso", "VASP", "GGA", "PBE", "TB-mBJ", "mBJ", "HSE06", "PAW", "SCF", "Kohn-Sham", "electronic structure", "electronic band structure", "band structure", "band gap", "DOS", "density of states", "total DOS", "partial DOS", "spin-up", "spin-down", "Fermi level", "VBM", "CBM", "BoltzTrap", "BoltzTrap2"]
        structure = ["half-Heusler", "half Heusler", "HH alloy", "HH alloys", "HH compound", "C1b", "MgAgAs", "F-43m", "space group 216", "face-centered cubic", "FCC", "XYZ", "Wyckoff positions", "lattice parameter", "structural optimization", "equilibrium geometry", "Birch-Murnaghan", "formation energy", "negative formation energy", "OQMD", "energy above hull", "thermodynamic stability", "structural stability", "ground-state energy", "synthesizable"]
        mech = ["mechanical stability", "elastic constants", "C11 C12 C44", "Born-Huang criteria", "Born and Huang criteria", "bulk modulus", "shear modulus", "Young's modulus", "Pugh's ratio", "Cauchy pressure", "Poisson's ratio", "Vickers hardness", "anisotropy factor", "phonon dispersion", "dynamical stability", "negative phonon frequency", "imaginary frequency", "acoustic modes", "optical modes", "phonon-phonon interaction", "Debye temperature", "Gruneisen parameter", "GIBBS2", "quasi-harmonic approximation", "thermodynamic properties"]
        mag = ["half-metal", "half-metallic", "half-metallicity", "100% spin polarization", "spin polarization", "ferromagnetic", "ferromagnetic ordering", "magnetic moment", "Slater-Pauling", "spintronic", "spintronics", "spin injector", "spin valve", "MRAM"]
        te = ["thermoelectric", "thermoelectric properties", "thermoelectric performance", "room-temperature thermoelectric", "thermoelectric device", "thermoelectric generator", "TEG", "Seebeck coefficient", "electrical conductivity", "thermal conductivity", "electronic thermal conductivity", "lattice thermal conductivity", "total thermal conductivity", "power factor", "figure of merit", "ZT", "zT", "Boltzmann transport", "BoltzTrap", "BoltzTrap2", "constant relaxation time approximation", "CRTA", "deformation potential theory", "DPT", "relaxation time", "effective mass", "deformation potential constant", "Slack equation", "Slack model", "AIMD", "ALAMODE", "low lattice thermal conductivity", "high Seebeck coefficient", "high electrical conductivity"]
        base["gate2"] = [f"{v.compact} {x}" for x in dft]
        base["gate3"] = [f"{v.compact} {x}" for x in (structure + mech + mag + te)]
        base["gate4"] = [f"{v.compact} {x}" for x in mech]
        base["gate5"] = [f"{v.compact} {x}" for x in mag]
        base["gate6"] = [f"{v.compact} {x}" for x in te]
    return {k: _dedupe_clean(vs) for k, vs in base.items()}
