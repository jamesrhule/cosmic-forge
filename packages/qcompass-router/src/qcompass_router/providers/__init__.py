"""qcompass_router provider adapters.

Importing this subpackage MUST succeed even when no provider SDK
is installed. Each adapter is a thin shell around its vendor SDK
that defers all SDK references to method bodies.
"""

from __future__ import annotations

from .azure import AzureAdapter
from .base import BackendInfo, JobHandle, ProviderAdapter, ProviderKind
from .braket import BraketAdapter
from .ibm import IBMAdapter
from .ionq import IonQAdapter
from .iqm import IQMAdapter
from .local_aer import LocalAerAdapter
from .local_lightning import LocalLightningAdapter
from .pasqal import PasqalAdapter
from .quera import QueraAdapter

ALL_ADAPTERS: tuple[type[ProviderAdapter], ...] = (
    LocalAerAdapter,
    LocalLightningAdapter,
    IBMAdapter,
    BraketAdapter,
    AzureAdapter,
    IonQAdapter,
    IQMAdapter,
    QueraAdapter,
    PasqalAdapter,
)


def list_providers() -> list[ProviderAdapter]:
    """Instantiate every shipped adapter."""
    return [cls() for cls in ALL_ADAPTERS]


__all__ = [
    "ALL_ADAPTERS",
    "AzureAdapter",
    "BackendInfo",
    "BraketAdapter",
    "IBMAdapter",
    "IonQAdapter",
    "IQMAdapter",
    "JobHandle",
    "LocalAerAdapter",
    "LocalLightningAdapter",
    "PasqalAdapter",
    "ProviderAdapter",
    "ProviderKind",
    "QueraAdapter",
    "list_providers",
]
