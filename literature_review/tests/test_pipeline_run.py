import pandas as pd
import pytest
from literature_review.pipeline import run, _extract_material


class _BaseClient:
    def __init__(self, fail=False):
        self.fail = fail

    def search(self, query, **kwargs):
        if self.fail:
            raise RuntimeError('source down')
        return [{"title": f"BaTbPa DFT half-Heusler {query}", "snippet": "C1b first principles", "doi": "10.1/x", "url": "https://example.org"}]


def _patch_clients(monkeypatch, fail_semantic=False, fail_crossref=False):
    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: _BaseClient())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: _BaseClient())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: _BaseClient(fail=fail_semantic))
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: _BaseClient(fail=fail_crossref))


def test_run_topn_and_outputs(tmp_path, monkeypatch):
    _patch_clients(monkeypatch)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}, {"material": "NaMgN"}]).to_csv(inp, index=False)

    out_dir = tmp_path / 'out'
    db = tmp_path / 'run.sqlite3'
    res = run(top_n=10, input_csv=inp, db_path=db, output_dir=out_dir)

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
    assert df.iloc[0]['Stability'] == 'stable'


def test_rank_column_not_used_as_material():
    row = pd.Series({'Rank': 1, 'Material': 'BaTbPa'})
    assert _extract_material(row) == 'BaTbPa'


def test_missing_material_column_raises_clear_error():
    row = pd.Series({'Rank': 1, 'Band Gap (eV)': 0.2})
    with pytest.raises(ValueError, match='No material/formula column found'):
        _extract_material(row)


def test_failed_sources_exported_and_optional_sources_not_blocking(tmp_path, monkeypatch):
    _patch_clients(monkeypatch, fail_semantic=True, fail_crossref=True)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"Material": "BaTbPa"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'd2.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert 'semantic_scholar:source down' in df.iloc[0]['failed_sources']
    assert 'crossref:source down' in df.iloc[0]['failed_sources']
    assert df.iloc[0]['Automated Status'] != 'incomplete_search_retry_needed'


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
