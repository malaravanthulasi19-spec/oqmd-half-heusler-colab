from __future__ import annotations

POSITIVE_CONTROLS = [
    "NiTiSn", "TiNiSn", "ZrNiSn", "HfNiSn", "CoTiSb",
    "FeVSb", "NbFeSb", "ZrCoSb", "ScNiSb", "YNiSb",
]

NEGATIVE_CONTROLS = [
    {"material": "CaNdU", "noise": ["CANDU"]},
    {"material": "NaNdU", "noise": ["Nandu"]},
    {"material": "CaNdPa", "noise": ["GDPR", "data protection authority"]},
    {"material": "BaTbPa", "noise": ["Lyapunov", "transient stability"]},
    {"material": "NaUTa", "noise": ["Nauta"]},
    {"material": "NdYU", "noise": ["Nd:YAG", "YU"]},
]

PASS_LABELS = {"PASS_DFT", "PASS_FORMULA_ONLY"}

