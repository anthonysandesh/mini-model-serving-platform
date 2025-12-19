"""Client for Triton Inference Server."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import requests

from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


class TritonHTTPClient:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def predict(self, model_name: str, model_version: int, array: np.ndarray) -> List[float]:
        if array.ndim == 1:
            array = np.expand_dims(array, axis=0)
        payload: Dict[str, Any] = {
            "inputs": [
                {
                    "name": "input",
                    "shape": list(array.shape),
                    "datatype": "FP32",
                    "data": array.astype(float).reshape(-1).tolist(),
                }
            ],
            "outputs": [{"name": "output"}],
        }
        endpoint = f"{self.url}/v2/models/{model_name}/versions/{model_version}/infer"
        resp = requests.post(endpoint, json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        outputs = data.get("outputs", [])
        if not outputs:
            raise RuntimeError("No outputs from Triton response")
        return outputs[0]["data"]
