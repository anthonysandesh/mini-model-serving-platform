"""Prediction gateway in front of Triton."""

from __future__ import annotations

import time
from typing import Dict

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from mmsp.deploy.canary import DeploymentState, choose_version, load_state, save_state
from mmsp.deploy.rollback import handle_alert
from mmsp.features.feast_adapter import FeastAdapter
from mmsp.features.lightweight_store import LightweightFeatureStore
from mmsp.monitoring.drift import DriftMonitor
from mmsp.monitoring.metrics import (
    observe_request,
    render_metrics,
    set_version_gauges,
)
from mmsp.serving.client import TritonHTTPClient
from mmsp.serving.schemas import PredictRequest, PredictResponse
from mmsp.utils.config import FeatureStoreConfig, PlatformConfig, load_platform_config
from mmsp.utils.logging import configure_logging, get_logger

configure_logging()
LOG = get_logger(__name__)

app = FastAPI(title="MMSP Gateway", version="0.1.0")
platform_cfg: PlatformConfig = load_platform_config()
state: DeploymentState = load_state(platform_cfg.deployment_state)
set_version_gauges(state.prod_version, state.canary_version)

feature_cfg: FeatureStoreConfig = platform_cfg.feature_store

feature_store = (
    FeastAdapter(repo_path=".") if feature_cfg.mode == "feast" else LightweightFeatureStore(
        feature_cfg.path, feature_cfg.entity_id_column
    )
)

drift_monitor = DriftMonitor(
    baseline_path=platform_cfg.drift.baseline_path,
    window_size=platform_cfg.drift.window_size,
    threshold=platform_cfg.drift.threshold,
    numeric_method=platform_cfg.drift.numeric_method,
    categorical_method=platform_cfg.drift.categorical_method,
    entity_id_column=feature_cfg.entity_id_column,
)

triton_client = TritonHTTPClient(platform_cfg.triton.url)


@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> Dict[str, object]:
    current = load_state(platform_cfg.deployment_state)
    return current.to_dict()


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    current = load_state(platform_cfg.deployment_state)
    version = choose_version(current)
    phase = "canary" if current.canary_version and version == current.canary_version else "prod"
    set_version_gauges(current.prod_version, current.canary_version)

    features = body.features
    if features is None:
        feature_map = feature_store.get_features([body.entity_id])
        features = feature_map.get(str(body.entity_id))
    if not features:
        observe_request(current.model_name, str(version), phase, 0.0, False)
        raise HTTPException(status_code=404, detail="Features not found")

    feature_values = np.array([features[k] for k in sorted(features.keys())], dtype=np.float32)
    start = time.perf_counter()
    success = True
    try:
        outputs = triton_client.predict(current.model_name, version, feature_values)
        prediction = float(outputs[0])
    except Exception as exc:
        success = False
        LOG.error("Prediction failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Prediction failed") from exc
    finally:
        latency = time.perf_counter() - start
        observe_request(current.model_name, str(version), phase, latency, success)
        drift_monitor.record(features)
    return PredictResponse(
        prediction=prediction,
        model_name=current.model_name,
        model_version=version,
        phase=phase,
        latency_ms=latency * 1000.0,
        features=features,
    )


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    data, content_type = render_metrics()
    return PlainTextResponse(content=data.decode(), media_type=content_type)


@app.post("/alerts")
async def alerts(request: Request) -> Dict[str, str]:
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        handle_alert(alert, platform_cfg.deployment_state)
    return {"status": "received", "alerts": len(alerts)}
