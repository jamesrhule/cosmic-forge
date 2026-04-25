"""Provider adapters (one per provider, all soft-imported)."""

from __future__ import annotations

from qcompass_router.providers.azure import AzureQuantumAdapter
from qcompass_router.providers.base import (
    BackendInfo,
    JobHandle,
    ProviderAdapter,
)
from qcompass_router.providers.braket import BraketAdapter
from qcompass_router.providers.ibm import IBMRuntimeAdapter
from qcompass_router.providers.ionq import IonQNativeAdapter
from qcompass_router.providers.iqm import IQMAdapter
from qcompass_router.providers.local_aer import LocalAerAdapter
from qcompass_router.providers.local_lightning import LocalLightningAdapter
from qcompass_router.providers.pasqal import PasqalAdapter
from qcompass_router.providers.quera import QueRaAdapter

__all__ = [
    "AzureQuantumAdapter",
    "BackendInfo",
    "BraketAdapter",
    "IBMRuntimeAdapter",
    "IonQNativeAdapter",
    "IQMAdapter",
    "JobHandle",
    "LocalAerAdapter",
    "LocalLightningAdapter",
    "PasqalAdapter",
    "ProviderAdapter",
    "QueRaAdapter",
    "default_adapters",
]


def default_adapters() -> list[ProviderAdapter]:
    """Return one instance of every adapter shipped with the package."""
    return [
        IBMRuntimeAdapter(),
        BraketAdapter(),
        AzureQuantumAdapter(),
        IonQNativeAdapter(),
        IQMAdapter(),
        QueRaAdapter(),
        PasqalAdapter(),
        LocalAerAdapter(),
        LocalLightningAdapter(),
    ]
