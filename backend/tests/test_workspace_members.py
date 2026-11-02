"""Gate 1 nit (c7): the uv workspace lists its members one by one.

With ``members = ["packages/*"]`` any non-empty directory under packages/
without a pyproject.toml (the ``__pycache__`` that packages/conftest.py's
import writes, a stray ``node_modules``, a build output) became a workspace
member and every uv command failed with "Workspace member ... is missing a
pyproject.toml".
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _workspace() -> dict:
    return tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))


def _python_package_dirs() -> set[str]:
    """Every directory that holds a Python package of this repository."""
    return {"backend", "workers"} | {
        f"packages/{p.parent.name}" for p in (REPO / "packages").glob("*/pyproject.toml")
    }


def test_members_are_explicit_and_complete() -> None:
    root = _workspace()
    members = root["tool"]["uv"]["workspace"]["members"]
    assert all(not any(c in m for c in "*?[") for m in members), f"glob in members: {members}"
    assert set(members) == _python_package_dirs(), "every Python package directory, nothing else"
    sources = root["tool"]["uv"]["sources"]
    for member in members:
        project = tomllib.loads((REPO / member / "pyproject.toml").read_text(encoding="utf-8"))
        name = re.sub(r"[-_.]+", "-", project["project"]["name"]).lower()
        assert sources.get(name) == {"workspace": True}, f"{name} must resolve from the workspace"


def test_stray_directories_under_packages_do_not_break_uv(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is not on PATH; the backend suite runs under `uv run`")
    manifests = [f"{d}/pyproject.toml" for d in _python_package_dirs()]
    for rel in ["pyproject.toml", "uv.lock", *manifests]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, tmp_path / rel)
    junk_files = (
        "packages/__pycache__/conftest.cpython-312.pyc",
        "packages/node_modules/x/index.js",
        "packages/dist/x.whl",
    )
    for junk in junk_files:
        (tmp_path / junk).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / junk).write_bytes(b"")
    proc = subprocess.run(
        [uv, "lock", "--check", "--offline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
