import pytest

from literature_review.composition_equivalence import canonical_element_set, formula_permutations
from literature_review.pipeline import run
from literature_review.strategic_classifier import load_prior_material_evidence


def test_canonical_equivalence():
    assert canonical_element_set("ZrFeTe") == canonical_element_set("FeZrTe")


def test_formula_permutations_include_variant():
    assert "FeZrTe" in formula_permutations("ZrFeTe")


def test_known_reported_compositions_blocked():
    for mat in ["ZrFeTe", "ZrTeRu", "ScCoTe", "TiFeTe"]:
        prior = load_prior_material_evidence(None, mat)
        assert prior["prior_conflict_flag"] is True
        assert prior["known_reported_composition_flag"] is True
        assert prior["prior_best_url"].startswith("http")


def test_pipeline_search_mode_validation():
    with pytest.raises(ValueError):
        run(top_n=1, search_mode="bad-mode")
