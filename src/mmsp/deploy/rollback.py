"""Rollback helpers triggered by alerts."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from mmsp.deploy.canary import rollback_canary
from mmsp.utils.logging import get_logger

LOG = get_logger(__name__)


def handle_alert(alert: Dict[str, object], state_path: str | Path) -> None:
    """Handle alertmanager webhook payload."""
    labels = alert.get("labels", {})
    name = labels.get("alertname") or labels.get("alert")
    severity = labels.get("severity", "")
    LOG.warning("Received alert", extra={"name": name, "severity": severity})
    rollback_canary(state_path)
