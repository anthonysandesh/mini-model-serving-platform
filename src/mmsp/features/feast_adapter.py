"""Feast adapter (optional)."""

from __future__ import annotations

from typing import Dict, Iterable

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


class FeastAdapter:
    def __init__(self, repo_path: str) -> None:
        try:
            from feast import FeatureStore  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Feast not installed. Install feast to enable feast mode."
            ) from exc
        self.store = FeatureStore(repo_path=repo_path)

    def get_features(self, entity_name: str, entity_ids: Iterable[str | int]) -> Dict[str, Dict[str, float]]:
        features = self.store.get_online_features(
            features=[f"{entity_name}:*"],
            entity_rows=[{"entity_id": eid} for eid in entity_ids],
        ).to_dict()
        result: Dict[str, Dict[str, float]] = {}
        for idx, eid in enumerate(entity_ids):
            feature_map = {k: v[idx] for k, v in features.items()}
            result[str(eid)] = {k: float(v) for k, v in feature_map.items()}
        return result
