from __future__ import annotations

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    """
    Population Stability Index for numeric columns.
    """
    expected = expected.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    actual = actual.astype(float).replace([np.inf, -np.inf], np.nan).dropna()

    if len(expected) < 10 or len(actual) < 10:
        return 0.0

    # same bin edges based on expected quantiles
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(expected, quantiles))
    if len(edges) < 3:  # not enough variability
        return 0.0

    exp_counts, _ = np.histogram(expected, bins=edges)
    act_counts, _ = np.histogram(actual, bins=edges)

    exp_perc = exp_counts / max(exp_counts.sum(), 1)
    act_perc = act_counts / max(act_counts.sum(), 1)

    # avoid zero
    eps = 1e-6
    exp_perc = np.clip(exp_perc, eps, None)
    act_perc = np.clip(act_perc, eps, None)

    return float(np.sum((act_perc - exp_perc) * np.log(act_perc / exp_perc)))


def cat_l1(expected: pd.Series, actual: pd.Series, top_k: int = 50) -> float:
    """
    L1 distance between category distributions (0..2).
    """
    expected = expected.fillna("").astype(str)
    actual = actual.fillna("").astype(str)

    exp = expected.value_counts(normalize=True)
    act = actual.value_counts(normalize=True)

    # union of top categories
    cats = set(exp.head(top_k).index).union(set(act.head(top_k).index))
    if not cats:
        return 0.0

    dist = 0.0
    for c in cats:
        dist += abs(float(act.get(c, 0.0)) - float(exp.get(c, 0.0)))
    return float(dist)


def compute_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    num_cols: List[str],
    cat_cols: List[str],
    psi_threshold: float = 0.2,
    cat_threshold: float = 0.2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    details: Dict[str, Any] = {"numeric": {}, "categorical": {}}

    drifted = []

    for c in num_cols:
        score = psi(reference[c], current[c])
        details["numeric"][c] = {"psi": score, "drift": score >= psi_threshold}
        if score >= psi_threshold:
            drifted.append(c)

    for c in cat_cols:
        score = cat_l1(reference[c], current[c])
        details["categorical"][c] = {"l1": score, "drift": score >= cat_threshold}
        if score >= cat_threshold:
            drifted.append(c)

    summary = {
        "drift_detected": len(drifted) > 0,
        "drifted_features": drifted,
        "psi_threshold": psi_threshold,
        "cat_threshold": cat_threshold,
        "n_reference": int(len(reference)),
        "n_current": int(len(current)),
    }
    return summary, details
