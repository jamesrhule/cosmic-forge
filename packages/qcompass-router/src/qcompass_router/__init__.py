"""qcompass-router — cost-aware backend router."""

from __future__ import annotations

from . import pricing, pricing_stub, ssl_pin, transforms
from .budget import (
    BudgetExceeded,
    ProjectBudget,
    UserBudget,
)
from .calibration import (
    CalibrationCache,
    CalibrationDrift,
    CalibrationSnapshot,
)
from .decision import (
    BackendRequest,
    RouterRequest,
    RoutingDecision,
    TransformRecord,
)
from .providers import (
    ALL_ADAPTERS,
    AzureAdapter,
    BackendInfo,
    BraketAdapter,
    IBMAdapter,
    IonQAdapter,
    IQMAdapter,
    JobHandle,
    LocalAerAdapter,
    LocalLightningAdapter,
    PasqalAdapter,
    ProviderAdapter,
    ProviderKind,
    QueraAdapter,
    list_providers,
)
from .router import Router

__version__ = "0.1.0"

__all__ = [
    "ALL_ADAPTERS",
    "AzureAdapter",
    "BackendInfo",
    "BackendRequest",
    "BraketAdapter",
    "BudgetExceeded",
    "CalibrationCache",
    "CalibrationDrift",
    "CalibrationSnapshot",
    "IBMAdapter",
    "IonQAdapter",
    "IQMAdapter",
    "JobHandle",
    "LocalAerAdapter",
    "LocalLightningAdapter",
    "PasqalAdapter",
    "ProjectBudget",
    "ProviderAdapter",
    "ProviderKind",
    "QueraAdapter",
    "Router",
    "RouterRequest",
    "RoutingDecision",
    "TransformRecord",
    "UserBudget",
    "list_providers",
    "pricing",
    "pricing_stub",
    "ssl_pin",
    "transforms",
]
