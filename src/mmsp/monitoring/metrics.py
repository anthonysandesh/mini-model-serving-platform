"""Prometheus metrics for the platform."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

registry = CollectorRegistry(auto_describe=True)

REQUEST_COUNTER = Counter(
    "gateway_request_total",
    "Total prediction requests",
    ["model", "version", "phase"],
    registry=registry,
)
REQUEST_ERROR_COUNTER = Counter(
    "gateway_request_errors_total",
    "Prediction errors",
    ["model", "version", "phase"],
    registry=registry,
)
LATENCY_HISTOGRAM = Histogram(
    "gateway_latency_seconds",
    "Prediction latency seconds",
    ["model", "version", "phase"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    registry=registry,
)
CURRENT_MODEL_GAUGE = Gauge(
    "gateway_current_model_version",
    "Current deployed model version",
    ["phase"],
    registry=registry,
)
FEATURE_DRIFT = Gauge(
    "feature_drift_score",
    "Drift score per feature",
    ["feature"],
    registry=registry,
)


def observe_request(model: str, version: str, phase: str, latency: float, success: bool) -> None:
    REQUEST_COUNTER.labels(model=model, version=version, phase=phase).inc()
    LATENCY_HISTOGRAM.labels(model=model, version=version, phase=phase).observe(latency)
    if not success:
        REQUEST_ERROR_COUNTER.labels(model=model, version=version, phase=phase).inc()


def set_version_gauges(prod_version: int, canary_version: int | None) -> None:
    CURRENT_MODEL_GAUGE.labels(phase="prod").set(prod_version)
    CURRENT_MODEL_GAUGE.labels(phase="canary").set(canary_version or 0)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST
