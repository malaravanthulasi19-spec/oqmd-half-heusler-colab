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
    completed: bool = True


class OQMDDownloader:
    FALLBACK_ELEMENTS = [
        'Ac', 'Ag', 'Al', 'Am', 'As', 'Au', 'B', 'Ba', 'Be', 'Bi', 'Br',
        'C', 'Ca', 'Cd', 'Ce', 'Cl', 'Co', 'Cr', 'Cs', 'Cu', 'Dy',
        'Er', 'Eu', 'F', 'Fe', 'Ga', 'Gd', 'Ge', 'Hf', 'Hg',
        'Ho', 'I', 'In', 'Ir', 'K', 'La', 'Li', 'Lu', 'Mg',
        'Mn', 'Mo', 'N', 'Na', 'Nb', 'Nd', 'Ni', 'O', 'Os',
        'P', 'Pa', 'Pb', 'Pd', 'Pr', 'Pt', 'Rb', 'Re', 'Rh',
        'Ru', 'S', 'Sb', 'Sc', 'Se', 'Si', 'Sm', 'Sn', 'Sr',
        'Ta', 'Tb', 'Tc', 'Te', 'Th', 'Ti', 'Tl', 'Tm',
        'U', 'V', 'W', 'Y', 'Yb', 'Zn', 'Zr',
    ]

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
            print('[Downloader] Falling back to per-element filters.')
            inserted = 0
            final_offset = 0
            for element in self.FALLBACK_ELEMENTS:
                element_offset, completed = self.db.get_element_progress(element)
                if completed:
                    print(f'[Downloader] mode=fallback_element element={element} already completed; skipping.')
                    continue
                filt = f'{base_filter} AND element_set={element}'
                print(
                    f'[Downloader] mode=fallback_element element={element} '
                    f'element_offset={element_offset} total_unique_rows={self.db.row_count()}'
                )
                result = self._run_single_filter(filt, element_offset)
                inserted += result.total_inserted
                final_offset = result.final_offset
                self.db.update_element_progress(
                    element=element,
                    last_offset=final_offset,
                    completed=result.completed,
                )
                print(
                    f'[Downloader] mode=fallback_element element={element} '
                    f'element_offset={final_offset} total_unique_rows={self.db.row_count()}'
                )
                if not result.completed:
                    print(f'[Downloader] Paused fallback at element={element}; safe to rerun later.')
                    break
            return DownloadResult(inserted, final_offset, 'fallback_element_set')

    def _run_single_filter(self, filter_expr: str, start_offset: int) -> DownloadResult:
        total_inserted = 0
        offset = start_offset
        completed = True

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
                completed = False
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

        return DownloadResult(
            total_inserted=total_inserted,
            final_offset=offset,
            filter_used=filter_expr,
            completed=completed,
        )
