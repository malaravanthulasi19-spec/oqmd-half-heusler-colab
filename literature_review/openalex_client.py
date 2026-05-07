import requests


class OpenAlexClient:
    BASE = "https://api.openalex.org/works"

    def search(self, query: str, per_page: int = 10) -> list[dict]:
        resp = requests.get(self.BASE, params={"search": query, "per-page": per_page}, timeout=30)
        return resp.json().get("results", [])
