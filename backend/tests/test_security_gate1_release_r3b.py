"""Gate 1 round 3B (OPS2): release-please.yml's publish jobs run pinned code
and publish nothing R11 has not cleared.

- LOW, publish-pypi holds ``id-token: write`` (PyPI trusted publishing) but
  installed uv "latest" (setup-uv's default) and let ``uv build`` fetch the
  build backend ``hatchling>=1.24`` unpinned and unhashed; ``|| true`` hid a
  failed build, so a partial set could be published.
- c6-cuda12 residual, publish-docker pushed
  ghcr.io/jamesrhule/qcompass-runtime:cuda12, which carries NVIDIA's CUDA and
  cuDNN base and nvidia-*-cu12 wheels under NVIDIA's own licences. Until
  James answers BLOCKED-ON-JAMES:cuda-image-r11 it is not published.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import yaml
from packaging.requirements import Requirement

REPO = Path(__file__).resolve().parents[2]
RELEASE = REPO / ".github" / "workflows" / "release-please.yml"
CI = REPO / ".github" / "workflows" / "ci.yml"
CONSTRAINTS = "packages/build-constraints.txt"


def _wf() -> dict[str, Any]:
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))


def _pypi_steps() -> list[dict[str, Any]]:
    return list(_wf()["jobs"]["publish-pypi"]["steps"])


def _build_step() -> dict[str, Any]:
    (step,) = [st for st in _pypi_steps() if "uv build" in str(st.get("run", ""))]
    return step


def _locked_pins() -> dict[str, str]:
    """name -> version for each `name==version` entry with hashes."""
    text = (REPO / CONSTRAINTS).read_text(encoding="utf-8")
    entries = re.findall(
        r"^([A-Za-z0-9._-]+)==(\S+) \\\n((?:\s+--hash=sha256:[0-9a-f]{64}(?: \\)?\n)+)", text, re.M
    )
    requirement_lines = [ln for ln in text.splitlines() if re.match(r"^[A-Za-z0-9]", ln)]
    assert len(requirement_lines) == len(entries), "every build requirement is == and hashed"
    return {re.sub(r"[-_.]+", "-", n).lower(): v for n, v, _ in entries}


def test_pypi_job_installs_the_pinned_uv_with_its_checksum() -> None:
    setups = [st for st in _pypi_steps() if "astral-sh/setup-uv@" in str(st.get("uses"))]
    assert len(setups) == 1
    with_ = setups[0].get("with") or {}
    ci_uv = yaml.safe_load(CI.read_text(encoding="utf-8"))["env"]["UV_VERSION"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(with_.get("version"))), (
        f"setup-uv installs {with_.get('version', 'latest (the default)')!r}, not an exact uv"
    )
    assert str(with_["version"]) == ci_uv, "the same uv as CI and the images"
    assert re.fullmatch(r"[0-9a-f]{64}", str(with_.get("checksum"))), "the download is checksummed"


def test_pypi_build_backend_comes_from_the_hash_lock() -> None:
    run = str(_build_step()["run"])
    # One command per line once the shell's line continuations are joined.
    builds = [ln for ln in run.replace("\\\n", " ").splitlines() if "uv build" in ln]
    assert builds
    for cmd in builds:
        assert f"--build-constraints {CONSTRAINTS}" in cmd and "--require-hashes" in cmd, cmd
    pins = _locked_pins()
    built = re.findall(r"packages/([\w-]+)", run.split("uv build", 1)[0])
    on_disk = {p.parent.name for p in (REPO / "packages").glob("*/pyproject.toml")}
    assert set(built) == on_disk, "every published package is built under the lock"
    for name in built:
        project = tomllib.loads((REPO / "packages" / name / "pyproject.toml").read_text("utf-8"))
        system = project["build-system"]
        assert system["build-backend"] == "hatchling.build", name
        for spec in system["requires"]:
            req = Requirement(spec)
            key = re.sub(r"[-_.]+", "-", req.name).lower()
            assert key in pins, f"{name}: {spec} is not in {CONSTRAINTS}"
            assert req.specifier.contains(pins[key]), f"{name}: {spec} vs locked {pins[key]}"


def _fake_uv(bin_dir: Path, log: Path, failing: str) -> None:
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{log}"\n'
        'pkg=""; out=""\n'
        'while [ $# -gt 0 ]; do case "$1" in\n'
        '  --package) pkg="$2"; shift ;;\n'
        '  --out-dir) out="$2"; shift ;;\n'
        "esac; shift; done\n"
        f'[ "$pkg" = "{failing}" ] && {{ echo "build of $pkg failed" >&2; exit 1; }}\n'
        'mkdir -p "$out" && touch "$out/$pkg-0.0.0-py3-none-any.whl"\n'
    )
    uv.chmod(uv.stat().st_mode | stat.S_IXUSR)


def _run_build_step(tmp_path: Path, failing: str) -> tuple[int, list[str]]:
    log = tmp_path / "uv.log"
    _fake_uv(tmp_path / "bin", log, failing)
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", str(_build_step()["run"])],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.returncode, log.read_text().splitlines() if log.exists() else []


def test_a_failed_package_build_fails_the_publish_job(tmp_path: Path) -> None:
    code, calls = _run_build_step(tmp_path, failing="qfull-hep")
    assert code != 0, "a package that fails to build must stop the publish (no `|| true`)"
    assert any("--package qfull-hep" in c for c in calls)


def test_a_clean_build_builds_every_package_under_the_lock(tmp_path: Path) -> None:
    code, calls = _run_build_step(tmp_path, failing="(none)")
    assert code == 0
    assert len(calls) == 11, calls
    assert all(f"--build-constraints {CONSTRAINTS} --require-hashes" in c for c in calls), calls


def test_publish_pypi_hides_no_failure() -> None:
    job = _wf()["jobs"]["publish-pypi"]
    assert "continue-on-error" not in job
    for st in job["steps"]:
        assert "continue-on-error" not in st
        assert not re.search(r"\|\|\s*(true|:)\b", str(st.get("run", ""))), st.get("run")


def test_cuda12_image_is_not_published_while_r11_is_open() -> None:
    job = _wf()["jobs"]["publish-docker"]
    matrix = job["strategy"]["matrix"]
    excluded = [e.get("flavour") for e in matrix.get("exclude", [])]
    published = [f for f in matrix["flavour"] if f not in excluded]
    assert published == ["cpu"], f"publish-docker pushes {published}"
    runs = " ".join(str(st.get("run", "")) for st in job["steps"])
    assert "BLOCKED-ON-JAMES:cuda-image-r11" in runs, "the release says why cuda12 is missing"
    assert (REPO / "docker" / "Dockerfile.cuda12").exists(), "the image itself stays (R2)"
