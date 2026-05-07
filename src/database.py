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
    last_offset INTEGER NOT NULL DEFAULT 0,
    current_filter TEXT,
    last_limit INTEGER,
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
            conn.execute('INSERT OR IGNORE INTO download_state(id, last_offset) VALUES (1, 0);')
            conn.commit()

    def get_last_offset(self) -> int:
        with self.connect() as conn:
            row = conn.execute('SELECT last_offset FROM download_state WHERE id = 1;').fetchone()
            return int(row[0]) if row else 0

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
            conn.executemany(
                'INSERT OR REPLACE INTO oqmd_rows(entry_id, payload_json) VALUES (?, ?);',
                records,
            )
            conn.commit()
        return len(records)

    def update_state(self, last_offset: int, current_filter: str, last_limit: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE download_state
                SET last_offset = ?, current_filter = ?, last_limit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1;
                """,
                (last_offset, current_filter, last_limit),
            )
            conn.commit()

    def fetch_all_rows(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cursor = conn.execute('SELECT payload_json FROM oqmd_rows ORDER BY entry_id ASC;')
            return [json.loads(row[0]) for row in cursor.fetchall()]

    def row_count(self) -> int:
        with self.connect() as conn:
            (count,) = conn.execute('SELECT COUNT(*) FROM oqmd_rows;').fetchone()
            return int(count)
