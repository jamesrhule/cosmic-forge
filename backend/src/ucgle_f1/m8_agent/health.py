"""Liveness and readiness probes (P3-06).

``GET /healthz``: the process is up and serving. Never touches
dependencies, so an orchestrator doesn't restart a healthy process just
because the database blips.

``GET /readyz``: the process can serve real traffic. It probes the
database (every store's ``ping()``), artifact storage (write and delete a
probe file) and the run queue. Returns 200 with every check, or 503 with
the failing ones, so a load balancer can drain the instance.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api_models import HealthResponse, ReadinessCheck, ReadinessResponse

log = logging.getLogger(__name__)

# A configuration gap the operator must close (R14), e.g.
# "BLOCKED-ON-JAMES:DATABASE_URL": the variable's name, never its value.
_BLOCKED = re.compile(r"BLOCKED-ON-JAMES:[A-Z][A-Z0-9_]*")


def _public_detail(exc: Exception) -> str:
    """What a failed check may say publicly: a BLOCKED-ON-JAMES marker, or "unavailable"."""
    found = _BLOCKED.search(str(exc))
    return found.group(0) if found else "unavailable"


def _artifacts_root() -> Path:
    env = os.environ.get("UCGLE_F1_ARTIFACTS")
    return Path(env) if env else Path.home() / ".ucgle_f1" / "artifacts"


def _check_database() -> None:
    from .auth import get_auth_store
    from .memory import get_store
    from .scans import get_scan_registry

    get_store().ping()
    get_auth_store().ping()
    get_scan_registry().ping()


def _check_storage() -> None:
    root = _artifacts_root()
    root.mkdir(parents=True, exist_ok=True)
    probe = root / f".readyz-{secrets.token_hex(4)}"
    probe.write_bytes(b"ok")
    probe.unlink()


def _check_queue() -> None:
    from .runs import get_registry

    get_registry().ping()


CHECKS: dict[str, Callable[[], None]] = {
    "database": _check_database,
    "storage": _check_storage,
    "queue": _check_queue,
}


def mount_health(app: FastAPI) -> None:
    @app.get("/healthz", response_model=HealthResponse, tags=["ops"])
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/readyz",
        response_model=ReadinessResponse,
        tags=["ops"],
        responses={503: {"model": ReadinessResponse, "description": "Not ready."}},
    )
    def readyz() -> JSONResponse:
        checks: dict[str, ReadinessCheck] = {}
        for name, probe in CHECKS.items():
            try:
                probe()
                checks[name] = ReadinessCheck(ok=True)
            except Exception as exc:  # noqa: BLE001 - any failure means not ready
                # SEC-L1: the probe is public; exception text can carry the
                # database host or user. The details go to the log only.
                log.warning("readiness check %s failed", name, exc_info=True)
                checks[name] = ReadinessCheck(ok=False, detail=_public_detail(exc))
        ready = all(c.ok for c in checks.values())
        body = ReadinessResponse(status="ready" if ready else "not_ready", checks=checks)
        return JSONResponse(body.model_dump(), status_code=200 if ready else 503)


__all__ = ["CHECKS", "mount_health"]
