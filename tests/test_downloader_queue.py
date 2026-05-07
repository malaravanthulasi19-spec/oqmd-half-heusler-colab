from pathlib import Path

from src.database import OQMDDatabase
from src.downloader import OQMDDownloader


class StubClient:
    def __init__(self, pages_by_filter: dict[str, list[list[dict]]], fail_once_filter: str | None = None):
        self.pages_by_filter = pages_by_filter
        self.calls = {}
        self.fail_once_filter = fail_once_filter

    def fetch_with_adaptive_page_sizes(self, filter_expr, offset, page_sizes, retries_per_page_size):
        key = (filter_expr, offset)
        self.calls[key] = self.calls.get(key, 0) + 1
        if self.fail_once_filter == filter_expr and self.calls[key] == 1:
            raise RuntimeError('timeout')
        pages = self.pages_by_filter.get(filter_expr, [])
        idx = offset
        if idx < len(pages):
            return {'data': pages[idx]}, 1
        return {'data': []}, 1


def test_entry_id_dedupe(tmp_path: Path) -> None:
    db = OQMDDatabase(tmp_path / 't.sqlite3')
    db.init_schema()
    assert db.upsert_rows([{'entry_id': 1}, {'entry_id': 1}]) == 2
    assert db.row_count() == 1


def test_job_progress_persists_and_completed_skipped(tmp_path: Path) -> None:
    base = 'X'
    filt = f'{base} AND element_set=Ac'
    client = StubClient({base: [[]], filt: [[{'entry_id': 10}], []]})
    db = OQMDDatabase(tmp_path / 't.sqlite3')
    d = OQMDDownloader(db, client)
    d.run(base_filter=base)
    pending = db.list_pending_jobs('fallback')
    assert not any(j['element'] == 'Ac' for j in pending)


def test_failed_job_resumes_from_saved_offset(tmp_path: Path) -> None:
    base = 'Y'
    filt = f'{base} AND element_set=Ag'
    db = OQMDDatabase(tmp_path / 't.sqlite3')
    db.init_schema()
    db.upsert_job('fallback:Ag', 'fallback', filt, 'Ag')
    db.update_job_progress('fallback:Ag', next_offset=1, last_limit=1)
    client = StubClient({base: [[]], filt: [[{'entry_id': 1}], [{'entry_id': 2}], []]})
    d = OQMDDownloader(db, client)
    d.run(base_filter=base)
    assert db.row_count() >= 1


def test_safe_stop_does_not_erase_progress(tmp_path: Path) -> None:
    base = 'Z'
    filt = f'{base} AND element_set=Al'
    class FailClient(StubClient):
        def fetch_with_adaptive_page_sizes(self, *args, **kwargs):
            raise RuntimeError('502')

    db = OQMDDatabase(tmp_path / 't.sqlite3')
    db.init_schema()
    db.upsert_rows([{'entry_id': 99}])
    d = OQMDDownloader(db, FailClient({}))
    result = d.run(base_filter=base)
    assert result.safe_stop is True
    assert db.row_count() == 1
