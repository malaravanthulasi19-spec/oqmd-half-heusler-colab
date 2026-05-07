#!/usr/bin/env python3
"""Verify integrity metrics for the OQMD SQLite dataset."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Path to SQLite file")
    parser.add_argument("--expected-count", type=int, default=None, help="Optional expected unique row count")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"[Verify] FAIL: SQLite file not found: {args.db}")
        return 1

    with sqlite3.connect(args.db) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='oqmd_rows';"
        ).fetchone()
        if not table_exists:
            print("[Verify] FAIL: table oqmd_rows does not exist")
            return 1

        (unique_rows,) = conn.execute("SELECT COUNT(*) FROM oqmd_rows;").fetchone()
        (duplicate_entry_ids,) = conn.execute(
            """
            SELECT COALESCE(SUM(cnt - 1), 0)
            FROM (
                SELECT entry_id, COUNT(*) AS cnt
                FROM oqmd_rows
                GROUP BY entry_id
                HAVING COUNT(*) > 1
            );
            """
        ).fetchone()

    print(f"[Verify] SQLite file: {args.db}")
    print("[Verify] table oqmd_rows: OK")
    print(f"[Verify] unique_rows: {unique_rows}")
    print(f"[Verify] duplicate_entry_id_count: {duplicate_entry_ids}")

    if args.expected_count is not None:
        if unique_rows != args.expected_count:
            print(f"[Verify] FAIL: expected {args.expected_count}, got {unique_rows}")
            return 1
        print(f"[Verify] expected_count check: OK ({args.expected_count})")

    print("[Verify] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
