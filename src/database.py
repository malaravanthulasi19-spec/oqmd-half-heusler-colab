"""SQLite storage for resumable OQMD downloads."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


CREATE_ROWS_SQL = """
CREATE TABLE IF NOT EXISTS oqmd_rows (
    entry_id INTEGER PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_STATE_SQL = """
CREATE TABLE IF NOT EXISTS download_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    mode TEXT NOT NULL DEFAULT 'base_filter',
    last_offset INTEGER NOT NULL DEFAULT 0,
    current_filter TEXT,
    last_limit INTEGER,
    last_error TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_FILTER_PROGRESS_SQL = """
CREATE TABLE IF NOT EXISTS filter_progress (
    filter_expr TEXT PRIMARY KEY,
    last_offset INTEGER NOT NULL DEFAULT 0,
    is_complete INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class OQMDDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode=WAL;')
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(CREATE_ROWS_SQL)
            conn.execute(CREATE_STATE_SQL)
            conn.execute(CREATE_FILTER_PROGRESS_SQL)
            conn.execute("INSERT OR IGNORE INTO download_state(id, mode, last_offset) VALUES (1, 'base_filter', 0);")
            conn.commit()

    def get_last_offset(self) -> int:
        with self.connect() as conn:
            row = conn.execute('SELECT last_offset FROM download_state WHERE id = 1;').fetchone()
            return int(row[0]) if row else 0

    def get_filter_progress(self, filter_expr: str) -> tuple[int, bool]:
        with self.connect() as conn:
            row = conn.execute(
                'SELECT last_offset, is_complete FROM filter_progress WHERE filter_expr = ?;',
                (filter_expr,),
            ).fetchone()
            if not row:
                return 0, False
            return int(row[0]), bool(row[1])

    def upsert_rows(self, rows: list[dict[str, Any]]) -> int:
        records: list[tuple[int, str]] = []
        for row in rows:
            entry_id = row.get('entry_id')
            if entry_id is None:
                continue
            records.append((int(entry_id), json.dumps(row, sort_keys=True)))
        if not records:
            return 0
        with self.connect() as conn:
            conn.executemany('INSERT OR REPLACE INTO oqmd_rows(entry_id, payload_json) VALUES (?, ?);', records)
            conn.commit()
        return len(records)

    def update_state(self, mode: str, last_offset: int, current_filter: str, last_limit: int | None, last_error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE download_state
                SET mode = ?, last_offset = ?, current_filter = ?, last_limit = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1;
                """,
                (mode, last_offset, current_filter, last_limit, last_error),
            )
            conn.commit()

    def update_filter_progress(self, filter_expr: str, last_offset: int, is_complete: bool) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO filter_progress(filter_expr, last_offset, is_complete)
                VALUES (?, ?, ?)
                ON CONFLICT(filter_expr) DO UPDATE SET
                    last_offset = excluded.last_offset,
                    is_complete = excluded.is_complete,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (filter_expr, last_offset, int(is_complete)),
            )
            conn.commit()

    def get_status(self) -> dict[str, Any]:
        with self.connect() as conn:
            state = conn.execute(
                'SELECT mode, last_offset, current_filter, last_limit, last_error FROM download_state WHERE id = 1;'
            ).fetchone()
            count = conn.execute('SELECT COUNT(*) FROM oqmd_rows;').fetchone()[0]
        return {
            'row_count': int(count),
            'mode': state[0] if state else None,
            'last_offset': int(state[1]) if state else 0,
            'current_filter': state[2] if state else None,
            'last_limit': state[3] if state else None,
            'last_error': state[4] if state else None,
            'db_path': str(self.db_path),
        }

    def fetch_all_rows(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cursor = conn.execute('SELECT payload_json FROM oqmd_rows ORDER BY entry_id ASC;')
            return [json.loads(row[0]) for row in cursor.fetchall()]

    def row_count(self) -> int:
        return int(self.get_status()['row_count'])
