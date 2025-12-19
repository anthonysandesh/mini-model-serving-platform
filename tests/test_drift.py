from pathlib import Path

import pandas as pd

from mmsp.monitoring.drift import DriftMonitor, ks_statistic, psi


def test_ks_and_psi() -> None:
    base = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    observed = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    assert ks_statistic(base, observed) > 0.3
    assert psi(base, observed) > 0.0


def test_drift_monitor(tmp_path: Path) -> None:
    df = pd.DataFrame({"entity_id": [1, 2, 3], "f1": [0.1, 0.2, 0.3]})
    baseline = tmp_path / "baseline.parquet"
    df.to_parquet(baseline)
    monitor = DriftMonitor(str(baseline), window_size=3, threshold=0.05)
    score = monitor.record({"f1": 0.9})["f1"]
    assert score > 0.05
