"""Download orchestration with resumable state and fallback strategy."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import BASE_FILTER, DEFAULT_PAGE_SIZES, DEFAULT_RETRIES_PER_PAGE_SIZE
from src.database import OQMDDatabase
from src.oqmd_client import OQMDClient

FALLBACK_ELEMENTS = [
    'Li','Be','B','C','N','O','F','Na','Mg','Al','Si','P','S','Cl','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni',
    'Cu','Zn','Ga','Ge','As','Se','Br','Rb','Sr','Y','Zr','Nb','Mo','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I',
    'Cs','Ba','La','Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Bi'
]


@dataclass
class DownloadResult:
    total_inserted: int
    final_offset: int
    filter_used: str


class OQMDDownloader:
    def __init__(self, db: OQMDDatabase, client: OQMDClient) -> None:
        self.db = db
        self.client = client

    def run(self, base_filter: str = BASE_FILTER, allow_fallback: bool = True) -> DownloadResult:
        self.db.init_schema()
        base_offset, base_done = self.db.get_filter_progress(base_filter)
        if not base_done:
            try:
                return self._run_single_filter(base_filter, base_offset, mode='base_filter')
            except RuntimeError as exc:
                self.db.update_state('base_filter', base_offset, base_filter, None, str(exc))
                print('[Downloader] Base filter failed repeatedly; progress saved, safe to rerun later.')
                if not allow_fallback:
                    raise

        if allow_fallback:
            print('[Downloader] Running fallback element mode.')
            total_inserted = 0
            for el in FALLBACK_ELEMENTS:
                filt = f'{base_filter} AND element_set~{el}'
                off, done = self.db.get_filter_progress(filt)
                if done:
                    continue
                try:
                    result = self._run_single_filter(filt, off, mode='fallback_element')
                    total_inserted += result.total_inserted
                except RuntimeError as exc:
                    self.db.update_state('fallback_element', off, filt, None, str(exc))
                    print('[Downloader] Fallback filter failed; progress saved, safe to rerun later.')
                    break
            return DownloadResult(total_inserted=total_inserted, final_offset=0, filter_used='fallback_element_set')

        return DownloadResult(total_inserted=0, final_offset=base_offset, filter_used=base_filter)

    def _run_single_filter(self, filter_expr: str, start_offset: int, mode: str) -> DownloadResult:
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
            except RuntimeError as exc:
                self.db.update_state(mode, offset, filter_expr, None, str(exc))
                self.db.update_filter_progress(filter_expr, offset, False)
                print('[Downloader] Page fetch failed at current offset; state saved, safe to rerun later.')
                raise
            rows = data.get('data', [])
            if not rows:
                self.db.update_filter_progress(filter_expr, offset, True)
                print(f'[Downloader] No more rows at offset={offset}. Complete.')
                break

            inserted = self.db.upsert_rows(rows)
            total_inserted += inserted
            offset += len(rows)
            self.db.update_state(mode, offset, filter_expr, used_limit)
            self.db.update_filter_progress(filter_expr, offset, False)
            print(f'[Downloader] mode={mode}, offset={offset}, rows={len(rows)}, inserted={inserted}')
            if len(rows) < used_limit:
                self.db.update_filter_progress(filter_expr, offset, True)
                break

        return DownloadResult(total_inserted=total_inserted, final_offset=offset, filter_used=filter_expr)
