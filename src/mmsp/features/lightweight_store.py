"""Lightweight feature store backed by Parquet."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


class LightweightFeatureStore:
    def __init__(self, path: str, entity_id_column: str = "entity_id") -> None:
        self.path = Path(path)
        self.entity_id_column = entity_id_column
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            empty = pd.DataFrame(columns=[self.entity_id_column])
            empty.to_parquet(self.path)

    def load_from_parquet(self, parquet_path: str) -> None:
        df = pd.read_parquet(parquet_path)
        df.to_parquet(self.path)
        LOG.info("Loaded features", extra={"rows": len(df), "dest": str(self.path)})

    def get_features(self, entity_ids: Iterable[str | int]) -> Dict[str, Dict[str, float]]:
        df = pd.read_parquet(self.path)
        subset = df[df[self.entity_id_column].isin(entity_ids)]
        result: Dict[str, Dict[str, float]] = {}
        for _, row in subset.iterrows():
            entity = str(row[self.entity_id_column])
            features = row.drop(labels=[self.entity_id_column]).to_dict()
            result[entity] = {k: float(v) for k, v in features.items()}
        return result

    def upsert(self, records: List[Dict[str, object]]) -> None:
        df = pd.DataFrame(records)
        if self.entity_id_column not in df.columns:
            raise ValueError(f"entity_id_column {self.entity_id_column} missing")
        df.to_parquet(self.path)
        LOG.info("Upserted features", extra={"rows": len(df)})
