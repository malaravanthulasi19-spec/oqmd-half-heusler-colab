import pandas as pd
from literature_review.pipeline import run


class _BaseClient:
    def __init__(self, fail=False):
        self.fail = fail

    def search(self, query, **kwargs):
        if self.fail:
            raise RuntimeError('source down')
        return [{"title": f"BaTbPa DFT half-Heusler {query}", "snippet": "C1b first principles", "doi": "10.1/x"}]


def _patch_clients(monkeypatch, fail_semantic=False):
    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: _BaseClient())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: _BaseClient())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: _BaseClient(fail=fail_semantic))
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: _BaseClient())


def test_run_topn_and_outputs(tmp_path, monkeypatch):
    _patch_clients(monkeypatch)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}, {"material": "NaMgN"}]).to_csv(inp, index=False)

    out_dir = tmp_path / 'out'
    db = tmp_path / 'run.sqlite3'
    res = run(top_n=10, input_csv=inp, db_path=db, output_dir=out_dir)

    assert res['materials_loaded'] == 2
    assert (out_dir / '05_all_hits_audit.csv').exists()


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


def test_incomplete_vs_not_found_logic(tmp_path, monkeypatch):
    _patch_clients(monkeypatch, fail_semantic=True)
    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}]).to_csv(inp, index=False)
    db = tmp_path / 'run.sqlite3'
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=db, output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert (df['Automated Status'] == 'incomplete_search_retry_needed').all()

def test_not_found_only_when_coverage_complete(tmp_path, monkeypatch):
    class Empty(_BaseClient):
        def search(self, query, **kwargs):
            return []

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: Empty())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: Empty())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: Empty())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: Empty())

    inp = tmp_path / 'input.csv'
    pd.DataFrame([{"material": "BaTbPa"}]).to_csv(inp, index=False)
    out_dir = tmp_path / 'out'
    run(top_n=10, input_csv=inp, db_path=tmp_path / 'd.sqlite3', output_dir=out_dir)
    df = pd.read_csv(out_dir / '05_all_hits_audit.csv')
    assert df.iloc[0]['Automated Status'] == 'not_found_after_protocol'
