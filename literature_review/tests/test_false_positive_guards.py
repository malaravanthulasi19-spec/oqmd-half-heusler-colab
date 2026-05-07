import pandas as pd

from literature_review.formula_variants import build_variants, exact_formula_match
from literature_review.pipeline import run
from literature_review.source_router import normalize_hits


def test_candu_and_nandu_do_not_match_compact_formulas():
    assert not exact_formula_match("CANDU thermalhydraulic code", build_variants("CaNdU"))
    assert not exact_formula_match("Nandu River microplastic study", build_variants("NaNdU"))


def test_gdpr_text_not_formula_match():
    assert not exact_formula_match("GDPR and data protection compliance", build_variants("CaNdPa"))


def test_crossref_list_fields_are_normalized_strings():
    hits = normalize_hits("crossref", [{"title": ["A", "B"], "abstract": {"k": [1, 2]}, "doi": ["10.1/x"]}])
    assert isinstance(hits[0].title, str)
    assert isinstance(hits[0].abstract, str)
    assert isinstance(hits[0].doi, str)


def test_pipeline_false_positives_and_true_positive(tmp_path, monkeypatch):
    class Bad:
        def search(self, query, **kwargs):
            if "NaNdU" in query:
                return [{"title": "Nandu River microplastic monitoring", "snippet": "river pollution", "doi": ""}]
            return [{"title": "CANDU thermalhydraulic code analysis", "snippet": "reactor stability Lyapunov", "doi": ""}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Bad())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Bad())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Bad())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Bad())

    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}, {"Material": "NaNdU"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=2, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Automated Status'] != 'reported_dft'
    assert df.iloc[1]['Automated Status'] != 'reported_dft'

    class Good:
        def search(self, query, **kwargs):
            return [{"title": "Ca Nd U density functional theory half-Heusler", "snippet": "electronic structure", "doi": "10.1/real"}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Good())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Good())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Good())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Good())
    out_dir2 = tmp_path / 'out2'
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd2.sqlite3', output_dir=out_dir2)
    df2 = pd.read_csv(out_dir2 / '05_all_hits_audit.csv')
    assert df2.iloc[0]['Automated Status'] == 'reported_dft'


def test_failed_sources_deduplicated(tmp_path, monkeypatch):
    class Fail:
        def search(self, query, **kwargs):
            raise RuntimeError('source down')

    class Ok:
        def search(self, query, **kwargs):
            return [{"title": "CaNdU half-Heusler first principles", "snippet": "", "doi": "10.1/x"}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.CROSSREF_ENABLED', True)
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Fail())
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['failed_sources'].count('crossref:source down') == 1


def test_weak_element_only_is_not_found_and_no_best_paper(tmp_path, monkeypatch):
    class Weak:
        def search(self, query, **kwargs):
            return [{"title": "Asthma and TB analysis in children", "snippet": "barium terbium protactinium element words", "doi": "10.1/weak"}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Weak())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Weak())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Weak())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Weak())
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "BaTbPa"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Automated Status'] == 'not_found_after_protocol'
    assert df.iloc[0]['exact_formula_hit_count'] == 0
    assert df.iloc[0]['dft_formula_hit_count'] == 0
    assert not bool(df.iloc[0]['formula_level_evidence_found'])
    assert pd.isna(df.iloc[0]['best_paper_title']) or df.iloc[0]['best_paper_title'] == ''


def test_crossref_disabled_by_default(tmp_path, monkeypatch):
    calls = {"crossref": 0}

    class Ok:
        def search(self, query, **kwargs):
            return [{"title": "CaNdU half-Heusler first principles", "snippet": "", "doi": "10.1/x"}]

    class Crossref:
        def search(self, query, **kwargs):
            calls['crossref'] += 1
            return []

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Ok())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Crossref())
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}]).to_csv(inp, index=False)
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=tmp_path / 'out')
    assert calls['crossref'] == 0


def test_reported_non_dft_requires_formula_level(tmp_path, monkeypatch):
    class NonDft:
        def search(self, query, **kwargs):
            return [{"title": "CaNdU half-Heusler synthesis study", "snippet": "experimental report", "doi": "10.1/nd"}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: NonDft())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: NonDft())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: NonDft())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: NonDft())
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=1, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Automated Status'] == 'reported_non_dft'
    assert df.iloc[0]['formula_level_evidence_found']
