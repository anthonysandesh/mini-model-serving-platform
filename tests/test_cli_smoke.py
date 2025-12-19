import os

from typer.testing import CliRunner

from mmsp import cli

runner = CliRunner()


def test_status_smoke(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_CONFIG", "configs/platform.yaml")
    result = runner.invoke(cli.app, ["status"])
    assert result.exit_code == 0
    assert "prod_version" in result.stdout
