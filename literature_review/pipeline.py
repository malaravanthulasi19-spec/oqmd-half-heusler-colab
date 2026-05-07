from __future__ import annotations

from pathlib import Path
import pandas as pd

from .paths import INPUT_CSV, BACKUP_SQLITE, OUTPUT_DIR
from .database import connect
from .models import Coverage
from .formula_variants import build_variants, exact_formula_match, permutation_formula_match, loose_element_system_match
from .query_builder import gate1_queries, gate2_queries, gate3_queries, gate4_queries
from .source_router import normalize_hits
from .google_scholar_client import GoogleScholarClient
from .openalex_client import OpenAlexClient
from .semantic_scholar_client import SemanticScholarClient
from .crossref_client import CrossrefClient
from .evidence_scoring import contains_any, score_reported_evidence, score_unreported_confidence
from .constants import DFT_KEYWORDS, PROTOTYPE_KEYWORDS, ELEC_KEYWORDS, FORM_ENERGY_KEYWORDS
from .classification import classify
from .coverage import coverage_complete
from .checkpoint import is_query_completed, mark_query_completed
from .export import export_outputs


def load_input(path: Path = INPUT_CSV):
    return pd.read_csv(path)


def _run_query(conn, material: str, gate: str, source: str, query: str, search_fn):
    if is_query_completed(conn, material, gate, source, query):
        rows = conn.execute(
            'SELECT title,snippet,abstract,doi,url FROM hits WHERE material=? AND source=?',
            (material, source),
        ).fetchall()
        prior = [
            normalize_hits(source, [{"title": t, "snippet": s, "abstract": a, "doi": d, "url": u}])[0]
            for t, s, a, d, u in rows
        ]
        return prior, True, False
    try:
        raw = search_fn(query)
        hits = normalize_hits(source, raw)
        for h in hits:
            conn.execute(
                "INSERT OR IGNORE INTO hits(material,source,title,snippet,abstract,doi,url) VALUES(?,?,?,?,?,?,?)",
                (material, source, h.title, h.snippet, h.abstract, h.doi, h.url),
            )
        mark_query_completed(conn, material, gate, source, query)
        conn.commit()
        return hits, False, False
    except Exception:
        return [], False, True


def run(top_n: int = 10, input_csv: Path = INPUT_CSV, db_path: Path = BACKUP_SQLITE, output_dir: Path = OUTPUT_DIR):
    conn = connect(db_path)
    df = load_input(input_csv).head(top_n)

    gsch = GoogleScholarClient()
    oalex = OpenAlexClient()
    sem = SemanticScholarClient()
    cref = CrossrefClient()

    rows = []
    for _, r in df.iterrows():
        material = str(r.get("material") or r.get("formula") or r.iloc[0])
        variants = build_variants(material)
        cov = Coverage()
        source_errors = False
        all_hits = []

        gates = [
            ("gate1", gate1_queries(variants)),
            ("gate2", gate2_queries(variants)),
            ("gate3", gate3_queries(variants)),
        ]
        for gate, queries in gates:
            for q in queries:
                h, _, err = _run_query(conn, material, gate, "google_scholar", q, gsch.search)
                all_hits.extend(h)
                source_errors = source_errors or err
                h, _, err = _run_query(conn, material, gate, "openalex", q, oalex.search)
                all_hits.extend(h)
                source_errors = source_errors or err
                h, _, err = _run_query(conn, material, gate, "semantic_scholar", q, sem.search)
                all_hits.extend(h)
                source_errors = source_errors or err
                h, _, err = _run_query(conn, material, gate, "crossref", q, cref.search)
                all_hits.extend(h)
                source_errors = source_errors or err

        cov.google_scholar_checked = True
        cov.openalex_checked = True
        cov.semantic_scholar_checked = True
        cov.crossref_checked = True
        cov.source_error = source_errors

        has_strong = any(exact_formula_match((h.title + " " + h.snippet + " " + h.abstract), variants) and contains_any((h.title + " " + h.snippet + " " + h.abstract), DFT_KEYWORDS) for h in all_hits)
        if not has_strong:
            for q in gate4_queries(variants):
                h, _, err = _run_query(conn, material, "gate4", "google_scholar", q, gsch.search)
                all_hits.extend(h)
                source_errors = source_errors or err
            cov.permutation_checked = True

        feat = {"multi_source": len({h.source for h in all_hits}) > 1}
        for h in all_hits:
            txt = f"{h.title} {h.snippet} {h.abstract}"
            feat["exact_title"] = feat.get("exact_title", False) or exact_formula_match(h.title, variants)
            feat["exact_snippet"] = feat.get("exact_snippet", False) or exact_formula_match(h.snippet, variants)
            feat["perm_match"] = feat.get("perm_match", False) or permutation_formula_match(txt, variants)
            feat["only_elements"] = feat.get("only_elements", False) or (loose_element_system_match(txt, variants) and not exact_formula_match(txt, variants))
            feat["dft"] = feat.get("dft", False) or contains_any(txt, DFT_KEYWORDS)
            feat["prototype"] = feat.get("prototype", False) or contains_any(txt, PROTOTYPE_KEYWORDS)
            feat["elec"] = feat.get("elec", False) or contains_any(txt, ELEC_KEYWORDS)
            feat["formation"] = feat.get("formation", False) or contains_any(txt, FORM_ENERGY_KEYWORDS)
            feat["doi"] = feat.get("doi", False) or bool(h.doi)

        reported = score_reported_evidence(feat)
        unreported = score_unreported_confidence({
            "exact_dft": feat.get("exact_title") and feat.get("dft"),
            "exact_no_dft": feat.get("exact_title") and not feat.get("dft"),
            "perm": feat.get("perm_match"),
            "similar_family": feat.get("prototype"),
            "weak_element": feat.get("only_elements"),
            "google_checked": cov.google_scholar_checked,
            "openalex_checked": cov.openalex_checked,
            "semantic_checked": cov.semantic_scholar_checked,
            "permutation_checked": cov.permutation_checked,
        })

        complete = coverage_complete(cov)
        label, reason = classify({"reported_evidence_score": reported, "unreported_confidence_score": unreported}, complete, source_errors)

        conn.execute(
            "INSERT OR REPLACE INTO classifications(material, automated_status, reported_evidence_score, unreported_confidence_score, reason) VALUES(?,?,?,?,?)",
            (material, label, reported, unreported, reason),
        )
        conn.execute(
            "INSERT OR REPLACE INTO coverage(material,google_scholar_checked,openalex_checked,semantic_scholar_checked,crossref_checked,permutation_checked,citation_neighbor_checked,full_text_checked,source_error) VALUES(?,?,?,?,?,?,?,?,?)",
            (material, int(cov.google_scholar_checked), int(cov.openalex_checked), int(cov.semantic_scholar_checked), int(cov.crossref_checked), int(cov.permutation_checked), 0, 0, int(source_errors)),
        )
        conn.commit()

        rows.append({"Material": material, "Automated Status": label, "Reported Evidence Score": reported, "Unreported Confidence Score": unreported, "Reason": reason})

    out_df = pd.DataFrame(rows)
    export_outputs(out_df, Path(output_dir))
    return {"materials_loaded": len(df), "db": str(db_path), "output_dir": str(output_dir), "status": "ok"}
