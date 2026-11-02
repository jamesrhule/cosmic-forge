"""M12 — Resource estimators.

Adapter classes that wrap external resource estimators and return
unified :class:`ResourceEstimate` records. Heavy SDKs are imported
lazily at first use; absent dependencies surface as
:class:`ResourceEstimationError` so callers can degrade gracefully.
"""

from __future__ import annotations

from .azure_qre import AzureMicrosoftEstimatorAdapter
from .qrechem import QREChemAdapter
from .stub_estimator import StubEstimator
from .tfermion import TFermionAdapter

__all__ = [
    "AzureMicrosoftEstimatorAdapter",
    "QREChemAdapter",
    "StubEstimator",
    "TFermionAdapter",
]
