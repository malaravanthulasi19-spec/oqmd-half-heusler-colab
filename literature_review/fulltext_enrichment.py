def should_run_fulltext(label: str, shortlist: bool, has_doi_or_oa: bool) -> bool:
    return shortlist and has_doi_or_oa and label in {"ambiguous_manual_review", "not_found_after_protocol"}
