#!/usr/bin/env python
"""Builds a tiny ONNX model and writes Triton repository layout."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper

from mmsp.deploy.triton_repo import build_triton_repository


def build_model(path: Path) -> None:
    X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, 4])
    Y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [None, 1])

    W = np.array([[0.2], [0.1], [0.05], [0.3]], dtype=np.float32)
    B = np.array([0.1], dtype=np.float32)
    w_init = helper.make_tensor("W", TensorProto.FLOAT, dims=W.shape, vals=W.flatten())
    b_init = helper.make_tensor("B", TensorProto.FLOAT, dims=B.shape, vals=B.flatten())

    matmul = helper.make_node("MatMul", ["input", "W"], ["matmul_out"])
    add = helper.make_node("Add", ["matmul_out", "B"], ["output"])

    graph = helper.make_graph(
        nodes=[matmul, add],
        name="linear_model",
        inputs=[X],
        outputs=[Y],
        initializer=[w_init, b_init],
    )
    model = helper.make_model(graph, producer_name="mmsp")
    onnx.save(model, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="examples/model_repository/example_model/1/model.onnx")
    args = parser.parse_args()
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    build_model(dest)
    build_triton_repository(
        artifact_path=str(dest),
        model_name="example_model",
        version=1,
        dest_repo="examples/model_repository",
        inputs=[{"name": "input", "dims": [4], "dtype": "TYPE_FP32"}],
        outputs=[{"name": "output", "dims": [1], "dtype": "TYPE_FP32"}],
    )
    print(f"Wrote model to {dest}")


if __name__ == "__main__":
    main()
