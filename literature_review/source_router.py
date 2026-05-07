from .models import Hit


def _normalize_value(v):
    if isinstance(v, dict):
        return " | ".join(f"{k}={_normalize_value(val)}" for k, val in sorted(v.items()))
    if isinstance(v, list):
        return " | ".join(str(_normalize_value(x)) for x in v)
    return "" if v is None else str(v)


def normalize_hits(source: str, raw_hits: list[dict]) -> list[Hit]:
    hits = []
    for h in raw_hits:
        title = _normalize_value(h.get("title") or "")
        snippet = _normalize_value(h.get("snippet") or h.get("display_name") or "")
        abstract = _normalize_value(h.get("abstract") or "")
        doi = _normalize_value(h.get("doi") or h.get("DOI") or h.get("externalIds", {}).get("DOI", ""))
        url = _normalize_value(h.get("link") or h.get("id") or h.get("url") or "")
        hits.append(Hit(source=source, title=title, snippet=snippet, abstract=abstract, doi=doi, url=url))
    return hits
