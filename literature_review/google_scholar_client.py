import os
import requests


class GoogleScholarClient:
    BASE = "https://serpapi.com/search.json"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")

    def search(self, query: str, num: int = 10) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY missing")
        params = {"engine": "google_scholar", "q": query, "num": num, "api_key": self.api_key}
        data = requests.get(self.BASE, params=params, timeout=30).json()
        return data.get("organic_results", [])
