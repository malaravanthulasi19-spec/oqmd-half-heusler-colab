#!/usr/bin/env python3
"""Export OQMD rows from SQLite payload_json to CSV and Parquet."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


def load_rows(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT payload_json FROM oqmd_rows ORDER BY entry_id;")
        rows = []
        for (payload_json,) in cur.fetchall():
            rows.append(json.loads(payload_json))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Path to SQLite file")
    parser.add_argument("--csv", required=True, type=Path, help="Output CSV path")
    parser.add_argument("--parquet", required=True, type=Path, help="Output Parquet path")
    args = parser.parse_args()

    if not args.db.exists():
        raise FileNotFoundError(f"SQLite file not found: {args.db}")

    rows = load_rows(args.db)
    if not rows:
        print("[Export] No rows found; skipping file writes.")
        return 0

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    args.parquet.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.csv, index=False)
    df.to_parquet(args.parquet, index=False)

    print(f"[Export] wrote {len(df)} rows")
    print(f"[Export] CSV: {args.csv}")
    print(f"[Export] Parquet: {args.parquet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
