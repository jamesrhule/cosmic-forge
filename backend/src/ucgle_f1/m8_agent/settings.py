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


# ── Run stream bounds (SF1) ───────────────────────────────────────
# A stream of a run that never ends (a lost worker before the janitor
# fails it, a misbehaving client) must not poll forever. It ends with a
# terminal error event after QCOMPASS_STREAM_IDLE_SECONDS without a new
# event (default 900) or QCOMPASS_STREAM_MAX_SECONDS overall (default
# 7200, two job wall-clock limits), checked on every poll; the client
# reconnects and replays while the run is not over. A running job is never
# idle: its worker appends a heartbeat event at every lease renewal. A run
# that ended without a terminal event (its worker died between the two
# writes) ends its streams too, once it has been over for
# STREAM_TERMINAL_GRACE_SECONDS: the streams look at the run every
# STREAM_RUN_CHECK_SECONDS while no event arrives.

STREAM_RUN_CHECK_SECONDS = 1.0
STREAM_TERMINAL_GRACE_SECONDS = 2.0


def _positive_seconds(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


def stream_idle_seconds() -> float:
    return _positive_seconds("QCOMPASS_STREAM_IDLE_SECONDS", 900.0)


def stream_max_seconds() -> float:
    return _positive_seconds("QCOMPASS_STREAM_MAX_SECONDS", 7200.0)


class StreamBound:
    """Tracks one stream's idle and overall deadlines (monotonic clock)."""

    def __init__(self) -> None:
        import time

        self._clock = time.monotonic
        self._start = self._last = self._clock()
        self._next_run_check = self._start + STREAM_RUN_CHECK_SECONDS
        self.idle = stream_idle_seconds()
        self.max = stream_max_seconds()

    def saw_event(self) -> None:
        self._last = self._clock()

    def run_check_due(self) -> bool:
        """True at most every STREAM_RUN_CHECK_SECONDS: time to ask whether the run ended."""
        now = self._clock()
        if now < self._next_run_check:
            return False
        self._next_run_check = now + STREAM_RUN_CHECK_SECONDS
        return True

    def expired(self) -> str | None:
        """A reason when the stream must end, else None."""
        now = self._clock()
        if now - self._start >= self.max:
            return f"stream ended after {self.max:g}s (QCOMPASS_STREAM_MAX_SECONDS); reconnect to resume"
        if now - self._last >= self.idle:
            return f"no run event for {self.idle:g}s (QCOMPASS_STREAM_IDLE_SECONDS); reconnect to resume"
        return None
