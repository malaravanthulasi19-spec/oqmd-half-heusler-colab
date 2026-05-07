from .models import Hit


def normalize_hits(source: str, raw_hits: list[dict]) -> list[Hit]:
    hits = []
    for h in raw_hits:
        title = h.get("title") or ""
        snippet = h.get("snippet") or h.get("display_name") or ""
        abstract = h.get("abstract") or ""
        doi = h.get("doi") or h.get("DOI") or h.get("externalIds", {}).get("DOI", "")
        url = h.get("link") or h.get("id") or h.get("url") or ""
        hits.append(Hit(source=source, title=title, snippet=snippet, abstract=abstract, doi=doi, url=url))
    return hits
