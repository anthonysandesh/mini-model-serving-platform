"""Typed configuration loading for the platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field

from mmsp.utils.io import atomic_write_json
from mmsp.utils.time import current_run_id


class TritonConfig(BaseModel):
    url: str
    grpc_url: str


class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    canary_default_weight: int = 10


class FeatureStoreConfig(BaseModel):
    mode: str = "lightweight"
    path: str
    entity_id_column: str = "entity_id"


class DriftConfig(BaseModel):
    baseline_path: str
    window_size: int = 200
    threshold: float = 0.3
    numeric_method: str = "ks"
    categorical_method: str = "psi"


class PlatformConfig(BaseModel):
    name: str = "mini-model-serving-platform"
    artifact_root: str = "artifacts"
    model_repository: str = "examples/model_repository"
    deployment_state: str = "artifacts/deployments/state.yaml"
    prometheus_url: str = "http://localhost:9090"
    triton: TritonConfig
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    feature_store: FeatureStoreConfig
    drift: DriftConfig
    alerts_config: Optional[str] = None
    drift_config: Optional[str] = None

    def artifact_path(self, *parts: str) -> Path:
        root = Path(self.artifact_root)
        return root.joinpath(*parts)


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_platform_config(path: Optional[str] = None) -> PlatformConfig:
    config_path = path or os.environ.get("PLATFORM_CONFIG") or "configs/platform.yaml"
    data = load_yaml(config_path)
    if "platform" not in data:
        raise ValueError(f"Invalid config file, expected 'platform' root at {config_path}")
    platform_cfg = PlatformConfig(**data["platform"])
    resolved_dir = platform_cfg.artifact_path("runs", current_run_id())
    resolved_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(resolved_dir / "resolved_config.json", platform_cfg.model_dump())
    return platform_cfg


def save_config(config: BaseModel, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(), f)
