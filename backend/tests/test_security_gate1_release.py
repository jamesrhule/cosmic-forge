"""Gate 1 round 3 (c6, MEDIUM): release-please.yml grants each job only what
it uses, pins every action to a commit SHA and installs the docs tools from a
hash-locked file.

At 9c6bf4c the workflow granted contents, pull-requests, packages, pages and
id-token write to every job, ran tag- or branch-pinned actions
(``pypa/gh-action-pypi-publish@release/v1``) and ran
``pip install mkdocs mkdocs-material pymdown-extensions`` unpinned, so a
moved tag or a compromised package could push to the repository, overwrite
the ghcr.io images or mint OIDC tokens. What each job publishes is unchanged;
the test pins that too.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
RELEASE = REPO / ".github" / "workflows" / "release-please.yml"
REQUIREMENTS = REPO / "docs" / "requirements.txt"

# The minimum each job needs, and nothing else.
PERMISSIONS = {
    "release-please": {"contents": "write", "pull-requests": "write"},
    "publish-pypi": {"contents": "read", "id-token": "write"},
    "publish-docker": {"contents": "read", "packages": "write"},
    "publish-docs": {"contents": "write"},
    "deploy-production": {"contents": "read", "id-token": "write"},
}


def _wf() -> dict[str, Any]:
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def test_no_default_permissions_and_minimum_per_job() -> None:
    wf = _wf()
    assert wf["permissions"] == {}, "the workflow grants nothing by default"
    assert set(wf["jobs"]) == set(PERMISSIONS)
    for name, job in wf["jobs"].items():
        assert job.get("permissions") == PERMISSIONS[name], f"{name}: {job.get('permissions')}"


def test_every_action_is_pinned_to_a_commit_with_its_tag() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    uses = [ln.strip() for ln in text.splitlines() if re.match(r"\s*(-\s+)?uses:", ln)]
    assert uses
    for line in uses:
        if re.fullmatch(r"uses:\s*\./\.github/workflows/deploy\.yml", line):
            continue  # this repository's own workflow, at the same commit
        assert re.fullmatch(
            r"(-\s+)?uses:\s*[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", line
        ), f"not pinned to a full commit SHA with its # vX.Y.Z tag: {line}"


def test_jobs_that_only_read_the_checkout_do_not_keep_its_token() -> None:
    wf = _wf()
    for name in ("publish-pypi", "publish-docker"):
        steps = _steps(wf["jobs"][name])
        (checkout,) = [st for st in steps if "actions/checkout@" in str(st.get("uses"))]
        assert checkout.get("with", {}).get("persist-credentials") is False, name


def test_docs_tools_install_from_the_hash_lock_only() -> None:
    wf = _wf()
    for name, job in wf["jobs"].items():
        for st in _steps(job):
            run = str(st.get("run", ""))
            if re.search(r"\bpip3?\b.*\binstall\b", run):
                assert name == "publish-docs", f"{name}: unexpected pip install"
                assert "--require-hashes" in run and "-r docs/requirements.txt" in run, run
                assert "--only-binary ':all:'" in run or "--only-binary :all:" in run, run
    lock = REQUIREMENTS.read_text(encoding="utf-8")
    entries = re.findall(
        r"^([A-Za-z0-9._-]+)==(\S+) \\\n((?:\s+--hash=sha256:[0-9a-f]{64}(?: \\)?\n)+)", lock, re.M
    )
    names = {n.lower() for n, _, _ in entries}
    requirement_lines = [ln for ln in lock.splitlines() if re.match(r"^[A-Za-z0-9]", ln)]
    assert len(requirement_lines) == len(entries), "every requirement is pinned with == and hashed"
    wanted = [
        ln.strip().lower()
        for ln in (REPO / "docs" / "requirements.in").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    assert wanted == ["mkdocs", "mkdocs-material", "pymdown-extensions"]
    assert set(wanted) <= names


def test_what_each_job_publishes_is_unchanged() -> None:
    jobs = _wf()["jobs"]
    (rp,) = _steps(jobs["release-please"])
    assert rp["with"] == {
        "config-file": ".github/release-please-config.json",
        "manifest-file": ".github/release-please-manifest.json",
    }
    assert jobs["publish-pypi"]["environment"] == "pypi"
    pypi_steps = _steps(jobs["publish-pypi"])
    (publish,) = [st for st in pypi_steps if "gh-action-pypi-publish" in str(st.get("uses"))]
    assert publish["with"] == {"packages-dir": "dist/"}
    docker_steps = _steps(jobs["publish-docker"])
    (push,) = [st for st in docker_steps if "build-push-action" in str(st.get("uses"))]
    assert push["with"]["push"] is True
    image = "ghcr.io/jamesrhule/qcompass-runtime:${{ matrix.flavour }}"
    assert push["with"]["tags"].splitlines() == [
        image,
        image + "-${{ needs.release-please.outputs.tag_name }}",
    ]
    assert jobs["publish-docker"]["strategy"]["matrix"]["flavour"] == ["cpu", "cuda12"]
    docs_runs = [st.get("run") for st in _steps(jobs["publish-docs"])]
    assert "mkdocs gh-deploy --force --clean" in docs_runs
    deploy = jobs["deploy-production"]
    assert deploy["uses"] == "./.github/workflows/deploy.yml"
    assert deploy["with"] == {"environment": "production"} and deploy["secrets"] == "inherit"
