"""qcompass_router provider adapters.

Importing this subpackage MUST succeed even when no provider SDK
is installed. Each adapter is a thin shell around its vendor SDK
that defers all SDK references to method bodies.
"""

from __future__ import annotations

from .azure import AzureAdapter
from .base import (
    KIND_FIDELITY_PRIOR,
    KIND_QUEUE_PRIOR_S,
    BackendInfo,
    JobHandle,
    ProviderAdapter,
    ProviderKind,
)
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


# PROMPT 6A class names (main-lineage callers + tests/lineage_6a).
# Aliases, not copies: one adapter class per provider.
AzureQuantumAdapter = AzureAdapter
IBMRuntimeAdapter = IBMAdapter
IonQNativeAdapter = IonQAdapter
QueRaAdapter = QueraAdapter


def list_providers() -> list[ProviderAdapter]:
    """Instantiate every shipped adapter."""
    return [cls() for cls in ALL_ADAPTERS]


# PROMPT 6A name for :func:`list_providers`.
default_adapters = list_providers


__all__ = [
    "ALL_ADAPTERS",
    "KIND_FIDELITY_PRIOR",
    "KIND_QUEUE_PRIOR_S",
    "AzureAdapter",
    "AzureQuantumAdapter",
    "BackendInfo",
    "BraketAdapter",
    "IBMAdapter",
    "IBMRuntimeAdapter",
    "IonQAdapter",
    "IonQNativeAdapter",
    "IQMAdapter",
    "JobHandle",
    "LocalAerAdapter",
    "LocalLightningAdapter",
    "PasqalAdapter",
    "ProviderAdapter",
    "ProviderKind",
    "QueRaAdapter",
    "QueraAdapter",
    "default_adapters",
    "list_providers",
]
