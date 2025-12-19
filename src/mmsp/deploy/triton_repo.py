"""Helpers to build Triton model repository layouts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


def generate_config_pbtxt(
    model_name: str,
    inputs: List[dict],
    outputs: List[dict],
    max_batch: int = 0,
) -> str:
    lines = [f'name: "{model_name}"', 'backend: "onnxruntime"']
    lines.append(f"max_batch_size: {max_batch}")
    for inp in inputs:
        dims = ", ".join(str(d) for d in inp["dims"])
        lines.append("input {")
        lines.append(f'  name: "{inp["name"]}"')
        lines.append(f'  data_type: {inp["dtype"]}')
        lines.append(f"  dims: [ {dims} ]")
        lines.append("}")
    for out in outputs:
        dims = ", ".join(str(d) for d in out["dims"])
        lines.append("output {")
        lines.append(f'  name: "{out["name"]}"')
        lines.append(f'  data_type: {out["dtype"]}')
        lines.append(f"  dims: [ {dims} ]")
        lines.append("}")
    lines.append('instance_group [ { kind: KIND_CPU } ]')
    return "\n".join(lines) + "\n"


def build_triton_repository(
    artifact_path: str,
    model_name: str,
    version: int,
    dest_repo: str,
    inputs: List[dict],
    outputs: List[dict],
) -> Path:
    repo_path = Path(dest_repo)
    model_version_dir = repo_path / model_name / str(version)
    model_version_dir.mkdir(parents=True, exist_ok=True)
    dest_model = model_version_dir / "model.onnx"
    src_path = Path(artifact_path)
    if src_path.resolve() != dest_model.resolve():
        shutil.copyfile(src_path, dest_model)
    config_text = generate_config_pbtxt(model_name, inputs, outputs)
    config_path = repo_path / model_name / "config.pbtxt"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_text)
    LOG.info(
        "Built Triton repository",
        extra={"model": model_name, "version": version, "path": str(model_version_dir)},
    )
    return model_version_dir
