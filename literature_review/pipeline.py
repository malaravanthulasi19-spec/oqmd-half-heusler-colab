from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from .checkpoint import is_query_completed, mark_query_completed
from .classification import classify
from .constants import DFT_KEYWORDS, PROTOTYPE_KEYWORDS
from .coverage import coverage_complete
from .crossref_client import CrossrefClient
from .database import connect
from .evidence_scoring import contains_any, score_reported_evidence, score_unreported_confidence
from .formula_variants import build_variants, exact_formula_match, loose_element_system_match, permutation_formula_match
from .google_scholar_client import GoogleScholarClient
from .models import Coverage
from .openalex_client import OpenAlexClient
from .paths import BACKUP_SQLITE, INPUT_CSV, OUTPUT_DIR
from .query_builder import gate1_queries, gate2_queries, gate3_queries, gate4_queries
from .semantic_scholar_client import SemanticScholarClient
from .source_router import normalize_hits
from .export import export_outputs


def _bool(v: bool) -> int:
    return 1 if v else 0


def _extract_material(row: pd.Series) -> str:
    for c in ["Material", "material", "formula", "Formula"]:
        if c in row and isinstance(row[c], str):
            return row[c]
    raise ValueError("No material/formula column found")


def _insert_material(conn, row: pd.Series, material: str):
    conn.execute(
        "INSERT OR REPLACE INTO materials(material, band_gap_ev, stability, oqmd_entry_id, final_rank) VALUES(?,?,?,?,?)",
        (
            material,
            float(row.get("Band Gap (eV)", row.get("band_gap", 0.0)) or 0.0),
            str(row.get("Stability", row.get("stability", "")) or ""),
            row.get("OQMD Entry ID", row.get("entry_id")),
            row.get("Final Rank", row.get("rank")),
        ),
    )


def _save_hits(conn, material: str, hits):
    conn.executemany(
        "INSERT OR IGNORE INTO hits(material, source, title, snippet, abstract, doi, url) VALUES(?,?,?,?,?,?,?)",
        [(material, h.source, h.title, h.snippet, h.abstract, h.doi, h.url) for h in hits],
    )


def _run_queries(conn, material: str, gate: str, source_name: str, queries: list[str], search_fn):
    all_hits = []
    checked = False
    source_error = False
    for q in queries:
        if is_query_completed(conn, material, gate, source_name, q):
            continue
        checked = True
        try:
            raw = search_fn(q)
            hits = normalize_hits(source_name, raw)
            _save_hits(conn, material, hits)
            all_hits.extend(hits)
            mark_query_completed(conn, material, gate, source_name, q)
        except Exception:
            source_error = True
    return all_hits, checked, source_error


def run(top_n: int = 10, input_csv: Path = INPUT_CSV, db_path: Path = BACKUP_SQLITE, output_dir: Path = OUTPUT_DIR, clients: dict[str, Any] | None = None):
    conn = connect(db_path)
    df = pd.read_csv(input_csv).head(top_n)

    c = clients or {
        "google_scholar": GoogleScholarClient(),
        "openalex": OpenAlexClient(),
        "semantic_scholar": SemanticScholarClient(),
        "crossref": CrossrefClient(),
    }

    out_rows = []
    processed = 0
    for _, row in df.iterrows():
        material = _extract_material(row)
        _insert_material(conn, row, material)
        variants = build_variants(material)
        cov = Coverage()
        if c.get("semantic_scholar") is None:
            cov.semantic_scholar_checked = True
        all_hits = []

        for gate, queries in [("gate1", gate1_queries(variants)), ("gate2", gate2_queries(variants)), ("gate3", gate3_queries(variants))]:
            h, checked, err = _run_queries(conn, material, gate, "google_scholar", queries, c["google_scholar"].search)
            all_hits += h
            cov.google_scholar_checked = cov.google_scholar_checked or checked
            cov.source_error = cov.source_error or err

            h, checked, err = _run_queries(conn, material, gate, "openalex", queries, c["openalex"].search)
            all_hits += h
            cov.openalex_checked = cov.openalex_checked or checked
            cov.source_error = cov.source_error or err

            if c.get("semantic_scholar") is not None:
                h, checked, err = _run_queries(conn, material, gate, "semantic_scholar", queries, c["semantic_scholar"].search)
                all_hits += h
                cov.semantic_scholar_checked = cov.semantic_scholar_checked or checked
                cov.source_error = cov.source_error or err

            h, checked, err = _run_queries(conn, material, gate, "crossref", queries, c["crossref"].search)
            all_hits += h
            cov.crossref_checked = cov.crossref_checked or checked
            cov.source_error = cov.source_error or err

        text_blob = " ".join([f"{h.title} {h.snippet} {h.abstract}" for h in all_hits])
        strong_dft = any(exact_formula_match(f"{h.title} {h.snippet} {h.abstract}", variants) and contains_any(f"{h.title} {h.snippet} {h.abstract}", DFT_KEYWORDS) for h in all_hits)

        if not strong_dft:
            h, checked, err = _run_queries(conn, material, "gate4", "google_scholar", gate4_queries(variants), c["google_scholar"].search)
            all_hits += h
            cov.permutation_checked = checked
            cov.source_error = cov.source_error or err

        feature = {
            "exact_title": any(exact_formula_match(h.title, variants) for h in all_hits),
            "exact_snippet": any(exact_formula_match(f"{h.snippet} {h.abstract}", variants) for h in all_hits),
            "perm_match": any(permutation_formula_match(f"{h.title} {h.snippet} {h.abstract}", variants) for h in all_hits),
            "dft": contains_any(text_blob, DFT_KEYWORDS),
            "prototype": contains_any(text_blob, PROTOTYPE_KEYWORDS),
            "elec": contains_any(text_blob, ["electronic structure", "band gap"]),
            "formation": contains_any(text_blob, ["formation energy"]),
            "doi": any(bool(h.doi) for h in all_hits),
            "multi_source": len({h.source for h in all_hits}) >= 2,
            "only_elements": (not any(exact_formula_match(f"{h.title} {h.snippet}", variants) for h in all_hits)) and loose_element_system_match(text_blob, variants),
            "no_dft": not contains_any(text_blob, DFT_KEYWORDS),
            "false_positive": len(all_hits) == 0,
        }
        rep_score = score_reported_evidence(feature)

        unreported_features = {
            "exact_dft": strong_dft,
            "exact_no_dft": feature["exact_title"] and not feature["dft"],
            "perm": feature["perm_match"],
            "similar_family": feature["prototype"] and feature["dft"],
            "weak_element": feature["only_elements"],
            "google_checked": cov.google_scholar_checked,
            "openalex_checked": cov.openalex_checked,
            "semantic_checked": cov.semantic_scholar_checked,
            "permutation_checked": cov.permutation_checked,
            "citation_checked": cov.citation_neighbor_checked,
            "fulltext_checked": cov.full_text_checked,
        }
        unr_score = score_unreported_confidence(unreported_features)
        complete = coverage_complete(cov)
        label, reason = classify({"reported_evidence_score": rep_score, "unreported_confidence_score": unr_score}, complete, cov.source_error)

        conn.execute(
            "INSERT OR REPLACE INTO coverage(material, google_scholar_checked, openalex_checked, semantic_scholar_checked, crossref_checked, permutation_checked, citation_neighbor_checked, full_text_checked, source_error) VALUES(?,?,?,?,?,?,?,?,?)",
            (material, _bool(cov.google_scholar_checked), _bool(cov.openalex_checked), _bool(cov.semantic_scholar_checked), _bool(cov.crossref_checked), _bool(cov.permutation_checked), _bool(cov.citation_neighbor_checked), _bool(cov.full_text_checked), _bool(cov.source_error)),
        )
        best = all_hits[0] if all_hits else None
        conn.execute(
            "INSERT OR REPLACE INTO classifications(material, automated_status, reported_evidence_score, unreported_confidence_score, reason, best_weak_match, best_matching_paper, doi, url, final_manual_label, reviewer_notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (material, label, rep_score, unr_score, reason, "", best.title if best else "", best.doi if best else "", best.url if best else "", "", ""),
        )
        conn.commit()

        out_rows.append({
            "Final Rank": row.get("Final Rank", row.get("rank", None)),
            "Material": material,
            "Band Gap (eV)": row.get("Band Gap (eV)", row.get("band_gap", None)),
            "Stability": row.get("Stability", row.get("stability", "")),
            "OQMD Entry ID": row.get("OQMD Entry ID", row.get("entry_id", None)),
            "Automated Status": label,
            "Unreported Confidence Score": unr_score,
            "Reported Evidence Score": rep_score,
            "Best Weak Match": "",
            "Best Matching Paper": best.title if best else "",
            "DOI": best.doi if best else "",
            "URL": best.url if best else "",
            "Google Scholar Checked": cov.google_scholar_checked,
            "OpenAlex Checked": cov.openalex_checked,
            "Semantic Scholar Checked": cov.semantic_scholar_checked,
            "Permutation Checked": cov.permutation_checked,
            "Citation Neighbor Checked": cov.citation_neighbor_checked,
            "Full Text Checked": cov.full_text_checked,
            "Reason": reason,
            "Final Manual Label": "",
            "Reviewer Notes": "",
        })
        processed += 1

    out_df = pd.DataFrame(out_rows)
    export_outputs(out_df, output_dir)
    return {"status": "ok", "materials_processed": processed, "db": str(db_path), "output_dir": str(output_dir)}
