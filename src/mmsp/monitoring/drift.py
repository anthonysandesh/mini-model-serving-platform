"""Data drift detection utilities."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List

import numpy as np
import pandas as pd
from scipy import stats

from mmsp.monitoring.metrics import FEATURE_DRIFT
from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


def ks_statistic(baseline: List[float], observed: List[float]) -> float:
    if not baseline or not observed:
        return 0.0
    baseline_arr = np.array(baseline, dtype=float)
    observed_arr = np.array(observed, dtype=float)
    return float(stats.ks_2samp(baseline_arr, observed_arr).statistic)


def psi(expected: List[float], actual: List[float], bins: int = 10) -> float:
    if not expected or not actual:
        return 0.0
    expected_arr = np.array(expected, dtype=float)
    actual_arr = np.array(actual, dtype=float)
    quantiles = np.linspace(0, 100, bins + 1)
    breakpoints = np.unique(np.percentile(expected_arr, quantiles))
    if breakpoints.size < 2:
        epsilon = 1e-3
        center = breakpoints[0]
        breakpoints = np.array([center - epsilon, center + epsilon])
    expected_counts, _ = np.histogram(expected_arr, bins=breakpoints)
    actual_counts, _ = np.histogram(actual_arr, bins=breakpoints)
    expected_perc = expected_counts / max(expected_counts.sum(), 1)
    actual_perc = actual_counts / max(actual_counts.sum(), 1)
    psi_values = []
    for e, a in zip(expected_perc, actual_perc):
        e = max(e, 1e-6)
        a = max(a, 1e-6)
        psi_values.append((a - e) * np.log(a / e))
    return float(np.sum(psi_values))


class DriftMonitor:
    """Maintains drift stats vs. baseline."""

    def __init__(
        self,
        baseline_path: str,
        window_size: int = 200,
        threshold: float = 0.3,
        numeric_method: str = "ks",
        categorical_method: str = "psi",
        entity_id_column: str = "entity_id",
    ) -> None:
        self.baseline = pd.read_parquet(baseline_path)
        if entity_id_column in self.baseline.columns:
            self.baseline = self.baseline.drop(columns=[entity_id_column])
        self.window_size = window_size
        self.threshold = threshold
        self.numeric_method = numeric_method
        self.categorical_method = categorical_method
        self.recent: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=window_size))

    def record(self, features: Dict[str, float]) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for key, value in features.items():
            if key not in self.baseline.columns:
                continue
            self.recent[key].append(float(value))
            baseline_series = self.baseline[key].dropna().tolist()
            recent_list = list(self.recent[key])
            if pd.api.types.is_numeric_dtype(self.baseline[key]):
                score = ks_statistic(baseline_series, recent_list) if self.numeric_method == "ks" else psi(
                    baseline_series, recent_list
                )
            else:
                score = psi(baseline_series, recent_list) if self.categorical_method == "psi" else ks_statistic(
                    baseline_series, recent_list
                )
            scores[key] = score
            FEATURE_DRIFT.labels(feature=key).set(score)
            if score > self.threshold:
                LOG.warning("Drift detected", extra={"feature": key, "score": score})
        return scores
