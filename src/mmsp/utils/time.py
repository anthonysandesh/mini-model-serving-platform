"""Time helpers."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone


def current_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    git = git_short_hash()
    return f"{ts}-{git}" if git else ts


def git_short_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        return ""
    return result.stdout.decode().strip()
