import pandas as pd

from literature_review.formula_variants import build_variants, exact_formula_match
from literature_review.pipeline import run


def test_formula_family_matches_and_false_positive_guards():
    v = build_variants("HfNiSn")
    assert exact_formula_match("HfNiSn-based thermoelectric", v)
    assert exact_formula_match("HfNiSn1-xSbx", v)
    assert exact_formula_match("HfNiSn:Sb", v)
    assert exact_formula_match("(Hf,Zr)NiSn", v)
    assert not exact_formula_match("CANDU", build_variants("CaNdU"))


def test_candidate_outputs_include_new_tiers(tmp_path, monkeypatch):
    class C:
        def search(self, query, **kwargs):
            return [{"title": f"{query}", "snippet": "", "abstract": "", "doi": "", "url": ""}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: C())
    inp = tmp_path / "in.csv"
    pd.DataFrame([{"Material": "HfNiSn"}]).to_csv(inp, index=False)
    out = tmp_path / "out"
    run(input_csv=inp, output_dir=out, db_path=tmp_path / "d.sqlite3")
    df = pd.read_csv(out / "05_all_hits_audit.csv")
    assert "novelty_confidence_tier" in df.columns
    assert "practicality_tier" in df.columns

