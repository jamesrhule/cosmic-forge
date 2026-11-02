"""Start a local compute API + worker on a throwaway Postgres (P4-02 e2e).

Used by ``scripts/e2e_live_serve.sh`` for the live Playwright project
(``playwright.live.config.ts``). Never touches a real database (R13):
Postgres is ``TEST_DATABASE_URL`` (CI's service container) or a cluster this
script starts and deletes, via the backend's test harness
(``ucgle_f1.db.pytest_plugin.scratch_database``); migrations are applied.

The API runs with development-only anonymous access
(``QCOMPASS_ENV=dev`` + ``QCOMPASS_DEV_ALLOW_ANONYMOUS=1``). That pair is
only ever set here and in tests; deploy configuration is checked to never
set it (``backend/tests/test_deploy_config.py``).

Usage: ``uv run --frozen python scripts/live_stack.py`` (stops on SIGTERM/
SIGINT, or when the API or worker exits). Ports: ``LIVE_API_PORT`` (8791),
web origin for CORS ``LIVE_WEB_ORIGIN`` (http://127.0.0.1:4312).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def _wait_http(url: str, timeout: float, proc: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"process exited ({proc.returncode}) before {url} answered")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.3)
    raise SystemExit(f"{url} did not answer within {timeout:.0f}s")


def main() -> int:
    from ucgle_f1.db.pytest_plugin import scratch_database

    port = int(os.environ.get("LIVE_API_PORT", "8791"))
    origin = os.environ.get("LIVE_WEB_ORIGIN", "http://127.0.0.1:4312")
    state = Path(tempfile.mkdtemp(prefix="qcompass-live-"))
    stop = {"flag": False}

    def _stop(*_: object) -> None:
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    with scratch_database() as url:
        if not url:
            print(
                "BLOCKED-ON-JAMES:DATABASE_URL (no Postgres binaries and no TEST_DATABASE_URL)",
                file=sys.stderr,
            )
            return 2
        env = {
            **os.environ,
            "DATABASE_URL": url,
            "QCOMPASS_ENV": "dev",
            "QCOMPASS_DEV_ALLOW_ANONYMOUS": "1",
            "QCOMPASS_CORS_ORIGINS": origin,
            "UCGLE_F1_STATE_DIR": str(state / "state"),
            "UCGLE_F1_ARTIFACTS": str(state / "artifacts"),
            "QCOMPASS_ARTIFACTS": str(state / "qcompass"),
            "PYTHONUNBUFFERED": "1",
        }
        env.pop(
            "SUPABASE_SERVICE_ROLE_KEY", None
        )  # artefact uploads report BLOCKED, never call out
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "ucgle_f1.m8_agent.server:build_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env=env,
        )
        worker = subprocess.Popen(
            [sys.executable, "-m", "qcompass_worker", "--classes", "cpu", "--poll-seconds", "0.2"],
            env=env,
        )
        procs = [api, worker]
        try:
            _wait_http(f"http://127.0.0.1:{port}/readyz", 120, api)
            print(
                f"live stack ready: api http://127.0.0.1:{port} (worker pid {worker.pid})",
                flush=True,
            )
            while not stop["flag"] and all(p.poll() is None for p in procs):
                time.sleep(0.5)
        finally:
            for p in procs:
                if p.poll() is None:
                    p.terminate()
            for p in procs:
                try:
                    p.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    p.kill()
        failed = [p.args[2] for p in procs if p.returncode not in (0, -signal.SIGTERM, None)]
        if failed and not stop["flag"]:
            print(f"live stack: {failed} exited unexpectedly", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
