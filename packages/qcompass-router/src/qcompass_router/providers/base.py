"""Provider adapter ABC + shared dataclasses.

Phase-6A: every concrete adapter soft-imports its SDK inside `is_available()`
so importing this package never raises in environments without provider SDKs.
"""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

ProviderKind = Literal[
    "local", "cloud-sc", "cloud-ion", "cloud-neutral-atom", "cloud-other"
]


@dataclass
class BackendInfo:
    """Minimal description of a backend a provider exposes."""

    provider: str
    name: str
    n_qubits: int = 0
    is_simulator: bool = False
    queue_length: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobHandle:
    """Opaque handle returned from `submit`. Phase-6B fills in retrieval."""

    provider: str
    backend: str
    job_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _try_import(*module_names: str) -> bool:
    """Return True iff every name in `module_names` imports without error.

    Used by adapters' `is_available()` so that missing SDKs / credentials
    never propagate at package-import time.
    """
    for name in module_names:
        try:
            importlib.import_module(name)
        except Exception:  # noqa: BLE001 — soft probe
            return False
    return True


class ProviderAdapter(ABC):
    """Provider adapter contract."""

    name: ClassVar[str]
    kind: ClassVar[ProviderKind]

    @abstractmethod
    def list_backends(self) -> list[BackendInfo]: ...

    @abstractmethod
    def estimate_cost_stub(self, circuit: Any, shots: int) -> float: ...

    @abstractmethod
    def submit(self, circuit: Any, shots: int, backend: str) -> JobHandle: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    def __repr__(self) -> str:  # pragma: no cover — trivial
        return f"<{type(self).__name__} name={self.name!r} kind={self.kind!r}>"
