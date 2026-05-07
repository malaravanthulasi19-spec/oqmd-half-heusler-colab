import requests


class UnpaywallClient:
    BASE = "https://api.unpaywall.org/v2"

    def lookup(self, doi: str, email: str = "test@example.com") -> dict:
        resp = requests.get(f"{self.BASE}/{doi}", params={"email": email}, timeout=30)
        return resp.json()
