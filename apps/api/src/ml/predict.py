from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd


def sanitize_features(features: Dict[str, Any], num_cols: List[str], cat_cols: List[str]) -> Dict[str, Any]:
    """
    - Only keeps columns in num_cols + cat_cols
    - Casts numeric columns to float
    - Fills missing columns with defaults (0 for numeric, "" for categorical)
    """
    allowed = set(num_cols) | set(cat_cols)

    clean: Dict[str, Any] = {}

    # keep only allowed keys
    for k, v in features.items():
        if k in allowed:
            clean[k] = v

    # fill missing
    for c in num_cols:
        if c not in clean or clean[c] is None or clean[c] == "":
            clean[c] = 0.0
        # cast to float safely
        try:
            clean[c] = float(clean[c])
        except Exception:
            clean[c] = 0.0

    for c in cat_cols:
        if c not in clean or clean[c] is None:
            clean[c] = ""
        else:
            clean[c] = str(clean[c])

    return clean


def to_dataframe(features: Dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([features])
