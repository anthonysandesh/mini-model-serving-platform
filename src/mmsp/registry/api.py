"""FastAPI service exposing registry operations."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mmsp.registry.store import RegistryStore
from mmsp.registry.models import ModelVersion
from mmsp.utils.config import load_platform_config
from mmsp.utils.logging import configure_logging

configure_logging()
platform_cfg = load_platform_config()
registry_path = Path(platform_cfg.artifact_root) / "registry" / "registry.json"
store = RegistryStore(registry_path)

app = FastAPI(title="MMSP Registry", version="0.1.0")


class RegisterRequest(BaseModel):
    name: str
    framework: str
    artifact_path: str
    version: Optional[int] = None
    metadata: Optional[dict] = None


class PromoteRequest(BaseModel):
    stage: str


@app.get("/models", response_model=List[ModelVersion])
def list_models(name: Optional[str] = None) -> List[ModelVersion]:
    return store.list_models(name=name)


@app.post("/models", response_model=ModelVersion)
def register_model(body: RegisterRequest) -> ModelVersion:
    path = Path(body.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail="artifact_path does not exist")
    return store.register(
        name=body.name,
        framework=body.framework,
        artifact_path=body.artifact_path,
        version=body.version,
        metadata=body.metadata,
    )


@app.post("/models/{name}/{version}/promote")
def promote_model(name: str, version: int, body: PromoteRequest) -> dict:
    try:
        store.promote(name, version, body.stage)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "ok", "stage": body.stage}
