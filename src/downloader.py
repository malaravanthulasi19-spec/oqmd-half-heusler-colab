"""Download orchestration with resumable global + fallback job queue strategy."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from src.config import (
    BACKUP_EVERY_PAGES,
    BASE_FILTER,
    DEFAULT_CONSECUTIVE_FAILURE_STOP,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_PAGE_SIZES,
    DEFAULT_RETRIES_PER_PAGE_SIZE,
    FALLBACK_ELEMENTS,
)
from src.database import OQMDDatabase
from src.oqmd_client import OQMDClient


@dataclass
class DownloadResult:
    total_inserted: int
    safe_stop: bool


class OQMDDownloader:
    def __init__(self, db: OQMDDatabase, client: OQMDClient) -> None:
        self.db = db
        self.client = client

    def run(
        self,
        base_filter: str = BASE_FILTER,
        backup_path: Path | None = None,
        search_mode: str = 'adaptive',
    ) -> DownloadResult:
        self.db.init_schema()
        mode = search_mode.strip().lower()
        if mode not in {'adaptive', 'global', 'fallback'}:
            raise ValueError("search_mode must be one of: 'adaptive', 'global', 'fallback'")

        if mode in {'adaptive', 'fallback'}:
            self._initialize_fallback_jobs(base_filter)
        total_inserted = 0
        safe_stop = False
        pages_since_backup = 0

        run_fallback = mode == 'fallback'
        if mode in {'adaptive', 'global'}:
            print('[Downloader] Trying global BASE_FILTER first.')
            base_inserted, base_safe_stop = self._process_one_stream('global', base_filter, None)
            total_inserted += base_inserted
            safe_stop = safe_stop or base_safe_stop
            if mode == 'adaptive':
                run_fallback = base_safe_stop or base_inserted == 0
                if run_fallback:
                    reason = 'safe stop' if base_safe_stop else 'no rows returned'
                    print(f'[Downloader] Switching to fallback search after global stream ({reason}).')

        if backup_path and total_inserted > 0:
            self.db.safe_backup_to(backup_path)

        if run_fallback:
            pending = self.db.list_pending_jobs(mode='fallback')
            for job in pending:
                print(f"[Downloader] Processing fallback job element={job['element']} offset={job['next_offset']}")
                inserted, stopped = self._process_one_stream(job['job_id'], job['filter_expr'], job)
                total_inserted += inserted
                safe_stop = safe_stop or stopped
                pages_since_backup += 1
                if backup_path and pages_since_backup >= BACKUP_EVERY_PAGES:
                    self.db.safe_backup_to(backup_path)
                    pages_since_backup = 0
                if stopped:
                    break

        if backup_path:
            self.db.safe_backup_to(backup_path)

        status = self.db.get_status()
        print(f"[Status] unique rows={status['unique_rows']}")
        print(f"[Status] completed fallback jobs={status['completed_jobs']}, pending fallback jobs={status['pending_jobs']}")
        print(f"[Status] current filter={status['current_filter']}, offset={status['last_offset']}")
        print(f"[Status] database path={status['database_path']}")
        if backup_path:
            print(f'[Status] backup path={backup_path}')

        if safe_stop:
            print('[Downloader] Stopped safely after repeated API failures; safe to rerun later.')
        return DownloadResult(total_inserted=total_inserted, safe_stop=safe_stop)

    def _initialize_fallback_jobs(self, base_filter: str) -> None:
        for element in FALLBACK_ELEMENTS:
            filter_expr = f'{base_filter} AND element_set={element}'
            self.db.upsert_job(job_id=f'fallback:{element}', mode='fallback', filter_expr=filter_expr, element=element)

    def _process_one_stream(self, job_id: str, filter_expr: str, job: dict | None) -> tuple[int, bool]:
        offset = int(job['next_offset']) if job else self.db.get_status()['last_offset']
        total_inserted = 0
        consecutive_failures = 0
        while True:
            try:
                data, used_limit = self.client.fetch_with_adaptive_page_sizes(
                    filter_expr=filter_expr,
                    offset=offset,
                    page_sizes=DEFAULT_PAGE_SIZES,
                    retries_per_page_size=DEFAULT_RETRIES_PER_PAGE_SIZE,
                )
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                if job:
                    attempts = self.db.record_job_failure(job_id, str(exc))
                    print(f'[Downloader] job={job_id} failure={attempts} error={exc}')
                else:
                    print(f'[Downloader] global failure={consecutive_failures} error={exc}')
                if consecutive_failures >= 2:
                    print(f'[Downloader] cooldown {DEFAULT_COOLDOWN_SECONDS}s after repeated timeout/502 failures.')
                    time.sleep(DEFAULT_COOLDOWN_SECONDS)
                if consecutive_failures >= DEFAULT_CONSECUTIVE_FAILURE_STOP:
                    return total_inserted, True
                return total_inserted, True

            rows = data.get('data', [])
            if not rows:
                if job:
                    self.db.mark_job_completed(job_id)
                break

            inserted = self.db.upsert_rows(rows)
            total_inserted += inserted
            offset += len(rows)
            self.db.update_state(last_offset=offset, current_filter=filter_expr, last_limit=used_limit)
            if job:
                self.db.update_job_progress(job_id=job_id, next_offset=offset, last_limit=used_limit)

            if len(rows) < used_limit:
                if job:
                    self.db.mark_job_completed(job_id)
                break

        return total_inserted, False
