"""Lightweight filesystem-backed model registry."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from mmsp.registry.models import ModelVersion, RegistryState
from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


class RegistryStore:
    """Filesystem model registry."""

    def __init__(self, path: str | Path = "artifacts/registry/registry.json") -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_state(RegistryState())

    def _read_state(self) -> RegistryState:
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RegistryState(**data)

    def _write_state(self, state: RegistryState) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))
        tmp.replace(self.path)

    def _hash_artifact(self, artifact_path: str | Path) -> str:
        path = Path(artifact_path)
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def register(
        self,
        name: str,
        framework: str,
        artifact_path: str,
        version: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ModelVersion:
        with self._lock:
            state = self._read_state()
            versions = state.models.get(name, [])
            next_version = version or (max(v.version for v in versions) + 1 if versions else 1)
            meta = metadata or {}
            if "hash" not in meta:
                meta["hash"] = self._hash_artifact(artifact_path)
            mv = ModelVersion.create(
                name=name,
                version=next_version,
                framework=framework,
                artifact_path=artifact_path,
                metadata=meta,
            )
            versions.append(mv)
            state.models[name] = versions
            self._write_state(state)
            LOG.info("Registered model", extra={"model": name, "version": next_version})
            return mv

    def list_models(self, name: Optional[str] = None) -> List[ModelVersion]:
        state = self._read_state()
        if name:
            return state.models.get(name, [])
        models: List[ModelVersion] = []
        for versions in state.models.values():
            models.extend(versions)
        return models

    def promote(self, name: str, version: int, stage: str) -> None:
        stage = stage.lower()
        with self._lock:
            state = self._read_state()
            versions = state.models.get(name)
            if not versions:
                raise ValueError(f"Model {name} not found")
            if not any(v.version == version for v in versions):
                raise ValueError(f"Version {version} not found for model {name}")
            state.stages.setdefault(name, {})[stage] = version
            updated: List[ModelVersion] = []
            for mv in versions:
                if mv.version == version:
                    mv = mv.model_copy(update={"stage": stage})
                elif mv.stage == stage:
                    mv = mv.model_copy(update={"stage": None})
                updated.append(mv)
            state.models[name] = updated
            self._write_state(state)
            LOG.info("Promoted model", extra={"model": name, "version": version, "stage": stage})

    def current_stage(self, name: str, stage: str) -> Optional[int]:
        state = self._read_state()
        return state.stages.get(name, {}).get(stage)
