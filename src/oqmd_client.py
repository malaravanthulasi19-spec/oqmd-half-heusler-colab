"""HTTP client for OQMD formationenergy endpoint with visible retry behavior."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from src.config import OQMD_FORMATION_ENERGY_URL


@dataclass
class OQMDClient:
    timeout_seconds: int
    cooldown_on_502_seconds: int = 30

    def fetch_page(self, filter_expr: str, limit: int, offset: int) -> dict[str, Any]:
        params = {'filter': filter_expr, 'limit': limit, 'offset': offset}
        resp = requests.get(OQMD_FORMATION_ENERGY_URL, params=params, timeout=self.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    def fetch_with_adaptive_page_sizes(self, filter_expr: str, offset: int, page_sizes: list[int], retries_per_page_size: int) -> tuple[dict[str, Any], int]:
        last_error: Exception | None = None
        for page_size in page_sizes:
            for attempt in range(1, retries_per_page_size + 1):
                try:
                    print(f"[OQMD] fetch offset={offset}, limit={page_size}, attempt={attempt}")
                    return self.fetch_page(filter_expr=filter_expr, limit=page_size, offset=offset), page_size
                except requests.RequestException as exc:
                    last_error = exc
                    status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
                    print(f"[OQMD] retryable error offset={offset}, limit={page_size}, attempt={attempt}: {exc}")
                    if status_code == 502:
                        print(f"[OQMD] 502 detected. Cooling down for {self.cooldown_on_502_seconds}s.")
                        time.sleep(self.cooldown_on_502_seconds)
                    else:
                        time.sleep(min(2 * attempt, 5))
        raise RuntimeError(f"Failed all page sizes at offset={offset}") from last_error
