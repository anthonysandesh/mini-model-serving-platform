"""Feature retrieval API."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query

from mmsp.features.feast_adapter import FeastAdapter
from mmsp.features.lightweight_store import LightweightFeatureStore
from mmsp.utils.config import FeatureStoreConfig, load_platform_config
from mmsp.utils.logging import configure_logging, get_logger

configure_logging()
LOG = get_logger(__name__)

app = FastAPI(title="Feature API", version="0.1.0")
platform_cfg = load_platform_config()
feature_cfg: FeatureStoreConfig = platform_cfg.feature_store

store = (
    FeastAdapter(repo_path=".") if feature_cfg.mode == "feast" else LightweightFeatureStore(
        feature_cfg.path, feature_cfg.entity_id_column
    )
)


@app.get("/features")
def get_features(entity_id: Optional[str] = None, entity_ids: Optional[List[str]] = Query(None)) -> Dict[str, Dict]:
    ids: List[str] = []
    if entity_id:
        ids.append(entity_id)
    if entity_ids:
        ids.extend(entity_ids)
    if not ids:
        raise HTTPException(status_code=400, detail="No entity_id provided")
    result = store.get_features(ids)
    if not result:
        raise HTTPException(status_code=404, detail="No features found")
    return {"features": result}
