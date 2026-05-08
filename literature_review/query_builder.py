from .constants import GATE2_TERMS, GATE3_TERMS
from .formula_variants import FormulaVariants


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
            f'"{v.compact}" "half-Heusler alloy"',
            f'"{v.compact}" "half-Heusler compound"',
            f'"{v.compact}" "band structure"',
            f'"{v.compact}" "ab initio"',
            f'"{v.compact}" thermoelectric',
        ]
    if profile == "candidate_screening_expanded":
        base["gate1"] = [f'"{v.compact}"', f'"{v.spaced}"', f'"{v.hyphenated}"']
        base["gate2"] = [
            f"{v.compact} DFT",
            f"{v.compact} density functional theory",
            f"{v.compact} first principles",
            f"{v.compact} first-principles",
            f"{v.compact} ab initio",
            f"{v.compact} electronic structure",
            f"{v.compact} band structure",
            f"{v.compact} DOS",
            f"{v.compact} density of states",
            f"{v.compact} band gap",
            f"{v.compact} formation energy",
            f"{v.compact} GGA",
            f"{v.compact} PBE",
            f"{v.compact} TB-mBJ",
            f"{v.compact} mBJ",
            f"{v.compact} HSE06",
            f"{v.compact} WIEN2k",
            f"{v.compact} Quantum Espresso",
            f"{v.compact} VASP",
            f"{v.compact} FP-LAPW",
            f"{v.compact} BoltzTrap",
            f"{v.compact} BoltzTrap2",
        ]
        base["gate3"] = [
            f"{v.compact} half-Heusler",
            f"{v.compact} half Heusler",
            f"{v.compact} HH alloy",
            f"{v.compact} HH compound",
            f"{v.compact} C1b",
            f"{v.compact} MgAgAs",
            f"{v.compact} F-43m",
            f"{v.compact} space group 216",
            f"{v.compact} thermodynamic stability",
            f"{v.compact} structural stability",
            f"{v.compact} mechanical stability",
            f"{v.compact} elastic constants",
            f"{v.compact} C11 C12 C44",
            f"{v.compact} phonon dispersion",
            f"{v.compact} dynamical stability",
            f"{v.compact} imaginary frequency",
            f"{v.compact} optical properties",
            f"{v.compact} thermodynamic properties",
            f"{v.compact} Debye temperature",
            f"{v.compact} thermoelectric",
            f"{v.compact} Seebeck",
            f"{v.compact} ZT",
            f"{v.compact} zT",
            f"{v.compact} power factor",
            f"{v.compact} thermal conductivity",
            f"{v.compact} lattice thermal conductivity",
            f"{v.compact} electrical conductivity",
            f"{v.compact} Slack model",
            f"{v.compact} AIMD",
            f"{v.compact} half-metal",
            f"{v.compact} half-metallic",
            f"{v.compact} spin polarization",
            f"{v.compact} ferromagnetic",
            f"{v.compact} magnetic moment",
            f"{v.compact} spintronic",
        ]
    return base
