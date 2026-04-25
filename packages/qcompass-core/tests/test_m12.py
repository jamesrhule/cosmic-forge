"""M12 estimator tests (the always-available stub + skip optional adapters)."""

from __future__ import annotations

import pytest

from qcompass_core import (
    AzureMicrosoftEstimatorAdapter,
    BackendRequest,
    Manifest,
    QREChemAdapter,
    ResourceEstimate,
    ResourceEstimationError,
    StubEstimator,
    TFermionAdapter,
)


def _manifest(label: str = "demo") -> Manifest:
    return Manifest(
        domain="null",
        version="1.0",
        problem={"label": label, "padding": "x" * 64},
        backend_request=BackendRequest(kind="classical"),
    )


def test_stub_estimator_returns_resource_estimate() -> None:
    est = StubEstimator().estimate(_manifest(), payload=None)
    assert isinstance(est, ResourceEstimate)
    assert est.estimator == "stub"
    assert est.physical_qubits > 0


def test_stub_estimator_scales_with_payload_size() -> None:
    big = StubEstimator().estimate(_manifest(label="x" * 200), payload=None)
    small = StubEstimator().estimate(_manifest(label="x"), payload=None)
    assert big.physical_qubits >= small.physical_qubits


def test_azure_adapter_raises_without_workspace() -> None:
    pytest.importorskip("azure.quantum")  # pragma: no cover - optional path
    with pytest.raises(ResourceEstimationError):
        AzureMicrosoftEstimatorAdapter().estimate(_manifest(), payload=None)


def test_qrechem_adapter_raises_when_unavailable() -> None:
    with pytest.raises(ResourceEstimationError):
        QREChemAdapter().estimate(_manifest(), payload=None)


def test_tfermion_adapter_raises_when_unavailable() -> None:
    with pytest.raises(ResourceEstimationError):
        TFermionAdapter().estimate(_manifest(), payload=None)
