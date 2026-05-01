"""Every provider adapter must import without its SDK installed.

`is_available()` MUST return False (or True only when the SDK is
genuinely importable) without raising. This guards the contract
that PROMPT 6A's package import never crashes on a minimal env.
"""

from __future__ import annotations

import pytest

from qcompass_router import (
    ALL_ADAPTERS,
    AzureAdapter,
    BraketAdapter,
    IBMAdapter,
    IonQAdapter,
    IQMAdapter,
    LocalAerAdapter,
    LocalLightningAdapter,
    PasqalAdapter,
    QueraAdapter,
    list_providers,
)


def test_all_adapter_classes_listed() -> None:
    expected = {
        LocalAerAdapter, LocalLightningAdapter, IBMAdapter, BraketAdapter,
        AzureAdapter, IonQAdapter, IQMAdapter, QueraAdapter, PasqalAdapter,
    }
    assert set(ALL_ADAPTERS) == expected


@pytest.mark.parametrize("adapter_cls", ALL_ADAPTERS)
def test_adapter_imports_and_is_available_does_not_raise(adapter_cls) -> None:
    adapter = adapter_cls()
    # is_available() MUST never raise — credentials / SDKs may be
    # absent in any combination.
    result = adapter.is_available()
    assert isinstance(result, bool)


def test_list_providers_returns_nine() -> None:
    providers = list_providers()
    assert len(providers) == len(ALL_ADAPTERS)
    names = {p.name for p in providers}
    assert names == {
        "local_aer", "local_lightning", "ibm", "braket", "azure",
        "ionq", "iqm", "quera", "pasqal",
    }


def test_list_backends_raises_when_sdk_absent_for_local_aer() -> None:
    """If qiskit-aer is genuinely missing the adapter must report so.

    The adapter itself doesn't raise on list_backends() (it only
    returns the static descriptor). But submit() raises ImportError
    cleanly.
    """
    aer = LocalAerAdapter()
    if aer.is_available():
        pytest.skip("qiskit-aer installed locally; skip the absent-SDK branch.")
    with pytest.raises((ImportError, NotImplementedError)):
        aer.submit(circuit=object(), shots=1, backend="aer_simulator")
