from __future__ import annotations

import re
from .composition_equivalence import canonical_element_set, formula_permutations

_DFT_CTX = ("dft", "first principles", "density functional", "band structure", "dos", "phonon", "thermoelectric", "seebeck", "zt")
_FAMILY = ("xyte half-heusler", "18-electron half-heusler tellurides", "miv mviii te half-heusler", "xfete half-heusler", "xcote half-heusler")


def _has_boundary(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text) is not None


def classify_hit_evidence_level(hit: dict, material: str) -> dict:
    txt = f"{hit.get('title','')} {hit.get('snippet','')} {hit.get('abstract','')}"
    perms = formula_permutations(material)
    exact = _has_boundary(txt, material)
    matched = next((p for p in perms if _has_boundary(txt, p)), "")
    perm = bool(matched and matched != material)
    dft = any(k.lower() in txt.lower() for k in _DFT_CTX)
    fam = any(k.lower() in txt.lower() for k in _FAMILY)
    level = "NO_RELEVANT_EVIDENCE"; reason = "No formula/family indicators"
    if exact and dft or perm and dft:
        level, reason = "DEEP_DFT_PROPERTY_EVIDENCE", "Formula/permutation with DFT/property context"
    elif exact:
        level, reason = "EXACT_FORMULA_EVIDENCE", "Exact formula match"
    elif perm:
        level, reason = "COMPOSITION_PERMUTATION_EVIDENCE", "Permutation formula match"
    elif fam:
        level, reason = "WEAK_FAMILY_EVIDENCE", "Family-level evidence only"
    return {
        "evidence_level": level,
        "evidence_level_reason": reason,
        "canonical_element_set": canonical_element_set(material),
        "matched_formula_variant": matched if matched else (material if exact else ""),
        "matched_formula_is_permutation": perm,
        "exact_formula_evidence_found": exact,
        "permutation_formula_evidence_found": perm,
        "family_level_evidence_found": fam,
        "deep_dft_property_evidence_found": level == "DEEP_DFT_PROPERTY_EVIDENCE",
    }
