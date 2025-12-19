#!/usr/bin/env python
"""Load sample features into the lightweight feature store."""

from __future__ import annotations

from pathlib import Path

from mmsp.features.lightweight_store import LightweightFeatureStore
from mmsp.utils.config import load_platform_config


def main() -> None:
    cfg = load_platform_config()
    src = Path("examples/feature_data.parquet")
    if not src.exists():
        raise SystemExit(f"Missing sample features at {src}")
    store = LightweightFeatureStore(cfg.feature_store.path, cfg.feature_store.entity_id_column)
    store.load_from_parquet(str(src))
    print(f"Loaded features from {src} into {cfg.feature_store.path}")


if __name__ == "__main__":
    main()
