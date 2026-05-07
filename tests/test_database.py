from pathlib import Path

from src.database import OQMDDatabase


def test_upsert_and_resume(tmp_path: Path) -> None:
    db = OQMDDatabase(tmp_path / 'test.sqlite3')
    db.init_schema()

    assert db.upsert_rows([{'entry_id': 10, 'name': 'foo'}, {'entry_id': 11, 'name': 'bar'}]) == 2
    assert db.row_count() == 2

    db.update_state(mode='base_filter', last_offset=225, current_filter='BASE', last_limit=25, last_error='502')
    db.update_filter_progress('BASE', 225, False)
    status = db.get_status()
    assert status['last_offset'] == 225
    assert status['mode'] == 'base_filter'
    assert db.get_filter_progress('BASE') == (225, False)

    assert db.upsert_rows([{'entry_id': 10, 'name': 'foo2'}]) == 1
    assert db.row_count() == 2
