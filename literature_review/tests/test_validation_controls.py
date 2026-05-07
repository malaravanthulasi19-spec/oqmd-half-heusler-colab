import pandas as pd

from literature_review.validation_controls import run_validation_controls, POSITIVE_CONTROL_FORMULAS


class _Client:
    def search(self, query, **kwargs):
        return [{
            "title": f"DFT electronic structure study of NiTiSn and half-Heusler family {query}",
            "snippet": "first-principles calculations",
            "abstract": "NiTiSn shows promising electronic structure in density functional theory",
            "doi": "10.1000/example",
            "url": "https://example.org/paper",
        }]


def test_validation_controls_output_structure(tmp_path, monkeypatch):
    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: _Client())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: _Client())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: _Client())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: _Client())

    out_dir = tmp_path / 'out'
    db = tmp_path / 'run.sqlite3'
    export_path = tmp_path / 'validation.csv'

    validation = run_validation_controls(db_path=db, output_dir=out_dir, export_path=export_path)

    expected_cols = {
        'Material',
        'Expected Label',
        'Automated Status',
        'exact_formula_hit_count',
        'dft_formula_hit_count',
        'formula_level_evidence_found',
        'best_paper_title',
        'best_doi',
        'best_url',
        'pass_fail',
        'reason',
    }
    assert expected_cols.issubset(set(validation.columns))
    assert len(validation) == len(POSITIVE_CONTROL_FORMULAS)
    assert export_path.exists()


def test_validation_fails_not_found_controls(tmp_path, monkeypatch):
    class WeakClient:
        def search(self, query, **kwargs):
            return [{"title": "General materials overview", "snippet": "broad survey", "abstract": "no compound-specific evidence", "doi": "", "url": ""}]

    monkeypatch.setattr('literature_review.pipeline.GoogleScholarClient', lambda: WeakClient())
    monkeypatch.setattr('literature_review.pipeline.OpenAlexClient', lambda: WeakClient())
    monkeypatch.setattr('literature_review.pipeline.SemanticScholarClient', lambda: WeakClient())
    monkeypatch.setattr('literature_review.pipeline.CrossrefClient', lambda: WeakClient())

    validation = run_validation_controls(db_path=tmp_path / 'db.sqlite3', output_dir=tmp_path / 'out2', export_path=tmp_path / 'v2.csv')
    assert (validation['Automated Status'] == 'not_found_after_protocol').any()
    failed = validation[validation['Automated Status'] == 'not_found_after_protocol']
    assert (failed['pass_fail'] == 'FAIL').all()
