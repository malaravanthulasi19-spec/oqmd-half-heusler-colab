import pandas as pd
import pytest
from literature_review.pipeline import run, _extract_material


class _BaseClient:
    def __init__(self, fail=False, payload=None):
        self.fail = fail
        self.payload = payload

    def search(self, query, **kwargs):
        if self.fail:
            raise RuntimeError('source down')
        if self.payload is not None:
            return self.payload
        return [{"title": f"BaTbPa DFT half-Heusler {query}", "snippet": "C1b first principles", "doi": "10.1/x", "url": "https://example.org"}]


def _patch_clients(monkeypatch, fail_semantic=False, fail_crossref=False, payload=None):
    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: _BaseClient(payload=payload))
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: _BaseClient(payload=payload))
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: _BaseClient(fail=fail_semantic, payload=payload))
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: _BaseClient(fail=fail_crossref, payload=payload))


def test_run_topn_and_outputs(tmp_path, monkeypatch):
    _patch_clients(monkeypatch)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}, {"material": "NaMgN"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    res = run(top_n=10, input_csv=inp, db_path=tmp_path / 'run.sqlite3', output_dir=out_dir)
    assert res['materials_loaded'] == 2
    assert (out_dir / '05_all_hits_audit.csv').exists()


def test_material_column_prefers_capitalized_material(tmp_path, monkeypatch):
    _patch_clients(monkeypatch)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Rank": 1, "Material": "BaTbPa", "Band Gap (eV)": 0.8, "Stability": "stable"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Material'] == 'BaTbPa'
    assert df.iloc[0]['Band Gap (eV)'] == 0.8


def test_missing_material_column_raises_clear_error():
    with pytest.raises(ValueError, match='No material/formula column found'):
        _extract_material(pd.Series({'Rank': 1}))


def test_false_positive_cases_and_real_positive(tmp_path, monkeypatch):
    payload = [
        {"title": "CANDU thermalhydraulic code stability", "snippet": "reactor code", "abstract": "Lyapunov analysis"},
        {"title": "Nandu River microplastic study", "snippet": "river", "abstract": "data protection GDPR"},
        {"title": "Ca Nd U density functional theory half-Heusler", "snippet": "first principles", "doi": ["10.9/x"], "url": ["https://x"]},
    ]
    _patch_clients(monkeypatch, payload=payload)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'fp.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Automated Status'] == 'reported_dft'
    assert df.iloc[0]['false_positive_count'] >= 1
    assert df.iloc[0]['dft_formula_hit_count'] >= 1


def test_nandu_and_gdpr_not_reported_dft(tmp_path, monkeypatch):
    payload = [{"title": "Nandu River microplastic data protection authority update", "snippet": "GDPR"}]
    _patch_clients(monkeypatch, payload=payload)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "NaNdU"}, {"Material": "CaNdPa"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'n.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert (df['Automated Status'] != 'reported_dft').all()


def test_crossref_list_fields_safe_and_dedup_failed_sources(tmp_path, monkeypatch):
    _patch_clients(monkeypatch, fail_crossref=True, payload=[{"title": "CaNdU half-Heusler first principles", "doi": ["10.1/a"]}])
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "CaNdU"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'c.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert 'crossref:source down' in df.iloc[0]['failed_sources']
    assert df.iloc[0]['failed_sources'].count('crossref:source down') == 1


def test_completed_queries_skipped(tmp_path, monkeypatch):
    calls = {"n": 0}

    class C(_BaseClient):
        def search(self, query, **kwargs):
            calls['n'] += 1
            return super().search(query, **kwargs)

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: C())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: C())
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}]).to_csv(inp, index=False)
    db = tmp_path / 'run.sqlite3'
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=db, output_dir=out_dir)
    first = calls['n']
    run(top_n=10, input_csv=inp, db_path=db, output_dir=out_dir)
    assert calls['n'] == first
