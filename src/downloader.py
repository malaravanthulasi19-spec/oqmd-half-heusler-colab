"""Download orchestration with resumable state and fallback strategy."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import BASE_FILTER, DEFAULT_PAGE_SIZES, DEFAULT_RETRIES_PER_PAGE_SIZE
from src.database import OQMDDatabase
from src.oqmd_client import OQMDClient, Repeated502Error


@dataclass
class DownloadResult:
    total_inserted: int
    final_offset: int
    filter_used: str


class OQMDDownloader:
    def __init__(self, db: OQMDDatabase, client: OQMDClient) -> None:
        self.db = db
        self.client = client

    def run(self, base_filter: str = BASE_FILTER) -> DownloadResult:
        self.db.init_schema()
        resume_offset = self.db.get_last_offset()
        print(f"[Downloader] Resuming from offset={resume_offset}")

        try:
            return self._run_single_filter(base_filter, resume_offset)
        except RuntimeError as exc:
            print(f"[Downloader] Base filter failed repeatedly: {exc}")
            print('[Downloader] Falling back to element_set filters (simple, no long NOT disjoint clauses).')
            # Minimal fallback set that can be expanded by users.
            fallback_filters = [
                f'{base_filter} AND element_set=Li-Mg-N',
                f'{base_filter} AND element_set=Co-Ti-Sb',
            ]
            inserted = 0
            final_offset = 0
            for filt in fallback_filters:
                result = self._run_single_filter(filt, 0)
                inserted += result.total_inserted
                final_offset = result.final_offset
            return DownloadResult(inserted, final_offset, 'fallback_element_set')

    def _run_single_filter(self, filter_expr: str, start_offset: int) -> DownloadResult:
        total_inserted = 0
        offset = start_offset

        while True:
            try:
                data, used_limit = self.client.fetch_with_adaptive_page_sizes(
                    filter_expr=filter_expr,
                    offset=offset,
                    page_sizes=DEFAULT_PAGE_SIZES,
                    retries_per_page_size=DEFAULT_RETRIES_PER_PAGE_SIZE,
                )
            except Repeated502Error as exc:
                self.db.update_state(
                    last_offset=offset,
                    current_filter=filter_expr,
                    last_limit=DEFAULT_PAGE_SIZES[0],
                )
                print(f'[Downloader] {exc}')
                print('[Downloader] Stopped safely after repeated 502s; safe to rerun later.')
                break
            rows = data.get('data', [])
            if not rows:
                print(f'[Downloader] No more rows at offset={offset}. Complete.')
                break

            inserted = self.db.upsert_rows(rows)
            total_inserted += inserted
            offset += len(rows)
            self.db.update_state(last_offset=offset, current_filter=filter_expr, last_limit=used_limit)
            print(
                f'[Downloader] offset={offset}, page_rows={len(rows)}, inserted={inserted}, '
                f'total_inserted={total_inserted}'
            )

            if len(rows) < used_limit:
                print('[Downloader] Final partial page reached. Complete.')
                break

        return DownloadResult(total_inserted=total_inserted, final_offset=offset, filter_used=filter_expr)
