from pathlib import Path
import pandas as pd

from literature_review.pipeline import run


class FakeClient:
    def __init__(self, payload=None, fail=False):
        self.calls = 0
        self.payload = payload if payload is not None else [{"title": "BaTbPa density functional theory half-Heusler", "snippet": "band gap", "doi": "10.1/x", "link": "u"}]
        self.fail = fail

    def search(self, query):
        self.calls += 1
        if self.fail:
            raise RuntimeError("source failure")
        return self.payload


def _input_csv(tmp_path: Path):
    p = tmp_path / "in.csv"
    pd.DataFrame([
        {"Material": "BaTbPa", "Band Gap (eV)": 1.2, "Stability": "stable", "OQMD Entry ID": 1, "Final Rank": 1},
        {"Material": "BaTbSb", "Band Gap (eV)": 1.1, "Stability": "stable", "OQMD Entry ID": 2, "Final Rank": 2},
    ]).to_csv(p, index=False)
    return p


def test_run_processes_and_exports_and_cache(tmp_path):
    inp = _input_csv(tmp_path)
    db = tmp_path / "db.sqlite3"
    out = tmp_path / "out"
    c = {"google_scholar": FakeClient(), "openalex": FakeClient(), "semantic_scholar": FakeClient(), "crossref": FakeClient()}
    res = run(top_n=1, input_csv=inp, db_path=db, output_dir=out, clients=c)
    assert res["materials_processed"] == 1
    assert (out / "02_ranked_not_found_after_protocol.csv").exists()
    import sqlite3
    conn = sqlite3.connect(db)
    first_completed = conn.execute("SELECT COUNT(*) FROM completed_queries").fetchone()[0]
    run(top_n=1, input_csv=inp, db_path=db, output_dir=out, clients=c)
    second_completed = conn.execute("SELECT COUNT(*) FROM completed_queries").fetchone()[0]
    assert second_completed >= first_completed
    first_hits = conn.execute("SELECT COUNT(*) FROM hits").fetchone()[0]
    run(top_n=1, input_csv=inp, db_path=db, output_dir=out, clients=c)
    second_hits = conn.execute("SELECT COUNT(*) FROM hits").fetchone()[0]
    assert second_hits == first_hits


def test_incomplete_failure_goes_to_incomplete_label(tmp_path):
    inp = _input_csv(tmp_path)
    db = tmp_path / "db.sqlite3"
    out = tmp_path / "out"
    c = {"google_scholar": FakeClient(fail=True), "openalex": FakeClient(), "semantic_scholar": FakeClient(), "crossref": FakeClient()}
    run(top_n=1, input_csv=inp, db_path=db, output_dir=out, clients=c)
    df = pd.read_csv(out / "05_all_hits_audit.csv")
    assert (df["Automated Status"] == "incomplete_search_retry_needed").all()


def test_not_found_requires_complete_coverage(tmp_path):
    inp = _input_csv(tmp_path)
    db = tmp_path / "db.sqlite3"
    out = tmp_path / "out"
    payload = [{"title": "Unrelated paper", "snippet": "random", "link": "u"}]
    c = {"google_scholar": FakeClient(payload=payload), "openalex": FakeClient(fail=True), "semantic_scholar": FakeClient(payload=payload), "crossref": FakeClient(payload=payload)}
    run(top_n=1, input_csv=inp, db_path=db, output_dir=out, clients=c)
    df = pd.read_csv(out / "05_all_hits_audit.csv")
    assert df.iloc[0]["Automated Status"] != "not_found_after_protocol"
    assert df.iloc[0]["Automated Status"] == "incomplete_search_retry_needed"
