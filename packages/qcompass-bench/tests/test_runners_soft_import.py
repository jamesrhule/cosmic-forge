"""External-runner adapters import without their SDKs (PROMPT 1 v2)."""

from __future__ import annotations

import pytest

from qcompass_bench.runners import (
    MQTBenchAdapter,
    QedCAdapter,
    SupermarQAdapter,
)


@pytest.mark.parametrize(
    "cls",
    [MQTBenchAdapter, QedCAdapter, SupermarQAdapter],
)
def test_adapter_imports_and_is_available_does_not_raise(cls) -> None:
    adapter = cls()
    # is_available() MUST never raise — SDKs may be absent in any
    # combination.
    available = adapter.is_available()
    assert isinstance(available, bool)


def test_mqt_bench_run_raises_when_sdk_absent() -> None:
    pytest.importorskip("pytest")  # always available; just to keep import order
    if MQTBenchAdapter().is_available():
        pytest.skip("mqt.bench installed locally; skip the absent-SDK branch")
    with pytest.raises(ImportError, match="mqt.bench"):
        MQTBenchAdapter().run("ghz", n_qubits=4)


def test_supermarq_run_raises_when_sdk_absent() -> None:
    if SupermarQAdapter().is_available():
        pytest.skip("supermarq installed locally; skip the absent-SDK branch")
    with pytest.raises(ImportError, match="supermarq"):
        SupermarQAdapter().run("hamiltonian-simulation")


def test_qed_c_run_raises_when_sdk_absent() -> None:
    if QedCAdapter().is_available():
        pytest.skip("qedc_benchmarks vendored locally; skip the absent path")
    with pytest.raises(ImportError, match="QED-C"):
        QedCAdapter().run("vqe-h2")
