from pathlib import Path

from src.database import OQMDDatabase


def test_upsert_and_resume(tmp_path: Path) -> None:
    db = OQMDDatabase(tmp_path / 'test.sqlite3')
    db.init_schema()

    rows = [
        {'entry_id': 10, 'name': 'foo'},
        {'entry_id': 11, 'name': 'bar'},
    ]
    assert db.upsert_rows(rows) == 2
    assert db.row_count() == 2

    db.update_state(last_offset=200, current_filter='x', last_limit=100)
    assert db.get_last_offset() == 200

    # Re-upsert same ID should replace, not duplicate.
    assert db.upsert_rows([{'entry_id': 10, 'name': 'foo2'}]) == 1
    assert db.row_count() == 2

    assert db.get_element_progress('Li') == (0, False)
    db.update_element_progress(element='Li', last_offset=125, completed=False)
    assert db.get_element_progress('Li') == (125, False)
    db.update_element_progress(element='Li', last_offset=250, completed=True)
    assert db.get_element_progress('Li') == (250, True)
