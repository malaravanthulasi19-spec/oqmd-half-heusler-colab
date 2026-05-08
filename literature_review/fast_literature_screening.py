from __future__ import annotations


def _f(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_local_material_gate(row: dict) -> dict:
    st = _f(row.get("Stability", 999), 999)
    bg = _f(row.get("Band Gap (eV)", -1), -1)
    tier = str(row.get("practicality_tier", "") or "")
    known = bool(row.get("known_reported_composition_flag"))
    conflict = bool(row.get("prior_conflict_flag"))

    if known or conflict:
        return {"local_gate_status": "SKIP_KNOWN_REPORTED", "local_gate_reason": "Known reported composition-equivalent literature found.", "should_search_literature": False, "should_run_deep_search": False}
    if st > 0.30:
        return {"local_gate_status": "LOW_PRIORITY", "local_gate_reason": "Stability > 0.30", "should_search_literature": False, "should_run_deep_search": False}
    if bg > 5.0:
        return {"local_gate_status": "LOW_PRIORITY", "local_gate_reason": "Band Gap (eV) > 5.0", "should_search_literature": False, "should_run_deep_search": False}
    if tier in {"HIGHLY_IMPRACTICAL", "RADIOACTIVE_REVIEW", "TOXICITY_REVIEW"}:
        return {"local_gate_status": "LOW_PRIORITY", "local_gate_reason": f"practicality_tier={tier}", "should_search_literature": False, "should_run_deep_search": False}
    if st <= 0.30 and 0.1 <= bg <= 3.0:
        return {"local_gate_status": "STRONG", "local_gate_reason": "Strong local gate", "should_search_literature": True, "should_run_deep_search": True}
    return {"local_gate_status": "FAST_ONLY", "local_gate_reason": "Only run compact exact/permutation search", "should_search_literature": True, "should_run_deep_search": False}
