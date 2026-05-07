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
from .checkpoint import is_query_completed, mark_query_completed
from .export import export_outputs


FALSE_POSITIVE_TERMS = [
    "candu",
    "nandu river",
    "gdpr",
    "data protection",
    "lyapunov",
    "microplastic",
    "river",
    "thermalhydraulic code",
]

DFT_STRONG_TERMS = ["dft", "first principles", "first-principles", "density functional theory", "electronic structure"]


def _is_false_positive_text(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in FALSE_POSITIVE_TERMS)


def load_input(path: Path = INPUT_CSV):
    return pd.read_csv(path)


def _first_present_column(row: pd.Series, candidates: list[str]):
    for col in candidates:
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            return row[col]
    return None


def _extract_material(row: pd.Series) -> str:
    candidates = ["Material", "material", "Formula", "formula", "Composition", "composition"]
    value = _first_present_column(row, candidates)
    if value is None:
        raise ValueError(f"No material/formula column found. Available columns: {list(row.index)}")
    return str(value).strip()


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
    except Exception as exc:
        return [], False, str(exc)


def run(top_n: int = 10, input_csv: Path = INPUT_CSV, db_path: Path = BACKUP_SQLITE, output_dir: Path = OUTPUT_DIR):
    conn = connect(db_path)
    df = load_input(input_csv).head(top_n)

    gsch = GoogleScholarClient()
    oalex = OpenAlexClient()
    sem = SemanticScholarClient()
    cref = CrossrefClient()

    rows = []
    for idx, r in df.iterrows():
        material = _extract_material(r)
        print(f"Processing {idx + 1}/{len(df)}: {material}")
        variants = build_variants(material)
        cov = Coverage()
        failed_sources: set[str] = set()
        all_hits = []
        completed_query_count = 0

        gates = [
            ("gate1", gate1_queries(variants)),
            ("gate2", gate2_queries(variants)),
            ("gate3", gate3_queries(variants)),
        ]
        for gate, queries in gates:
            for q in queries:
                print(f"  {gate} query: {q}")
                h, _, err = _run_query(conn, material, gate, "google_scholar", q, gsch.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"google_scholar:{err}")
                else:
                    completed_query_count += 1
                h, _, err = _run_query(conn, material, gate, "openalex", q, oalex.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"openalex:{err}")
                else:
                    completed_query_count += 1
                h, _, err = _run_query(conn, material, gate, "semantic_scholar", q, sem.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"semantic_scholar:{err}")
                else:
                    completed_query_count += 1
                h, _, err = _run_query(conn, material, gate, "crossref", q, cref.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"crossref:{err}")
                else:
                    completed_query_count += 1

        cov.google_scholar_checked = True
        cov.openalex_checked = True
        cov.semantic_scholar_checked = not any(x.startswith("semantic_scholar:") for x in failed_sources)
        cov.crossref_checked = not any(x.startswith("crossref:") for x in failed_sources)
        cov.source_error = bool(failed_sources)

        has_strong = any(exact_formula_match((h.title + " " + h.snippet + " " + h.abstract), variants) and contains_any((h.title + " " + h.snippet + " " + h.abstract), DFT_KEYWORDS) for h in all_hits)
        if not has_strong:
            for q in gate4_queries(variants):
                h, _, err = _run_query(conn, material, "gate4", "google_scholar", q, gsch.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"google_scholar:{err}")
                else:
                    completed_query_count += 1
            cov.permutation_checked = True

        feat = {"multi_source": len({h.source for h in all_hits}) > 1}
        false_positive_count = 0
        valid_hits = []
        exact_formula_hit_count = 0
        dft_formula_hit_count = 0
        for h in all_hits:
            txt = f"{h.title} {h.snippet} {h.abstract}"
            exact = exact_formula_match(txt, variants)
            perm = permutation_formula_match(txt, variants)
            dft = contains_any(txt, DFT_STRONG_TERMS)
            false_positive = _is_false_positive_text(txt) and not (exact or perm)
            if false_positive:
                false_positive_count += 1
            if exact:
                exact_formula_hit_count += 1
            if (exact or perm) and dft and (not false_positive):
                dft_formula_hit_count += 1

            feat["exact_title"] = feat.get("exact_title", False) or exact_formula_match(h.title, variants)
            feat["exact_snippet"] = feat.get("exact_snippet", False) or exact_formula_match(h.snippet, variants)
            feat["perm_match"] = feat.get("perm_match", False) or perm
            feat["only_elements"] = feat.get("only_elements", False) or (loose_element_system_match(txt, variants) and not (exact or perm))
            feat["dft"] = feat.get("dft", False) or dft
            feat["prototype"] = feat.get("prototype", False) or contains_any(txt, PROTOTYPE_KEYWORDS)
            feat["elec"] = feat.get("elec", False) or contains_any(txt, ELEC_KEYWORDS)
            feat["formation"] = feat.get("formation", False) or contains_any(txt, FORM_ENERGY_KEYWORDS)
            feat["doi"] = feat.get("doi", False) or bool(h.doi)

            if (exact or perm) and not false_positive:
                valid_hits.append((3 if dft else 2, "exact_or_perm_formula", h))
            elif feat["only_elements"] and not false_positive:
                valid_hits.append((1, "element_system_weak", h))

        valid_hits.sort(key=lambda x: x[0], reverse=True)

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

        complete = cov.google_scholar_checked and cov.openalex_checked
        has_exact_or_perm = feat.get("exact_title") or feat.get("exact_snippet") or feat.get("perm_match")
        if dft_formula_hit_count > 0 and has_exact_or_perm and false_positive_count == 0:
            label, reason = "reported_dft", "exact/permutation formula + DFT context"
        elif has_exact_or_perm and false_positive_count == 0:
            label, reason = "reported_non_dft", "formula-level evidence without DFT"
        else:
            label, reason = classify({"reported_evidence_score": reported, "unreported_confidence_score": unreported}, complete, False)
        if (not complete) or (not any(h.source == "google_scholar" for h in all_hits) and not any(h.source == "openalex" for h in all_hits) and failed_sources):
            label, reason = "incomplete_search_retry_needed", "required sources/gates incomplete"

        conn.execute(
            "INSERT OR REPLACE INTO classifications(material, automated_status, reported_evidence_score, unreported_confidence_score, reason) VALUES(?,?,?,?,?)",
            (material, label, reported, unreported, reason),
        )
        conn.execute(
            "INSERT OR REPLACE INTO coverage(material,google_scholar_checked,openalex_checked,semantic_scholar_checked,crossref_checked,permutation_checked,citation_neighbor_checked,full_text_checked,source_error) VALUES(?,?,?,?,?,?,?,?,?)",
            (material, int(cov.google_scholar_checked), int(cov.openalex_checked), int(cov.semantic_scholar_checked), int(cov.crossref_checked), int(cov.permutation_checked), 0, 0, int(bool(failed_sources))),
        )
        conn.commit()

        print(f"  source status: gs={cov.google_scholar_checked} oa={cov.openalex_checked} sem={cov.semantic_scholar_checked} cr={cov.crossref_checked}")
        print(f"  hit count: {len(all_hits)}")
        print(f"  final label: {label}")
        rows.append({
            "Rank": r.get("Rank"),
            "Material": material,
            "Band Gap (eV)": r.get("Band Gap (eV)"),
            "Stability": r.get("Stability"),
            "OQMD Entry ID": r.get("OQMD Entry ID"),
            "Space Group": r.get("Space Group"),
            "Automated Status": label,
            "Reported Evidence Score": reported,
            "Unreported Confidence Score": unreported,
            "Reason": reason,
            "google_scholar_checked": cov.google_scholar_checked,
            "openalex_checked": cov.openalex_checked,
            "semantic_scholar_checked": cov.semantic_scholar_checked,
            "crossref_checked": cov.crossref_checked,
            "permutation_checked": cov.permutation_checked,
            "citation_neighbor_checked": cov.citation_neighbor_checked,
            "full_text_checked": cov.full_text_checked,
            "source_error": cov.source_error,
            "failed_sources": " | ".join(sorted(failed_sources)),
            "completed_query_count": completed_query_count,
            "hit_count": len(all_hits),
            "best_paper_title": valid_hits[0][2].title if valid_hits else "",
            "best_doi": valid_hits[0][2].doi if valid_hits else "",
            "best_url": valid_hits[0][2].url if valid_hits else "",
            "best_evidence_match_type": valid_hits[0][1] if valid_hits else "",
            "best_evidence_source": valid_hits[0][2].source if valid_hits else "",
            "false_positive_count": false_positive_count,
            "valid_evidence_hit_count": len(valid_hits),
            "exact_formula_hit_count": exact_formula_hit_count,
            "dft_formula_hit_count": dft_formula_hit_count,
            "final_manual_label": "",
            "reviewer_notes": "",
        })

    out_df = pd.DataFrame(rows)
    export_outputs(out_df, Path(output_dir))
    return {"materials_loaded": len(df), "db": str(db_path), "output_dir": str(output_dir), "status": "ok"}
