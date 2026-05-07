from literature_review.evidence_scoring import contains_any, score_reported_evidence
from literature_review.classification import classify
from literature_review.constants import DFT_KEYWORDS, PROTOTYPE_KEYWORDS


def test_keyword_detection():
    t = "density functional theory on half-Heusler C1b"
    assert contains_any(t, DFT_KEYWORDS)
    assert contains_any(t, PROTOTYPE_KEYWORDS)


def test_scoring_and_classification():
    score = score_reported_evidence({"exact_title": True, "dft": True, "prototype": True})
    assert score >= 80
    label, _ = classify({"reported_evidence_score": score, "unreported_confidence_score": 40}, True, False)
    assert label == "reported_dft"


def test_coverage_gating_to_incomplete():
    label, _ = classify({"reported_evidence_score": 0, "unreported_confidence_score": 140}, False, True)
    assert label == "incomplete_search_retry_needed"
