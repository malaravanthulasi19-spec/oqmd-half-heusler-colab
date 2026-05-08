from literature_review.evidence_depth_scoring import compute_reported_depth_score
from literature_review.pipeline import run
import pandas as pd


def test_formula_only_low_score():
    d = compute_reported_depth_score({"title": "BaTbPa", "exact_formula_match": True, "formula_level_evidence_found": True})
    assert 10 <= d["reported_depth_score"] <= 29


def test_formula_halfheusler_medium_score():
    d = compute_reported_depth_score({"title": "BaTbPa half-Heusler C1b", "exact_formula_match": True, "spaced_formula_match": True, "formula_level_evidence_found": True})
    assert 30 <= d["reported_depth_score"] <= 49


def test_formula_dft_high_score():
    d = compute_reported_depth_score({"title": "BaTbPa density functional theory VASP", "exact_formula_match": True, "spaced_formula_match": True, "formula_permutation_match": True, "formula_level_evidence_found": True})
    assert d["reported_depth_score"] >= 50


def test_deep_study_score():
    txt = "BaTbPa DFT DOS band structure elastic constants C11 C12 C44 phonon dispersion thermoelectric Seebeck ZT"
    d = compute_reported_depth_score({"title": txt, "exact_formula_match": True, "formula_level_evidence_found": True})
    assert d["reported_depth_score"] >= 75


def test_element_only_cannot_be_high():
    d = compute_reported_depth_score({"title": "barium terbium protactinium thermoelectric", "evidence_tier": "TIER_1_ELEMENT_SYSTEM_WEAK", "formula_level_evidence_found": False})
    assert d["reported_depth_score"] < 50


def test_false_positive_penalty_applies():
    d = compute_reported_depth_score({"title": "CANDU Nandu GDPR", "false_positive_flag": True, "formula_level_evidence_found": False})
    assert d["false_positive_penalty"] <= -50


def test_depth_fields_appear_in_exports_and_keyword_only_not_reported_dft(tmp_path, monkeypatch):
    class NonFormulaDft:
        def search(self, query, **kwargs):
            return [{"title": "electronic structure density functional theory in alloy family", "snippet": "half-Heusler", "doi": ""}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: NonFormulaDft())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: NonFormulaDft())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: NonFormulaDft())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: NonFormulaDft())

    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "BaTbPa"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '07_all_hits_audit.csv')
    for c in [
        "reported_depth_score", "reported_depth_tier", "property_groups_detected", "formula_evidence_score",
        "half_heusler_context_score", "dft_method_score", "property_depth_score", "false_positive_penalty", "manual_warning"
    ]:
        assert c in df.columns
    assert df.iloc[0]["Automated Status"] != "reported_dft"
