#!/usr/bin/env python
"""Simple load generator for the gateway."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple

import requests


def load_requests(path: Path) -> List[Dict[str, object]]:
    payloads: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            payloads.append(json.loads(line))
    return payloads


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    idx = int(0.95 * len(values)) - 1
    idx = max(idx, 0)
    return sorted(values)[idx]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://localhost:8080")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--rps", type=int, default=10)
    parser.add_argument("--requests-file", default="examples/sample_requests.jsonl")
    args = parser.parse_args()

    payloads = load_requests(Path(args.requests_file))
    latencies: List[float] = []
    errors = 0
    total = 0
    start = time.time()
    idx = 0
    while time.time() - start < args.duration:
        payload = payloads[idx % len(payloads)]
        idx += 1
        t0 = time.perf_counter()
        try:
            resp = requests.post(f"{args.gateway}/predict", json=payload, timeout=5)
            if resp.status_code != 200:
                errors += 1
            else:
                latencies.append(time.perf_counter() - t0)
        except Exception:
            errors += 1
        total += 1
        sleep_time = max(0, (1 / args.rps) - (time.perf_counter() - t0))
        time.sleep(sleep_time)

    print(f"Sent {total} requests, errors={errors}")
    if latencies:
        print(f"Latency p50: {median(latencies)*1000:.2f} ms, p95: {p95(latencies)*1000:.2f} ms")
    if total:
        print(f"Error rate: {errors/total*100:.2f}%")


if __name__ == "__main__":
    main()
