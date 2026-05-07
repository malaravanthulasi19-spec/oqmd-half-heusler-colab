import os
import requests


class SemanticScholarClient:
    BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    def search(self, query: str, limit: int = 10) -> list[dict]:
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        params = {"query": query, "limit": limit, "fields": "title,abstract,url,externalIds"}
        resp = requests.get(self.BASE, params=params, headers=headers, timeout=30)
        return resp.json().get("data", [])
