"""qcompass-router — cost-aware backend router."""

from __future__ import annotations

from . import ft, pricing, pricing_stub, ssl_pin, transforms
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
    FoMaC,
    assert_no_drift,
    load_calibration_seed,
)
from .decision import (
    BackendRequest,
    RouterRequest,
    RoutingDecision,
    TransformRecord,
)
from .ft import FaultTolerantPlan, surface_code_compile
from .pricing import (
    Cost,
    FreeTierLedger,
    LivePricing,
    PricingEngine,
    set_tenant_budget_hook,
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
    "FaultTolerantPlan",
    "FoMaC",
    "FreeTierLedger",
    "IBMAdapter",
    "IQMAdapter",
    "IonQAdapter",
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
    "assert_no_drift",
    "ft",
    "list_providers",
    "load_calibration_seed",
    "pricing",
    "pricing_stub",
    "set_tenant_budget_hook",
    "ssl_pin",
    "surface_code_compile",
    "transforms",
]
