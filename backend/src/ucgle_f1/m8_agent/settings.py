"""Environment-driven API settings (P3-06, P3-04).

Read from environment variables only (R9). Names are listed in
``.env.example``.

- ``QCOMPASS_ENV``: ``dev`` | ``staging`` | ``production``. Defaults to
  ``production``, so an unset variable never relaxes anything.
- ``QCOMPASS_CORS_ORIGINS``: comma-separated allowlist of browser origins.
  Unset means no cross-origin access, except in ``dev``, where the local
  Vite/wrangler origins are allowed. ``*`` is honoured only in ``dev``.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_DEV_ORIGINS = (
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8787",
    "http://127.0.0.1:8787",
)


def qcompass_env() -> str:
    env = os.environ.get("QCOMPASS_ENV", "production").strip().lower()
    return env if env in {"dev", "staging", "production"} else "production"


def is_dev() -> bool:
    return qcompass_env() == "dev"


def cors_origins() -> list[str]:
    raw = os.environ.get("QCOMPASS_CORS_ORIGINS", "")
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if not origins:
        return list(_DEV_ORIGINS) if is_dev() else []
    if "*" in origins and not is_dev():
        log.warning("QCOMPASS_CORS_ORIGINS='*' is ignored outside QCOMPASS_ENV=dev")
        origins = [o for o in origins if o != "*"]
    return origins


__all__ = ["cors_origins", "is_dev", "qcompass_env"]
