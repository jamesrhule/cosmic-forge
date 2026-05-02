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
    DeviceCalibration,
    load_calibration_seed,
)
from .pricing import Cost, LivePricing, PricingEngine
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
    "Cost",
    "DeviceCalibration",
    "IBMAdapter",
    "IonQAdapter",
    "IQMAdapter",
    "JobHandle",
    "LivePricing",
    "LocalAerAdapter",
    "LocalLightningAdapter",
    "PasqalAdapter",
    "PricingEngine",
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
    "load_calibration_seed",
    "pricing",
    "pricing_stub",
    "ssl_pin",
    "transforms",
]
