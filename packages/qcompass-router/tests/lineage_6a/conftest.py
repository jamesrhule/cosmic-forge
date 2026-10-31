"""Test fixtures + helpers for qcompass-router."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from qcompass_router.providers.base import (
    BackendInfo,
    JobHandle,
    ProviderAdapter,
)


SMALL_QASM = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
""".strip()


LARGE_QASM = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[40];
creg c[40];
h q[0];
""".strip()


class FakeAdapter(ProviderAdapter):
    """Configurable test double for `ProviderAdapter`.

    Instance attributes shadow the ClassVar declarations on the base ABC,
    which keeps each test instance independent.
    """

    # ClassVars on the ABC are unset; declare defaults here so abstract
    # checks see them, then override per-instance in __init__.
    name: ClassVar[str] = "fake"
    kind: ClassVar[str] = "cloud-other"

    def __init__(
        self,
        name: str,
        *,
        kind: str = "cloud-other",
        available: bool = True,
        backends: list[str] | None = None,
        cost: float = 1.0,
        per_backend_cost: dict[str, float] | None = None,
    ) -> None:
        # Per-instance shadowing of the ClassVars.
        self.name = name  # type: ignore[misc]
        self.kind = kind  # type: ignore[misc]
        self._available = available
        self._backends = backends or [f"{name}_backend"]
        self._cost = cost
        self._per_backend_cost = per_backend_cost or {}

    def is_available(self) -> bool:
        return self._available

    def list_backends(self) -> list[BackendInfo]:
        return [BackendInfo(provider=self.name, name=b) for b in self._backends]

    def estimate_cost_stub(self, circuit: Any, shots: int) -> float:
        return self._cost

    def estimate_cost_for(self, backend: str, shots: int) -> float:
        return self._per_backend_cost.get(backend, self._cost)

    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle:
        return JobHandle(provider=self.name, backend=backend, job_id="fake-job")


@pytest.fixture
def small_qasm() -> str:
    return SMALL_QASM


@pytest.fixture
def large_qasm() -> str:
    return LARGE_QASM


@pytest.fixture
def fake_adapter_factory():
    return FakeAdapter
