import requests


class CrossrefClient:
    BASE = "https://api.crossref.org/works"

    def search(self, query: str, rows: int = 10) -> list[dict]:
        resp = requests.get(self.BASE, params={"query": query, "rows": rows}, timeout=30)
        return resp.json().get("message", {}).get("items", [])
