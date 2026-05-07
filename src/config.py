"""Configuration for the OQMD half-Heusler downloader."""

from pathlib import Path

BASE_FILTER = 'generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0'
EXPECTED_RAW_COUNT = 3117
DEFAULT_PAGE_SIZES = [100, 50, 25, 10, 5, 1]
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_RETRIES_PER_PAGE_SIZE = 2

# Colab-friendly defaults; callers can override.
DEFAULT_RUNTIME_DIR = Path('/content/oqmd_runtime')
DEFAULT_DB_PATH = DEFAULT_RUNTIME_DIR / 'oqmd_half_heusler.sqlite3'
DEFAULT_CSV_PATH = DEFAULT_RUNTIME_DIR / 'exports' / 'oqmd_half_heusler.csv'
DEFAULT_PARQUET_PATH = DEFAULT_RUNTIME_DIR / 'exports' / 'oqmd_half_heusler.parquet'

OQMD_FORMATION_ENERGY_URL = 'https://oqmd.org/oqmdapi/formationenergy'
