"""A3 — sandbox containment.

dry-run must never write outside the sandbox path; network egress
is blocked at the Docker network level. We assert the invariants
structurally (the Docker path uses ``network_mode='none'``; the
subprocess path clears proxy env vars and relocates state dirs).
"""

from __future__ import annotations

import inspect

import pytest

from ucgle_f1.m8_agent.sandbox import dry_run
from ucgle_f1.m8_agent.sandbox.dry_run import dry_run_patch


@pytest.mark.a_audit
def test_docker_path_uses_no_network() -> None:
    src = inspect.getsource(dry_run)
    assert 'network_mode="none"' in src or "network_mode='none'" in src, (
        "Docker sandbox must set network_mode='none' for A3"
    )


@pytest.mark.a_audit
def test_subprocess_path_relocates_state_dirs() -> None:
    src = inspect.getsource(dry_run)
    assert "UCGLE_F1_STATE_DIR" in src
    assert "UCGLE_F1_ARTIFACTS" in src, (
        "Subprocess sandbox must redirect state + artifact paths"
    )
    assert '"HTTPS_PROXY": ""' in src or "'HTTPS_PROXY': ''" in src, (
        "Subprocess sandbox must clear HTTPS_PROXY"
    )


@pytest.mark.a_audit
def test_missing_patch_returns_clean_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Invalid diff should not crash; passed=False with diagnostic log.
    from ucgle_f1.domain import ServiceError

    from ucgle_f1.m8_agent.tools.patch import dry_run_patch as tool_wrapper

    with pytest.raises(ServiceError):
        tool_wrapper(patch_id="does_not_exist", in_docker=False)
    _ = dry_run_patch  # keep import so static analysers know it's used
