"""Canary deployment controller."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import requests
import yaml

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


@dataclass
class DeploymentState:
    model_name: str
    prod_version: int
    canary_version: Optional[int] = None
    canary_weight: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "model_name": self.model_name,
            "prod_version": self.prod_version,
            "canary_version": self.canary_version,
            "canary_weight": self.canary_weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "DeploymentState":
        return cls(
            model_name=str(data.get("model_name", "example_model")),
            prod_version=int(data.get("prod_version", 1)),
            canary_version=data.get("canary_version"),
            canary_weight=int(data.get("canary_weight", 0)),
        )


def load_state(path: str | Path) -> DeploymentState:
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        state = DeploymentState(model_name="example_model", prod_version=1)
        save_state(state, path)
        return state
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return DeploymentState.from_dict(data)


def save_state(state: DeploymentState, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(state.to_dict(), f)


def choose_version(state: DeploymentState) -> int:
    if state.canary_version and state.canary_weight > 0:
        roll = random.randint(1, 100)
        if roll <= state.canary_weight:
            return state.canary_version
    return state.prod_version


def start_canary(
    state_path: str | Path,
    model_name: str,
    canary_version: int,
    weight: int,
    prod_version: Optional[int] = None,
) -> DeploymentState:
    state = load_state(state_path)
    state.model_name = model_name
    state.prod_version = prod_version or state.prod_version
    state.canary_version = canary_version
    state.canary_weight = weight
    save_state(state, state_path)
    LOG.info(
        "Started canary",
        extra={
          "model": model_name,
          "prod_version": state.prod_version,
          "canary_version": state.canary_version,
          "weight": weight,
        },
    )
    return state


def promote_canary(state_path: str | Path) -> DeploymentState:
    state = load_state(state_path)
    if not state.canary_version:
        raise ValueError("No canary version to promote")
    state.prod_version = state.canary_version
    state.canary_version = None
    state.canary_weight = 0
    save_state(state, state_path)
    LOG.info("Promoted canary to prod", extra={"prod_version": state.prod_version})
    return state


def rollback_canary(state_path: str | Path) -> DeploymentState:
    state = load_state(state_path)
    state.canary_version = None
    state.canary_weight = 0
    save_state(state, state_path)
    LOG.warning("Rolled back canary", extra={"prod_version": state.prod_version})
    return state


def query_prometheus(prom_url: str, query: str) -> float:
    try:
        resp = requests.get(f"{prom_url}/api/v1/query", params={"query": query}, timeout=5)
        resp.raise_for_status()
        payload = resp.json()
        result = payload["data"]["result"]
        if not result:
            return 0.0
        return float(result[0]["value"][1])
    except Exception as exc:
        LOG.error("Failed to query Prometheus", extra={"error": str(exc), "query": query})
        return 0.0


def evaluate_canary(
    prom_url: str,
    alerts_config: Dict[str, str | float],
    window: str,
) -> Dict[str, float]:
    metrics = {}
    for key, expr in alerts_config.items():
        if not isinstance(expr, str):
            continue
        q = expr.replace("WINDOW", window)
        metrics[key] = query_prometheus(prom_url, q)
    return metrics


def watch_canary(
    prom_url: str,
    alerts_cfg: Dict[str, object],
    state_path: str | Path,
    max_checks: int = 5,
    sleep_seconds: int = 15,
) -> DeploymentState:
    thresholds = {
        "error_rate": alerts_cfg.get("error_rate_threshold", 0.05),
        "latency_p95": alerts_cfg.get("latency_p95_threshold", 0.5),
        "drift": alerts_cfg.get("drift_threshold", 0.3),
    }
    exprs = alerts_cfg.get("promql", {})
    window = str(alerts_cfg.get("evaluation_window", "2m"))
    for _ in range(max_checks):
        stats = evaluate_canary(prom_url, exprs, window)
        LOG.info("Canary metrics", extra=stats)
        if (
            stats.get("error_rate", 0) > thresholds["error_rate"]
            or stats.get("latency_p95", 0) > thresholds["latency_p95"]
            or stats.get("drift", 0) > thresholds["drift"]
        ):
            return rollback_canary(state_path)
        time.sleep(sleep_seconds)
    return promote_canary(state_path)
