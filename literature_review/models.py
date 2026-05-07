from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MaterialRecord:
    material: str
    band_gap_ev: float = 0.0
    stability: str = ""
    oqmd_entry_id: Optional[int] = None
    final_rank: Optional[int] = None


@dataclass
class Coverage:
    google_scholar_checked: bool = False
    openalex_checked: bool = False
    semantic_scholar_checked: bool = False
    crossref_checked: bool = False
    permutation_checked: bool = False
    citation_neighbor_checked: bool = False
    full_text_checked: bool = False
    source_error: bool = False


@dataclass
class Hit:
    source: str
    title: str = ""
    snippet: str = ""
    abstract: str = ""
    doi: str = ""
    url: str = ""


@dataclass
class ClassificationResult:
    label: str
    reason: str
    reported_evidence_score: int
    unreported_confidence_score: int
    best_matching_paper: str = ""
    best_weak_match: str = ""
    doi: str = ""
    url: str = ""
    reviewer_notes: str = ""
    manual_label: str = ""
    coverage: Coverage = field(default_factory=Coverage)
