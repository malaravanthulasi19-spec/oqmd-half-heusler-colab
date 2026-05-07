from literature_review.formula_variants import build_variants, exact_formula_match, loose_element_system_match, permutation_formula_match


def test_formula_parsing_and_variants():
    v = build_variants("BaTbPa")
    assert v.compact == "BaTbPa"
    assert v.spaced == "Ba Tb Pa"
    assert v.hyphenated == "Ba-Tb-Pa"
    assert "TbBaPa" in v.permutations


def test_exact_vs_element_system_matching():
    v = build_variants("BaTbPa")
    assert exact_formula_match("We studied BaTbPa by DFT.", v)
    assert not exact_formula_match("Ba and Tb and Pa system", v)
    assert loose_element_system_match("Ba and Tb and Pa system", v)
    assert permutation_formula_match("PaTbBa has a gap", v)


def test_false_word_collisions_not_formula_matches():
    v = build_variants("CaNdU")
    assert not exact_formula_match("CANDU reactor analysis", v)
    assert not exact_formula_match("candu reactor analysis", v)
    v2 = build_variants("NaNdU")
    assert not exact_formula_match("Nandu River microplastic study", v2)
