"""Gate 1 round 4 (R4-FEOPS): every package publish-pypi publishes builds.

``publish-pypi`` (.github/workflows/release-please.yml) builds the 11
workspace packages with ``uv build`` under the hash-locked build backend and
stops at the first failure, so one package that cannot build means nothing is
published. Its own tests (backend/tests/test_security_gate1_release_r3b.py)
use a fake ``uv``. This file runs the job's build step verbatim with the real
``uv`` and the real build backend, so a package that cannot build fails the
``packages`` CI job on the PR instead of the next release.

The step runs in a scratch directory: its relative paths
(``packages/build-constraints.txt``, ``dist/``) resolve there, a symlink
makes ``packages/`` the workspace's own, and ``UV_PROJECT`` points uv at the
workspace, so the sources are built in place and nothing is written into the
checkout.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from collections import Counter
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
RELEASE = REPO / ".github" / "workflows" / "release-please.yml"


def _build_step_run() -> str:
    workflow = yaml.safe_load(RELEASE.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["publish-pypi"]["steps"]
    (run,) = [str(st["run"]) for st in steps if "uv build" in str(st.get("run", ""))]
    return run


def _published() -> list[str]:
    """The package directories the step builds, in its order."""
    return re.findall(r"packages/([\w-]+)", _build_step_run().split("uv build", 1)[0])


def _project(pkg: str) -> dict[str, object]:
    return tomllib.loads((REPO / "packages" / pkg / "pyproject.toml").read_text("utf-8"))


def _dist_stem(pkg: str) -> str:
    project = _project(pkg)["project"]
    assert isinstance(project, dict)
    return f"{re.sub(r'[-_.]+', '_', project['name']).lower()}-{project['version']}"


def _tracked(pkg: str, sub: str) -> list[str]:
    """Git-tracked files under packages/<pkg>/<sub>, relative to it."""
    root = f"packages/{pkg}/{sub}"
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", root],
        cwd=REPO,
        capture_output=True,
        check=True,
    ).stdout.decode()
    files = [f[len(root) + 1 :] for f in out.split("\0") if f]
    assert files, f"no tracked files under {root}"
    return files


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert shutil.which("uv"), "uv must be on PATH (CI's setup-uv puts it there)"
    work = tmp_path_factory.mktemp("release-build")
    (work / "packages").symlink_to(REPO / "packages", target_is_directory=True)
    proc = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _build_step_run()],
        cwd=work,
        env={**os.environ, "UV_PROJECT": str(REPO)},
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, (
        f"publish-pypi's build step failed ({proc.returncode}); nothing would be published:\n"
        f"{proc.stdout[-3000:]}\n{proc.stderr[-6000:]}"
    )
    return work / "dist"


def test_the_step_builds_every_workspace_package() -> None:
    on_disk = sorted(p.parent.name for p in (REPO / "packages").glob("*/pyproject.toml"))
    assert sorted(_published()) == on_disk
    assert len(on_disk) == 11


def test_every_package_builds_a_wheel_and_an_sdist(dist: Path) -> None:
    expected = set()
    for pkg in _published():
        stem = _dist_stem(pkg)
        expected |= {f"{stem}-py3-none-any.whl", f"{stem}.tar.gz"}
    # uv also writes a `.gitignore` into the out-dir; the publish action uploads
    # dist/*, which a dotfile never matches.
    assert {p.name for p in dist.iterdir() if not p.name.startswith(".")} == expected


@pytest.mark.parametrize("pkg", _published())
def test_the_wheel_ships_every_package_file_once(dist: Path, pkg: str) -> None:
    with zipfile.ZipFile(dist / f"{_dist_stem(pkg)}-py3-none-any.whl") as whl:
        names = whl.namelist()
    dupes = [n for n, c in Counter(names).items() if c > 1]
    assert not dupes, f"{pkg}: {dupes} added twice"
    wheel = _project(pkg)["tool"]["hatch"]["build"]["targets"]["wheel"]  # type: ignore[index]
    for src_dir in wheel["packages"]:
        module = Path(src_dir).name
        missing = [
            f
            for f in _tracked(pkg, src_dir)
            if f"{module}/{f}" not in names and not f.endswith(".pyc")
        ]
        assert not missing, f"{pkg}: the wheel lacks {missing}"


@pytest.mark.parametrize("pkg", _published())
def test_the_sdist_carries_the_sources(dist: Path, pkg: str) -> None:
    stem = _dist_stem(pkg)
    with tarfile.open(dist / f"{stem}.tar.gz") as sdist:
        names = set(sdist.getnames())
    assert f"{stem}/pyproject.toml" in names
    missing = [f for f in _tracked(pkg, "src") if f"{stem}/src/{f}" not in names]
    assert not missing, f"{pkg}: the sdist lacks {missing}"
