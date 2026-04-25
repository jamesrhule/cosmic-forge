"""Every provider adapter must import in a clean env (no SDKs / no creds)
and `is_available()` must return False when its SDK or credentials are
missing. CI runs without optional SDKs installed so this is the gate.
"""

from __future__ import annotations

import importlib

import pytest

PROVIDER_MODULES = [
    "qcompass_router.providers.ibm",
    "qcompass_router.providers.braket",
    "qcompass_router.providers.azure",
    "qcompass_router.providers.ionq",
    "qcompass_router.providers.iqm",
    "qcompass_router.providers.quera",
    "qcompass_router.providers.pasqal",
    "qcompass_router.providers.local_aer",
    "qcompass_router.providers.local_lightning",
]


@pytest.mark.parametrize("module_name", PROVIDER_MODULES)
def test_provider_module_imports_without_sdk(module_name: str) -> None:
    """Importing the module must not require the provider SDK."""
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_top_level_package_imports_cleanly() -> None:
    import qcompass_router

    assert qcompass_router.Router is not None
    assert qcompass_router.BackendRequest is not None
    assert qcompass_router.RoutingDecision is not None


def _has(module: str) -> bool:
    try:
        importlib.import_module(module)
    except Exception:  # noqa: BLE001
        return False
    return True


def test_cloud_adapters_unavailable_without_creds() -> None:
    """Cloud adapters must report `is_available() is False` without creds.

    We only assert this for adapters whose SDKs are NOT installed in the
    test environment — when the SDK is present the adapter may still be
    unavailable (no creds) but we don't want the test to be flaky.
    """
    from qcompass_router.providers import (
        AzureQuantumAdapter,
        BraketAdapter,
        IBMRuntimeAdapter,
        IonQNativeAdapter,
        IQMAdapter,
        PasqalAdapter,
        QueRaAdapter,
    )

    cases: list[tuple[object, str]] = [
        (IBMRuntimeAdapter(), "qiskit_ibm_runtime"),
        (BraketAdapter(), "braket.aws"),
        (AzureQuantumAdapter(), "azure.quantum"),
        (IonQNativeAdapter(), "ionq"),
        (IQMAdapter(), "iqm.iqm_client"),
        (QueRaAdapter(), "bloqade.analog"),
        (PasqalAdapter(), "pulser"),
    ]
    for adapter, sdk_module in cases:
        if _has(sdk_module):
            continue
        assert adapter.is_available() is False, (
            f"{type(adapter).__name__}.is_available() should be False "
            f"when {sdk_module} is not installed."
        )


def test_local_adapter_availability_tracks_sdk() -> None:
    """Local adapters' availability follows their SDK presence."""
    from qcompass_router.providers import (
        LocalAerAdapter,
        LocalLightningAdapter,
    )

    assert LocalAerAdapter().is_available() == _has("qiskit_aer")
    assert LocalLightningAdapter().is_available() == (
        _has("pennylane") and _has("pennylane_lightning")
    )
