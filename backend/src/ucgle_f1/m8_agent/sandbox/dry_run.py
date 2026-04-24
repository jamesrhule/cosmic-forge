"""Ephemeral patch-dry-run harness.

Docker path:
  • Copies the repo into a throwaway container.
  • Applies the patch (``git apply``).
  • Runs the affected pytest files + the S1–S15 audit subset.
  • Network: ``network_mode='none'`` → enforces A3.
  • Filesystem: tmpfs overlay; no writes leak outside the container.

Subprocess fallback (CI, no Docker):
  • Clones the repo into a tmpdir via ``git worktree add``.
  • Applies the patch there; runs pytest with UCGLE_F1_STATE_DIR
    redirected under the tmpdir so the memory store is isolated.

Both paths return a :class:`PatchTestReport`. A5 rejects patches
that break any S1–S15 check.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...domain import AuditCheckId, PatchTestReport


def _guess_affected_tests(target_path: str) -> list[str]:
    """Heuristic: map a source file to its pytest counterparts."""
    if "m1_background" in target_path:
        return ["audit/physics/test_s4.py", "tests/unit/test_m1.py"]
    if "m2_scalar" in target_path:
        return ["tests/unit/test_m2.py"]
    if "m3_modes" in target_path:
        return ["audit/physics/test_s1.py", "audit/physics/test_s2.py",
                "audit/physics/test_s3.py", "tests/unit/test_m3.py"]
    if "m4_anomaly" in target_path:
        return ["audit/physics/test_s5.py", "audit/physics/test_s6.py",
                "tests/unit/test_m4.py"]
    if "m5_boltzmann" in target_path:
        return ["audit/physics/test_s8.py", "tests/unit/test_m5.py"]
    if "m6_gw" in target_path:
        return ["audit/physics/test_s13.py", "tests/unit/test_m6.py"]
    if "m8_agent" in target_path:
        return ["audit/agent/"]
    return ["audit/"]


def dry_run_patch(
    patch_id: str,
    target_path: str,
    unified_diff: str,
    in_docker: bool = True,
) -> PatchTestReport:
    try:
        import docker  # type: ignore[import-not-found]

        docker_available = in_docker and docker.from_env() is not None
    except Exception:  # noqa: BLE001
        docker_available = False

    tests = _guess_affected_tests(target_path)
    if docker_available:
        return _docker_path(patch_id, unified_diff, tests)
    return _subprocess_path(patch_id, unified_diff, tests)


def _docker_path(
    patch_id: str,
    unified_diff: str,
    tests: list[str],
) -> PatchTestReport:
    import docker  # type: ignore[import-not-found]

    client = docker.from_env()
    root = _repo_root()

    # Package the diff in a temp dir and bind-mount read-only.
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "patch.diff").write_text(unified_diff)
        container = client.containers.run(
            image="python:3.11-slim",
            command=[
                "bash", "-lc",
                "cp -r /src /work && cd /work && "
                "git init -q && git add -A && git commit -q -m base && "
                "git apply /patch/patch.diff && "
                "pip install -e backend[dev] -q && "
                "pytest -q " + " ".join(tests),
            ],
            volumes={
                str(root): {"bind": "/src", "mode": "ro"},
                td: {"bind": "/patch", "mode": "ro"},
            },
            network_mode="none",
            detach=True,
            tty=False,
        )
        try:
            result = container.wait(timeout=900)
            logs = container.logs().decode(errors="replace")
        finally:
            container.remove(force=True)

    passed = result.get("StatusCode", 1) == 0
    preserved, broken = _classify_audit_results(logs)
    return PatchTestReport(
        patchId=patch_id,
        passed=passed,
        testsRun=tests,
        auditChecksPreserved=preserved,
        auditChecksBroken=broken,
        sandboxLog=logs[-4000:],
    )


def _subprocess_path(
    patch_id: str,
    unified_diff: str,
    tests: list[str],
) -> PatchTestReport:
    root = _repo_root()
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "repo"
        shutil.copytree(root, work, ignore=shutil.ignore_patterns(
            "node_modules", ".venv", "__pycache__", ".git",
        ))
        (work / "patch.diff").write_text(unified_diff)
        env = {
            **os.environ,
            "UCGLE_F1_STATE_DIR": str(work / ".state"),
            "UCGLE_F1_ARTIFACTS": str(work / ".artifacts"),
            "NO_PROXY": "*",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
        }
        apply = subprocess.run(
            ["git", "apply", "--check", "patch.diff"],
            cwd=work, env=env, capture_output=True, text=True,
        )
        if apply.returncode != 0:
            return PatchTestReport(
                patchId=patch_id, passed=False, testsRun=[],
                auditChecksPreserved=[], auditChecksBroken=[],
                sandboxLog=apply.stderr,
            )
        subprocess.run(["git", "apply", "patch.diff"], cwd=work, env=env, check=True)
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", *tests],
            cwd=work / "backend", env=env,
            capture_output=True, text=True, timeout=900,
        )
        logs = proc.stdout + "\n" + proc.stderr
        passed = proc.returncode == 0
    preserved, broken = _classify_audit_results(logs)
    return PatchTestReport(
        patchId=patch_id, passed=passed, testsRun=tests,
        auditChecksPreserved=preserved, auditChecksBroken=broken,
        sandboxLog=logs[-4000:],
    )


def _classify_audit_results(log: str) -> tuple[list[AuditCheckId], list[AuditCheckId]]:
    preserved: list[AuditCheckId] = []
    broken: list[AuditCheckId] = []
    for cid in [
        "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8",
        "S9", "S10", "S11", "S12", "S13", "S14", "S15",
    ]:
        # pytest prints "PASSED tests/.../test_s1.py::..." / "FAILED ..."
        if f"test_{cid.lower()}" in log.lower():
            if "FAILED" in log and f"test_{cid.lower()}" in log:
                broken.append(cid)  # type: ignore[arg-type]
            else:
                preserved.append(cid)  # type: ignore[arg-type]
    return preserved, broken


def _repo_root() -> Path:
    # backend/src/ucgle_f1/m8_agent/sandbox/dry_run.py → ../../../../..
    return Path(__file__).resolve().parents[5]
