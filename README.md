# Mini Model Serving Platform (MMSP)

Internal ML serving platform mini-clone with registry, Triton serving, feature retrieval, canary deploy + rollback, monitoring, alerting, GitOps, and a one-command demo.

```
                        +--------------------+
                        |   ArgoCD (GitOps)  |
                        +---------+----------+
                                  |
                                  v
    +----------------------+   +---+---------+     +-----------------+
    |    Clients / Load    |-->| Gateway     |---->|  Triton Server  |
    +----------------------+   +---+---------+     +-----------------+
                                 |   ^ metrics            ^
                    features     |   | alerts             |
                                 v   |                    |
                         +-------+---+--------+           |
                         | Feature API/Store  |           |
                         +--------------------+           |
                                 ^                        |
                                 |                        |
                        +--------+---------+     +--------+---------+
                        |   Prometheus     |<----+  Alertmanager    |
                        +--------+---------+     +------------------+
                                 |
                                 v
                              Grafana
```

## Quickstart (Local Docker Compose)
1. Install deps + CLI: `pip install -r requirements.txt -c constraints.txt && pip install -e .` (or set `PYTHONPATH=src` to run scripts directly)
2. Build sample model + repo and data: `make generate-model`
3. Start stack: `make up`
4. Load features: `make load-features`
5. Send traffic: `python scripts/send_load.py --duration 10 --gateway http://localhost:8080`
6. Grafana: http://localhost:3000 (admin/admin). Prometheus: http://localhost:9090. Gateway: http://localhost:8080/predict.
7. Stop: `make down`

Or run everything: `make demo` (build model, start compose, load features, fire load).

## Quickstart (Kubernetes + ArgoCD GitOps)
1. Build/push app image `mmsp-app` with `docker build -t mmsp-app:dev .`
2. Create namespace + apply Kustomize overlay: `kubectl apply -k k8s/overlays/dev`
3. Port-forward for local access: `kubectl port-forward svc/gateway -n mmsp 8080:8000`
4. ArgoCD: `kubectl apply -f k8s/apps/argocd-application.yaml` (update repo URL if needed) then sync from ArgoCD UI/CLI.
5. Grafana: `kubectl port-forward svc/grafana -n mmsp 3000:3000`

## Canary + Rollback Demo
1. Register and package model: `mmsp register --model-path examples/model_repository/example_model/1/model.onnx --name example_model`
2. Start canary at 10%: `mmsp deploy --name example_model --version 1 --canary 10`
3. Generate load: `mmsp loadgen --rps 20 --duration 60 --gateway http://localhost:8080`
4. Watch metrics at `/metrics` or Grafana (QPS, latency, errors). PromQL thresholds defined in `configs/alerts.yaml`.
5. Alertmanager posts to `/alerts` on the gateway. The webhook triggers rollback when error rate/p95/drift exceed thresholds. Successful runs promote canary to prod.

## Monitoring + Alerting
- Metrics: Prometheus scrapes gateway (`gateway_request_total`, `gateway_latency_seconds`, `feature_drift_score`, `gateway_current_model_version`) plus Triton metrics.
- Dashboard: `infra/grafana/dashboards/platform_dashboard.json` provisioned automatically (Grafana admin/admin).
- Alerts: `infra/prometheus/alerts.yaml` and `infra/prometheus/rules.yaml` fire HighErrorRate, HighLatencyP95, DriftDetected, TritonDown, GatewayDown via Alertmanager webhook to the gateway.

## Data Drift
- Baseline from `examples/feature_data.parquet`.
- For numeric features: Kolmogorov–Smirnov statistic.
- For categorical: PSI (population stability index).
- DriftMonitor keeps a sliding window (`configs/drift.yaml`) and exports `feature_drift_score{feature="..."}` gauges. Scores above threshold (default 0.3) trigger warnings and alerts.

## Feature Retrieval
- Default lightweight Parquet-backed store at `artifacts/features/store.parquet`.
- API: `GET /features?entity_id=123` on the feature-api service.
- Feast support optional via `mmsp.features.feast_adapter.FeastAdapter` when `feature_store.mode=feast`.
- Load sample features: `scripts/load_features.py` (reads `examples/feature_data.parquet`).

## Model Registry + Triton Repo
- Filesystem registry at `artifacts/registry/registry.json` with FastAPI service (`infra/docker-compose.yaml`).
- `mmsp register` stores versioned metadata (hash, created_at) and builds Triton repository layout under `examples/model_repository/<model>/<version>/`.

## One-Command CLI
- `mmsp up|down` – start/stop local stack
- `mmsp register` – register model + build Triton repo
- `mmsp deploy` – start canary with percentage split
- `mmsp promote` – promote canary to prod
- `mmsp rollback` – manual rollback
- `mmsp status` – show deployment state
- `mmsp loadgen` – send sample load and report p50/p95/error rate

## Add a New Model
1. Export ONNX artifact.
2. `mmsp register --model-path path/to/model.onnx --name your_model --version 1`
3. Update `configs/platform.yaml` if custom repo/path needed.
4. `mmsp deploy --name your_model --version 1 --canary 10`
5. Monitor metrics + alerts, then `mmsp promote --name your_model --version 1`.

## Drift Calculation Details
- Sliding window of recent feature values (`window_size` in `configs/drift.yaml`).
- Numeric: `ks_2samp` comparing recent vs baseline; Categorical: PSI with quantile bins.
- Exported as Prometheus gauges per feature; Alert rule triggers when max drift over 5m > threshold.

## Monitoring Screenshots
- Grafana URL: http://localhost:3000 (admin/admin).
- Panels: QPS, p95 latency, error rate, current prod/canary versions, per-feature drift.
- Prometheus UI: http://localhost:9090.

## Reproducibility
- Python 3.10+, pinned deps (`requirements.txt` + `constraints.txt`), deterministic configs stored under `artifacts/runs/<run_id>/`.
- CI: `.github/workflows/ci.yml` runs lint (`ruff`) and tests (`pytest`).
