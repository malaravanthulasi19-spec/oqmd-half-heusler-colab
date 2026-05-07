"""Export utilities for CSV and Parquet outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.database import OQMDDatabase


def export_all(db: OQMDDatabase, csv_path: Path, parquet_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    rows = db.fetch_all_rows()
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    print(f'[Export] wrote CSV: {csv_path}')
    print(f'[Export] wrote Parquet: {parquet_path}')
