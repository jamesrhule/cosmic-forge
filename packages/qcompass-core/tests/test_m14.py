"""M14 router tests."""

from __future__ import annotations

import pytest

from qcompass_core import (
    BackendRequest,
    BackendUnavailableError,
    available_backends,
    get_backend,
    register_provider,
    reset_router,
)
from qcompass_core.m14_backend_router.backends import ClassicalCPUBackend


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_router()
    yield
    reset_router()


def test_classical_cpu_is_always_available() -> None:
    assert "classical_cpu" in available_backends()


def test_router_resolves_classical_kind_to_cpu() -> None:
    backend = get_backend(BackendRequest(kind="classical"))
    assert backend.name == "classical_cpu"


def test_router_explicit_target_works() -> None:
    backend = get_backend(BackendRequest(kind="auto", target="classical_cpu"))
    assert isinstance(backend, ClassicalCPUBackend)


def test_router_priority_list_works() -> None:
    backend = get_backend(BackendRequest(
        kind="auto", priority=["nonexistent", "classical_cpu"],
    ))
    assert backend.name == "classical_cpu"


def test_router_raises_for_unknown_target() -> None:
    with pytest.raises(BackendUnavailableError):
        get_backend(BackendRequest(kind="auto", target="warp_drive"))


def test_register_custom_provider() -> None:
    class FakeBackend:
        name = "fake_qpu"
        provider = "fakecorp"
        calibration_hash = "f0"

        def submit(self, payload, *, shots, seed):
            return {"echo": payload}

        def cost_estimate(self, payload):
            from qcompass_core import ResourceEstimate
            return ResourceEstimate(
                physical_qubits=1, logical_qubits=1, t_count=0,
                rotation_count=0, depth=1, runtime_seconds=0.0,
                estimator="stub",
            )

    class FakeProvider:
        name = "fakecorp"

        def list_backends(self) -> list[str]:
            return ["fake_qpu"]

        def get_backend(self, name: str):
            assert name == "fake_qpu"
            return FakeBackend()

    register_provider(FakeProvider())
    assert "fake_qpu" in available_backends()
    backend = get_backend(BackendRequest(kind="auto", target="fake_qpu"))
    assert backend.name == "fake_qpu"


def test_classical_cpu_submit_echoes_payload() -> None:
    backend = ClassicalCPUBackend()
    out = backend.submit({"hello": "world"}, shots=4, seed=1)
    assert out["echo"] == {"hello": "world"}
    assert out["shots"] == 4
