"""Lightweight Kubernetes helpers."""

from __future__ import annotations

import subprocess
from typing import List, Optional

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


def run_kubectl(args: List[str]) -> None:
    cmd = ["kubectl"] + args
    LOG.info("Running kubectl", extra={"cmd": " ".join(cmd)})
    subprocess.run(cmd, check=True)


def apply_kustomize(path: str, namespace: Optional[str] = None) -> None:
    args = ["apply", "-k", path]
    if namespace:
        args.extend(["-n", namespace])
    run_kubectl(args)


def delete_kustomize(path: str, namespace: Optional[str] = None) -> None:
    args = ["delete", "-k", path]
    if namespace:
        args.extend(["-n", namespace])
    run_kubectl(args)
