LABELS = {
    "reported_dft",
    "reported_non_dft",
    "reported_similar_family",
    "not_found_after_protocol",
    "incomplete_search_retry_needed",
    "ambiguous_manual_review",
    "false_positive",
}

DFT_KEYWORDS = ["dft", "density functional theory", "first principles", "first-principles"]
PROTOTYPE_KEYWORDS = ["half-heusler", "half heusler", "c1b", "mgagas", "f-43m"]
ELEC_KEYWORDS = ["electronic structure", "band gap"]
FORM_ENERGY_KEYWORDS = ["formation energy"]

GATE2_TERMS = ["DFT", "density functional theory", "first principles", "electronic structure", "band gap", "formation energy"]
GATE3_TERMS = ["half-Heusler", "half Heusler", "C1b", "MgAgAs", "F-43m"]

REPORTED_EVIDENCE_WEIGHTS = {
    "exact_title": 50,
    "exact_snippet": 40,
    "perm_match": 30,
    "dft": 30,
    "prototype": 20,
    "elec": 15,
    "formation": 10,
    "doi": 10,
    "multi_source": 10,
    "only_elements": -40,
    "no_dft": -35,
    "false_positive": -25,
}

UNREPORTED_CONFIDENCE_BASE = 100
UNREPORTED_CONFIDENCE_WEIGHTS = {
    "exact_dft": -60,
    "exact_no_dft": -40,
    "perm": -30,
    "similar_family": -20,
    "weak_element": -10,
    "google_checked": 10,
    "openalex_checked": 10,
    "semantic_checked": 10,
    "permutation_checked": 10,
    "citation_checked": 10,
    "fulltext_checked": 10,
}
