import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS materials (
  material TEXT PRIMARY KEY,
  band_gap_ev REAL,
  stability TEXT,
  oqmd_entry_id INTEGER,
  final_rank INTEGER
);
CREATE TABLE IF NOT EXISTS hits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  material TEXT,
  source TEXT,
  title TEXT,
  snippet TEXT,
  abstract TEXT,
  doi TEXT,
  url TEXT,
  UNIQUE(material, source, title, doi, url)
);
CREATE TABLE IF NOT EXISTS classifications (
  material TEXT PRIMARY KEY,
  automated_status TEXT,
  reported_evidence_score INTEGER,
  unreported_confidence_score INTEGER,
  reason TEXT,
  best_weak_match TEXT,
  best_matching_paper TEXT,
  doi TEXT,
  url TEXT,
  final_manual_label TEXT,
  reviewer_notes TEXT
);
CREATE TABLE IF NOT EXISTS coverage (
  material TEXT PRIMARY KEY,
  google_scholar_checked INTEGER,
  openalex_checked INTEGER,
  semantic_scholar_checked INTEGER,
  crossref_checked INTEGER,
  permutation_checked INTEGER,
  citation_neighbor_checked INTEGER,
  full_text_checked INTEGER,
  source_error INTEGER
);
CREATE TABLE IF NOT EXISTS completed_queries (
  material TEXT,
  gate TEXT,
  source TEXT,
  query TEXT,
  PRIMARY KEY(material, gate, source, query)
);
"""


def connect(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
