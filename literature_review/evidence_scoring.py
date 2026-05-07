from .constants import *


def contains_any(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords)


def score_reported_evidence(features: dict) -> int:
    w = REPORTED_EVIDENCE_WEIGHTS
    score = 0
    for k, val in features.items():
        if val and k in w:
            score += w[k]
    return score


def score_unreported_confidence(features: dict) -> int:
    score = UNREPORTED_CONFIDENCE_BASE
    for k, weight in UNREPORTED_CONFIDENCE_WEIGHTS.items():
        if features.get(k):
            score += weight
    return score
