import pandas as pd
from .paths import INPUT_CSV, BACKUP_SQLITE
from .database import connect


def load_input(path=INPUT_CSV):
    return pd.read_csv(path)


def run(top_n: int = 10):
    conn = connect(BACKUP_SQLITE)
    df = load_input().head(top_n)
    return {"materials_loaded": len(df), "db": str(BACKUP_SQLITE), "status": "scaffold"}
