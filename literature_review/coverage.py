from .models import Coverage


def coverage_complete(c: Coverage, require_citation=False, require_fulltext=False) -> bool:
    base = c.google_scholar_checked and c.openalex_checked and c.semantic_scholar_checked and c.crossref_checked
    if not base:
        return False
    if require_citation and not c.citation_neighbor_checked:
        return False
    if require_fulltext and not c.full_text_checked:
        return False
    return True
