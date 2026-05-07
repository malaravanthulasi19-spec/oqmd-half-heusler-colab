"""Configuration for the OQMD half-Heusler downloader."""

from pathlib import Path

BASE_FILTER = 'generic=ABC AND ntypes=3 AND spacegroup="F-43m" AND band_gap>0'
EXPECTED_RAW_COUNT = 3117
DEFAULT_PAGE_SIZES = [25, 10, 5, 1]
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_RETRIES_PER_PAGE_SIZE = 2
DEFAULT_CONSECUTIVE_FAILURE_STOP = 8
DEFAULT_COOLDOWN_SECONDS = 20
BACKUP_EVERY_PAGES = 1

FALLBACK_ELEMENTS = [
    'Ac', 'Ag', 'Al', 'Am', 'As', 'Au', 'B', 'Ba', 'Be', 'Bi', 'Br',
    'C', 'Ca', 'Cd', 'Ce', 'Cl', 'Co', 'Cr', 'Cs', 'Cu', 'Dy',
    'Er', 'Eu', 'F', 'Fe', 'Ga', 'Gd', 'Ge', 'Hf', 'Hg',
    'Ho', 'I', 'In', 'Ir', 'K', 'La', 'Li', 'Lu', 'Mg',
    'Mn', 'Mo', 'N', 'Na', 'Nb', 'Nd', 'Ni', 'O', 'Os',
    'P', 'Pa', 'Pb', 'Pd', 'Pr', 'Pt', 'Rb', 'Re', 'Rh',
    'Ru', 'S', 'Sb', 'Sc', 'Se', 'Si', 'Sm', 'Sn', 'Sr',
    'Ta', 'Tb', 'Tc', 'Te', 'Th', 'Ti', 'Tl', 'Tm',
    'U', 'V', 'W', 'Y', 'Yb', 'Zn', 'Zr',
]

# Colab-friendly defaults; callers can override.
DEFAULT_RUNTIME_DIR = Path('/content/oqmd_runtime')
DEFAULT_DB_PATH = DEFAULT_RUNTIME_DIR / 'oqmd_half_heusler.sqlite3'
DEFAULT_CSV_PATH = DEFAULT_RUNTIME_DIR / 'exports' / 'oqmd_half_heusler.csv'
DEFAULT_PARQUET_PATH = DEFAULT_RUNTIME_DIR / 'exports' / 'oqmd_half_heusler.parquet'

OQMD_FORMATION_ENERGY_URL = 'https://oqmd.org/oqmdapi/formationenergy'
