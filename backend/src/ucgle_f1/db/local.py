"""A throwaway local Postgres cluster for tests and dev (P3-01).

Tests run against a real Postgres (never SQLite). CI provides one as a
``postgres:16`` service and sets ``DATABASE_URL``. Elsewhere,
:func:`start_local_postgres` creates a cluster with the installed server
binaries (``initdb``/``pg_ctl`` from ``pg_config --bindir`` or
``/usr/lib/postgresql/<ver>/bin``) in a temporary directory, on a free port.
Postgres refuses to run as root, so under root the cluster runs as the
``postgres`` user via ``runuser``.
"""

from __future__ import annotations

import glob
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LocalPostgres:
    url: str
    datadir: Path
    _bindir: Path
    _runas: list[str]

    def stop(self) -> None:
        subprocess.run(
            [*self._runas, str(self._bindir / "pg_ctl"), "-D", str(self.datadir), "-m", "immediate", "stop"],
            check=False, capture_output=True,
        )
        shutil.rmtree(self.datadir.parent, ignore_errors=True)


def find_bindir() -> Path | None:
    exe = shutil.which("pg_config")
    if exe:
        out = subprocess.run([exe, "--bindir"], capture_output=True, text=True, check=False).stdout.strip()
        if out and (Path(out) / "initdb").exists():
            return Path(out)
    for cand in sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True):
        if (Path(cand) / "initdb").exists():
            return Path(cand)
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def start_local_postgres() -> LocalPostgres:
    bindir = find_bindir()
    if bindir is None:
        msg = "no Postgres server binaries found (install postgresql or set DATABASE_URL)"
        raise RuntimeError(msg)
    root = Path(tempfile.mkdtemp(prefix="qcompass-pg-"))
    datadir = root / "data"
    runas: list[str] = []
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        runas = ["runuser", "-u", "postgres", "--"]
        shutil.chown(root, "postgres", "postgres")
        os.chmod(root, 0o700)
    port = _free_port()
    subprocess.run(
        [*runas, str(bindir / "initdb"), "-D", str(datadir), "-U", "postgres", "--auth=trust",
         "--encoding=UTF8", "--no-instructions"],
        check=True, capture_output=True,
    )
    subprocess.run(
        [*runas, str(bindir / "pg_ctl"), "-D", str(datadir), "-l", str(datadir / "server.log"),
         "-o", f"-p {port} -c listen_addresses=127.0.0.1 -c unix_socket_directories={root} "
               "-c fsync=off -c full_page_writes=off -c max_connections=200",
         "-w", "start"],
        check=True, capture_output=True,
    )
    url = f"postgresql://postgres@127.0.0.1:{port}/postgres"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        ready = subprocess.run(
            [str(bindir / "pg_isready"), "-h", "127.0.0.1", "-p", str(port)], capture_output=True, check=False,
        )
        if ready.returncode == 0:
            break
        time.sleep(0.2)
    return LocalPostgres(url=url, datadir=datadir, _bindir=bindir, _runas=runas)


__all__ = ["LocalPostgres", "find_bindir", "start_local_postgres"]
