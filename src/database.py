"""SQLite storage for resumable OQMD downloads."""

from __future__ import annotations

import json
import shutil
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

CREATE_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS download_jobs (
    job_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    filter_expr TEXT NOT NULL,
    element TEXT,
    next_offset INTEGER NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
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
            conn.execute(CREATE_JOBS_SQL)
            conn.execute('INSERT OR IGNORE INTO download_state(id, last_offset) VALUES (1, 0);')
            conn.commit()


    def get_last_offset(self) -> int:
        with self.connect() as conn:
            row = conn.execute('SELECT last_offset FROM download_state WHERE id=1;').fetchone()
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
            conn.executemany('INSERT OR REPLACE INTO oqmd_rows(entry_id, payload_json) VALUES (?, ?);', records)
            conn.commit()
        return len(records)

    def update_state(self, last_offset: int, current_filter: str, last_limit: int) -> None:
        with self.connect() as conn:
            conn.execute(
                'UPDATE download_state SET last_offset=?, current_filter=?, last_limit=?, updated_at=CURRENT_TIMESTAMP WHERE id=1;',
                (last_offset, current_filter, last_limit),
            )
            conn.commit()

    def upsert_job(self, job_id: str, mode: str, filter_expr: str, element: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO download_jobs(job_id, mode, filter_expr, element)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO NOTHING;
                """,
                (job_id, mode, filter_expr, element),
            )
            conn.commit()

    def list_pending_jobs(self, mode: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cur = conn.execute(
                'SELECT job_id, mode, filter_expr, element, next_offset, failed_attempts, last_limit FROM download_jobs WHERE mode=? AND completed=0 ORDER BY element;',
                (mode,),
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def update_job_progress(self, job_id: str, next_offset: int, last_limit: int, reset_failures: bool = True) -> None:
        with self.connect() as conn:
            if reset_failures:
                conn.execute(
                    'UPDATE download_jobs SET next_offset=?, last_limit=?, failed_attempts=0, last_error=NULL, updated_at=CURRENT_TIMESTAMP WHERE job_id=?;',
                    (next_offset, last_limit, job_id),
                )
            else:
                conn.execute(
                    'UPDATE download_jobs SET next_offset=?, last_limit=?, updated_at=CURRENT_TIMESTAMP WHERE job_id=?;',
                    (next_offset, last_limit, job_id),
                )
            conn.commit()

    def mark_job_completed(self, job_id: str) -> None:
        with self.connect() as conn:
            conn.execute('UPDATE download_jobs SET completed=1, updated_at=CURRENT_TIMESTAMP WHERE job_id=?;', (job_id,))
            conn.commit()

    def record_job_failure(self, job_id: str, error: str) -> int:
        with self.connect() as conn:
            conn.execute(
                'UPDATE download_jobs SET failed_attempts=failed_attempts+1, last_error=?, updated_at=CURRENT_TIMESTAMP WHERE job_id=?;',
                (error, job_id),
            )
            row = conn.execute('SELECT failed_attempts FROM download_jobs WHERE job_id=?;', (job_id,)).fetchone()
            conn.commit()
            return int(row[0])

    def get_status(self) -> dict[str, Any]:
        with self.connect() as conn:
            (row_count,) = conn.execute('SELECT COUNT(*) FROM oqmd_rows;').fetchone()
            state = conn.execute('SELECT last_offset, current_filter, last_limit FROM download_state WHERE id=1;').fetchone()
            (jobs_completed,) = conn.execute('SELECT COUNT(*) FROM download_jobs WHERE completed=1;').fetchone()
            (jobs_pending,) = conn.execute('SELECT COUNT(*) FROM download_jobs WHERE completed=0;').fetchone()
        return {
            'unique_rows': int(row_count),
            'last_offset': int(state[0]) if state else 0,
            'current_filter': state[1] if state else None,
            'last_limit': state[2] if state else None,
            'completed_jobs': int(jobs_completed),
            'pending_jobs': int(jobs_pending),
            'database_path': str(self.db_path),
        }

    def safe_backup_to(self, backup_path: Path) -> None:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as src_conn:
            src_conn.execute('PRAGMA wal_checkpoint(FULL);')
            with sqlite3.connect(backup_path) as dst_conn:
                src_conn.backup(dst_conn)
        wal = self.db_path.with_suffix(self.db_path.suffix + '-wal')
        shm = self.db_path.with_suffix(self.db_path.suffix + '-shm')
        for f in (wal, shm):
            if f.exists() and backup_path.parent == self.db_path.parent:
                shutil.copy2(f, backup_path.parent / f.name)

    def row_count(self) -> int:
        return self.get_status()['unique_rows']
