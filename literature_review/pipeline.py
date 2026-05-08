from __future__ import annotations

from pathlib import Path
import pandas as pd

from .paths import INPUT_CSV, BACKUP_SQLITE, OUTPUT_DIR
from .database import connect
from .models import Coverage
from .formula_variants import build_variants, exact_formula_match, permutation_formula_match, loose_element_system_match
from .query_builder import gate1_queries, gate2_queries, gate3_queries, gate4_queries, profile_queries
from .source_router import normalize_hits
from .google_scholar_client import GoogleScholarClient
from .openalex_client import OpenAlexClient
from .semantic_scholar_client import SemanticScholarClient
from .crossref_client import CrossrefClient
from .evidence_scoring import contains_any, score_reported_evidence, score_unreported_confidence
from .constants import DFT_KEYWORDS, PROTOTYPE_KEYWORDS, ELEC_KEYWORDS, FORM_ENERGY_KEYWORDS
from .classification import classify
from .checkpoint import is_query_completed, mark_query_completed
from .export import export_outputs, export_material_screening_master
from .material_selection_scoring import compute_material_selection_scores
from .evidence_depth_scoring import compute_reported_depth_score
from .keypaper_filters import detect_keypaper_context, compute_keypaper_depth_score
from .composition_equivalence import formula_permutations
from .fast_literature_screening import compute_local_material_gate
from .strategic_classifier import load_prior_material_evidence


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
HALF_HEUSLER_TERMS = ["half-heusler", "half heusler", "c1b", "mgagas", "f-43m", "space group 216"]


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


def run(
    top_n: int = 10,
    input_csv: Path = INPUT_CSV,
    db_path: Path = BACKUP_SQLITE,
    output_dir: Path = OUTPUT_DIR,
    enable_crossref: bool = False,
    search_profile: str = "candidate_screening",
    recall_second_pass: bool = False,
    calibration_passed: bool = True,
    search_mode: str = "fast",
):
    if search_mode not in {"fast", "adaptive", "deep"}:
        raise ValueError("search_mode must be one of: fast, adaptive, deep")
    if search_profile == "candidate_screening_expanded" and top_n > 10:
        print("Expanded search profile is expensive. Recommended top_n=10 first.")
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
        prior = load_prior_material_evidence(None, material)
        r = r.copy()
        for k, v in prior.items():
            r[k] = v
        gate_meta = compute_local_material_gate(r.to_dict())
        variants = build_variants(material)
        cov = Coverage()
        failed_sources: set[str] = set()
        all_hits = []
        completed_query_count = 0
        prototype = str(r.get("Prototype", "") or "")
        space_group = str(r.get("Space Group", "") or "")
        input_half_heusler_verified = any(k in prototype.lower() for k in ["c1b", "halfheusler", "half-heusler", "mgagas"]) or space_group == "F-43m"

        prof = profile_queries(variants, search_profile)
        if search_mode in {"fast", "adaptive"}:
            perms = formula_permutations(material)[:6]
            base_formula = perms[0] if perms else variants.compact
            gate1 = [f"\"{p}\"" for p in perms]
            gate1 += [f"\"{base_formula}\" half-Heusler DFT", f"\"{base_formula}\" thermoelectric"]
            gate2 = []
            if search_mode == "adaptive" and gate_meta.get("should_search_literature", False):
                gate2 = [
                    f"{base_formula} (\"DFT\" OR \"density functional theory\" OR \"first principles\")",
                    f"{base_formula} (\"half-Heusler\" OR \"C1b\" OR \"MgAgAs\" OR \"F-43m\")",
                    f"{base_formula} (\"band structure\" OR \"DOS\" OR \"density of states\")",
                    f"{base_formula} (\"phonon dispersion\" OR \"mechanical stability\")",
                    f"{base_formula} (\"thermoelectric\" OR \"Seebeck\" OR \"ZT\" OR \"BoltzTrap\")",
                ]
            gates = [("gate1", gate1), ("gate2", gate2), ("gate3", [])]
        else:
            gates = [("gate1", prof["gate1"]), ("gate2", prof["gate2"]), ("gate3", prof["gate3"]) ]
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
                if enable_crossref and gate == "gate1":
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
        if not has_strong and search_mode == "deep":
            for q in gate4_queries(variants):
                h, _, err = _run_query(conn, material, "gate4", "google_scholar", q, gsch.search)
                all_hits.extend(h)
                if err:
                    failed_sources.add(f"google_scholar:{err}")
                else:
                    completed_query_count += 1
            cov.permutation_checked = True

        feat = {"multi_source": len({h.source for h in all_hits}) > 1}
        second_pass_used=False
        second_pass_formula_hits=0
        second_pass_dft_hits=0
        false_positive_count = 0
        valid_hits = []
        exact_formula_hit_count = 0
        dft_formula_hit_count = 0
        literature_half_heusler_context_found = False
        for h in all_hits:
            txt = f"{h.title} {h.snippet} {h.abstract}"
            exact = exact_formula_match(txt, variants)
            perm = permutation_formula_match(txt, variants)
            dft = contains_any(txt, DFT_STRONG_TERMS)
            hh_ctx = contains_any(txt, HALF_HEUSLER_TERMS)
            false_positive = _is_false_positive_text(txt) and not (exact or perm)
            if false_positive:
                false_positive_count += 1
            if exact:
                exact_formula_hit_count += 1
            if (exact or perm) and dft and (not false_positive):
                dft_formula_hit_count += 1
            if (exact or perm) and hh_ctx and (not false_positive):
                literature_half_heusler_context_found = True

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
            elif loose_element_system_match(txt, variants) and not false_positive:
                valid_hits.append((1, "element_system_weak", h))

        valid_hits.sort(key=lambda x: x[0], reverse=True)

        best_keypaper = {"keypaper_depth_score": 0, "keypaper_depth_tier": "SHALLOW_OR_NO_RELEVANT_EVIDENCE", "keypaper_context_groups_detected": 0, "keypaper_manual_warning": ""}
        best_keypaper_ctx = {}

        best_depth = {
            "reported_depth_score": 0,
            "reported_depth_tier": "NO_VALID_EVIDENCE",
            "property_groups_detected": "",
            "formula_evidence_score": 0,
            "half_heusler_context_score": 0,
            "dft_method_score": 0,
            "property_depth_score": 0,
            "false_positive_penalty": 0,
            "manual_warning": "",
        }
        for _, tier_name, hit in valid_hits:
            txt = f"{hit.title} {hit.snippet} {hit.abstract}"
            exact = exact_formula_match(txt, variants)
            perm = permutation_formula_match(txt, variants)
            depth = compute_reported_depth_score({
                "title": hit.title,
                "snippet": hit.snippet,
                "abstract": hit.abstract,
                "exact_formula_match": exact,
                "spaced_formula_match": exact_formula_match(txt, variants),
                "hyphenated_formula_match": exact_formula_match(txt.replace(" ", "-"), variants),
                "alloy_doped_formula_match": any(x in txt.lower() for x in ["doped", "alloy"]),
                "formula_permutation_match": perm,
                "false_positive_flag": _is_false_positive_text(txt) and not (exact or perm),
                "evidence_tier": "TIER_1_ELEMENT_SYSTEM_WEAK" if tier_name == "element_system_weak" else "TIER_3_FORMULA_LEVEL",
                "formula_level_evidence_found": bool(exact or perm),
            })
            if depth["reported_depth_score"] > best_depth["reported_depth_score"]:
                best_depth = depth

            kctx = detect_keypaper_context(txt)
            kdepth = compute_keypaper_depth_score({**kctx, "formula_level_evidence_found": bool(exact or perm), "false_positive_flag": _is_false_positive_text(txt) and not (exact or perm), "evidence_tier": "TIER_1_ELEMENT_SYSTEM_WEAK" if tier_name == "element_system_weak" else "TIER_3_FORMULA_LEVEL"})
            if kdepth["keypaper_depth_score"] > best_keypaper["keypaper_depth_score"]:
                best_keypaper = kdepth
                best_keypaper_ctx = kctx

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
        formula_level_evidence_found = bool(has_exact_or_perm and false_positive_count == 0)
        if recall_second_pass and search_profile == "validation_recall" and not formula_level_evidence_found:
            second_pass_used=True
            for q in [f"\"{variants.compact}\" half-Heusler", f"\"{variants.compact}\" thermoelectric", f"\"{variants.compact}\" DFT", f"\"{variants.compact}\" first principles", f"\"{variants.compact}\" electronic structure", f"\"{variants.compact}\" band structure"]:
                h, _, _ = _run_query(conn, material, "gate_second_pass", "google_scholar", q, gsch.search)
                for hit in h:
                    t=f"{hit.title} {hit.snippet} {hit.abstract}"
                    if exact_formula_match(t, variants): second_pass_formula_hits += 1
                    if exact_formula_match(t, variants) and contains_any(t, DFT_STRONG_TERMS): second_pass_dft_hits += 1
                all_hits.extend(h)
            formula_level_evidence_found = formula_level_evidence_found or second_pass_formula_hits > 0
            dft_formula_hit_count += second_pass_dft_hits

        if dft_formula_hit_count > 0 and formula_level_evidence_found:
            if input_half_heusler_verified or literature_half_heusler_context_found or contains_any(f"{prototype} {space_group}", HALF_HEUSLER_TERMS):
                label, reason = "reported_dft", "exact/permutation formula + DFT context"
            else:
                label, reason = "ambiguous_manual_review", "formula + DFT found, but half-Heusler context not confirmed"
        elif formula_level_evidence_found:
            label, reason = "reported_non_dft", "formula-level evidence without DFT"
        elif complete and exact_formula_hit_count == 0 and dft_formula_hit_count == 0 and not formula_level_evidence_found and calibration_passed:
            label, reason = "not_found_after_protocol", "no exact formula-level literature evidence found; only weak element-system hits"
        elif complete and not calibration_passed:
            label, reason = "incomplete_search_retry_needed", "PIPELINE_NOT_CALIBRATED: Do not use not_found_after_protocol as novelty evidence until validation passes."
        else:
            label, reason = classify({"reported_evidence_score": reported, "unreported_confidence_score": unreported}, complete, False)
        if best_keypaper["keypaper_depth_score"] >= 80:
            if formula_level_evidence_found and dft_formula_hit_count > 0 and (input_half_heusler_verified or literature_half_heusler_context_found):
                label, reason = "reported_dft", "deep key-paper-style DFT/property study detected"
            else:
                label, reason = "ambiguous_manual_review", "deep key-paper-style literature evidence requires manual review"
        elif best_keypaper["keypaper_depth_score"] >= 60:
            unreported = max(0, unreported - 20)
        elif best_depth["reported_depth_score"] >= 50 and label == "not_found_after_protocol":
            label, reason = "ambiguous_manual_review", "DFT-level depth evidence requires manual verification"
            unreported = max(0, unreported - 35)
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
        best_hit = valid_hits[0] if valid_hits and valid_hits[0][1] != "element_system_weak" else None
        score_cols = compute_material_selection_scores({**r.to_dict(), **best_depth, "Automated Status": label, "formula_level_evidence_found": formula_level_evidence_found, "exact_formula_hit_count": exact_formula_hit_count, "dft_formula_hit_count": dft_formula_hit_count, "google_scholar_checked": cov.google_scholar_checked, "openalex_checked": cov.openalex_checked, "semantic_scholar_checked": cov.semantic_scholar_checked, "source_error": cov.source_error, "best_paper_title": best_hit[2].title if best_hit else "", "best_doi": best_hit[2].doi if best_hit else ""})
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
            "best_paper_title": best_hit[2].title if best_hit else "",
            "best_doi": best_hit[2].doi if best_hit else "",
            "best_url": best_hit[2].url if best_hit else "",
            "best_evidence_match_type": valid_hits[0][1] if valid_hits else "",
            "best_evidence_source": valid_hits[0][2].source if valid_hits else "",
            "false_positive_count": false_positive_count,
            "valid_evidence_hit_count": len(valid_hits),
            "exact_formula_hit_count": exact_formula_hit_count,
            "dft_formula_hit_count": dft_formula_hit_count,
            "formula_level_evidence_found": formula_level_evidence_found,
            "novelty_confidence_tier": "REPORTED_DFT" if label=="reported_dft" else ("REPORTED_NON_DFT" if label=="reported_non_dft" else ("INCOMPLETE_SEARCH" if label=="incomplete_search_retry_needed" else ("AMBIGUOUS_REVIEW_REQUIRED" if label=="ambiguous_manual_review" else ("HIGH_CONFIDENCE_UNREPORTED" if calibration_passed else "LOW_CONFIDENCE_UNREPORTED")))),
            "input_half_heusler_verified": input_half_heusler_verified,
            "literature_half_heusler_context_found": literature_half_heusler_context_found,
            "half_heusler_filter_status": (
                "MISSING_PROTOTYPE_METADATA" if not prototype.strip() and not space_group.strip()
                else "INPUT_CONFIRMED_C1B" if input_half_heusler_verified
                else "LITERATURE_CONFIRMED_HALF_HEUSLER" if literature_half_heusler_context_found
                else "NOT_HALF_HEUSLER_REVIEW"
            ),
            "second_pass_used": second_pass_used,
            "second_pass_formula_hits": second_pass_formula_hits,
            "second_pass_dft_hits": second_pass_dft_hits,
            "final_manual_label": "",
            "reviewer_notes": "",
            "reported_depth_score": best_depth["reported_depth_score"],
            "reported_depth_tier": best_depth["reported_depth_tier"],
            "property_groups_detected": best_depth["property_groups_detected"],
            "formula_evidence_score": best_depth["formula_evidence_score"],
            "half_heusler_context_score": best_depth["half_heusler_context_score"],
            "dft_method_score": best_depth["dft_method_score"],
            "property_depth_score": best_depth["property_depth_score"],
            "false_positive_penalty": best_depth["false_positive_penalty"],
            "manual_warning": best_depth["manual_warning"],
            **best_keypaper,
            **best_keypaper_ctx,
            "search_mode_used": search_mode,
            "local_gate_status": gate_meta.get("local_gate_status", ""),
            "local_gate_reason": gate_meta.get("local_gate_reason", ""),
            "query_budget_used": completed_query_count,
            "query_budget_skipped": 0,
            "search_stopped_early": False,
            "early_stop_reason": "",
            "deep_search_used": search_mode == "deep",
            **score_cols,
        })

    out_df = pd.DataFrame(rows)
    out_dir = Path(output_dir)
    export_outputs(out_df, out_dir)
    master_path = export_material_screening_master(rows, hits=[], coverage=[], output_dir=out_dir)
    print(f"Master workbook: {master_path}")
    return {"materials_loaded": len(df), "db": str(db_path), "output_dir": str(output_dir), "master_workbook": str(master_path), "status": "ok"}
