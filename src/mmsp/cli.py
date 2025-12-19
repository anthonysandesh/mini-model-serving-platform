"""MMSP command line interface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from mmsp.deploy.canary import DeploymentState, load_state, promote_canary, rollback_canary, save_state, start_canary
from mmsp.deploy.triton_repo import build_triton_repository
from mmsp.registry.store import RegistryStore
from mmsp.utils.config import load_platform_config
from mmsp.utils.logging import configure_logging, get_logger

configure_logging()
LOG = get_logger(__name__)

app = typer.Typer(add_completion=False)
platform_cfg = load_platform_config()
registry_path = Path(platform_cfg.artifact_root) / "registry" / "registry.json"
registry = RegistryStore(registry_path)


def run(cmd: list[str]) -> None:
    LOG.info("Running command", extra={"cmd": " ".join(cmd)})
    subprocess.run(cmd, check=True)


@app.command()
def up() -> None:
    """Bring up local stack via docker-compose."""
    run(["docker-compose", "-f", "infra/docker-compose.yaml", "up", "-d"])


@app.command()
def down() -> None:
    """Tear down local stack."""
    run(["docker-compose", "-f", "infra/docker-compose.yaml", "down"])


@app.command()
def register(
    model_path: str = typer.Option(..., help="Path to ONNX model"),
    name: str = typer.Option(..., help="Model name"),
    framework: str = typer.Option("onnx", help="Framework"),
    version: Optional[int] = typer.Option(None, help="Version override"),
) -> None:
    mv = registry.register(name=name, framework=framework, artifact_path=model_path, version=version)
    build_triton_repository(
        artifact_path=model_path,
        model_name=name,
        version=mv.version,
        dest_repo=platform_cfg.model_repository,
        inputs=[{"name": "input", "dims": [4], "dtype": "TYPE_FP32"}],
        outputs=[{"name": "output", "dims": [1], "dtype": "TYPE_FP32"}],
    )
    typer.echo(f"Registered model {name} version {mv.version}")


@app.command()
def deploy(
    name: str = typer.Option("example_model", help="Model name"),
    version: int = typer.Option(..., help="Version to deploy"),
    env: str = typer.Option("local", help="local|k8s"),
    canary: int = typer.Option(10, help="Traffic percentage for canary"),
) -> None:
    state_path = platform_cfg.deployment_state
    state = start_canary(state_path, name, version, canary)
    typer.echo(f"Started canary for {name} v{version} at {canary}% traffic")


@app.command()
def promote(name: str = typer.Option("example_model"), version: int = typer.Option(...)) -> None:
    state = load_state(platform_cfg.deployment_state)
    state.model_name = name
    state.canary_version = version
    save_state(state, platform_cfg.deployment_state)
    promote_canary(platform_cfg.deployment_state)
    registry.promote(name, version, "prod")
    typer.echo(f"Promoted {name} v{version} to prod")


@app.command()
def rollback(name: str = typer.Option("example_model")) -> None:
    rollback_canary(platform_cfg.deployment_state)
    typer.echo(f"Rolled back canary for {name}")


@app.command()
def status() -> None:
    state = load_state(platform_cfg.deployment_state)
    typer.echo(state)


@app.command()
def loadgen(
    rps: int = typer.Option(20, help="Requests per second"),
    duration: int = typer.Option(30, help="Duration in seconds"),
    gateway_url: str = typer.Option("http://localhost:8080"),
) -> None:
    cmd = [
        sys.executable,
        "scripts/send_load.py",
        "--rps",
        str(rps),
        "--duration",
        str(duration),
        "--gateway",
        gateway_url,
    ]
    run(cmd)


if __name__ == "__main__":
    app()
