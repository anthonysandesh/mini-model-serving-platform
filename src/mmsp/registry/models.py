"""Registry models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelVersion(BaseModel):
    name: str
    version: int
    framework: str
    artifact_path: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    stage: Optional[str] = None

    @classmethod
    def create(
        cls,
        name: str,
        version: int,
        framework: str,
        artifact_path: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> "ModelVersion":
        meta = metadata or {}
        if "created_at" not in meta:
            meta["created_at"] = datetime.now(timezone.utc).isoformat()
        return cls(
            name=name,
            version=version,
            framework=framework,
            artifact_path=artifact_path,
            metadata=meta,
        )


class RegistryState(BaseModel):
    models: Dict[str, List[ModelVersion]] = Field(default_factory=dict)
    stages: Dict[str, Dict[str, int]] = Field(default_factory=dict)  # name -> stage -> version
