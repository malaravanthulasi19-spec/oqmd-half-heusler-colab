from .constants import LABELS


def classify(scores: dict, coverage_complete: bool, source_error: bool) -> tuple[str, str]:
    if (not coverage_complete) or source_error:
        return "incomplete_search_retry_needed", "required sources/gates incomplete"
    rep = scores["reported_evidence_score"]
    unr = scores["unreported_confidence_score"]
    if rep >= 80:
        return "reported_dft", "strong formula+DFT evidence"
    if rep >= 45:
        return "reported_non_dft", "reported but weak/no DFT evidence"
    if rep >= 25:
        return "reported_similar_family", "similar-family/prototype evidence"
    if unr >= 130:
        return "not_found_after_protocol", "rigorous protocol found no report"
    return "ambiguous_manual_review", "insufficient or conflicting evidence"
