def should_run_citation_neighbor(label: str, shortlist: bool) -> bool:
    return shortlist and label in {"not_found_after_protocol", "ambiguous_manual_review"}
