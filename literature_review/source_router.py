from .models import Hit


def _safe_scalar(value):
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    if isinstance(value, dict):
        return " | ".join(f"{k}:{v}" for k, v in value.items())
    return value or ""


def normalize_hits(source: str, raw_hits: list[dict]) -> list[Hit]:
    hits = []
    for h in raw_hits:
        title = _safe_scalar(h.get("title"))
        snippet = _safe_scalar(h.get("snippet") or h.get("display_name"))
        abstract = _safe_scalar(h.get("abstract"))
        doi = _safe_scalar(h.get("doi") or h.get("DOI") or h.get("externalIds", {}).get("DOI", ""))
        url = _safe_scalar(h.get("link") or h.get("id") or h.get("url"))
        hits.append(Hit(source=source, title=title, snippet=snippet, abstract=abstract, doi=doi, url=url))
    return hits
