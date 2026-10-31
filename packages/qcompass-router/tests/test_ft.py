"""qcompass_router.ft tests (PROMPT 9 v2 §C)."""

from __future__ import annotations

import pytest

from qcompass_router.ft import (
    FaultTolerantPlan,
    PINNED_TEST_VECTORS,
    azure_re_pin_for,
    surface_code_compile,
)


class _StubCircuit:
    def __init__(self, n: int, ops: dict[str, int]) -> None:
        self.num_qubits = n
        self._ops = ops

    def count_ops(self) -> dict[str, int]:
        return dict(self._ops)


def test_surface_code_compile_returns_plan_for_femoco_shape() -> None:
    plan = surface_code_compile(
        _StubCircuit(152, {"ccx": 900_000, "t": 1_500_000}),
        code_distance=17,
    )
    assert isinstance(plan, FaultTolerantPlan)
    assert plan.logical_qubits == 152
    assert plan.physical_qubits >= plan.logical_qubits
    assert plan.toffoli_count == 900_000
    assert plan.magic_state_factory.startswith("ZX_15to1")
    assert plan.wallclock_s > 0.0


def test_surface_code_compile_rejects_zero_qubit_circuit() -> None:
    with pytest.raises(ValueError, match="num_qubits"):
        surface_code_compile(_StubCircuit(0, {}))


def test_pinned_test_vectors_present() -> None:
    assert "femoco_thc_active_152" in PINNED_TEST_VECTORS
    assert "schwinger_3plus1d_n128" in PINNED_TEST_VECTORS
    for vec in PINNED_TEST_VECTORS.values():
        for key in (
            "logical_qubits", "physical_qubits", "wallclock_s",
            "toffoli_count", "magic_state_factory", "code_distance",
        ):
            assert key in vec


def test_azure_re_pin_for_picks_closest_vector() -> None:
    pin = azure_re_pin_for(152, 6_300_000)
    assert pin is not None
    assert pin["logical_qubits"] == 152


def test_plan_envelope_round_trip() -> None:
    plan = surface_code_compile(_StubCircuit(8, {"ccx": 64}))
    env = plan.to_envelope()
    for key in (
        "logical_qubits", "physical_qubits", "wallclock_s",
        "toffoli_count", "magic_state_factory", "provider",
    ):
        assert key in env


def test_femoco_template_emits_qir_and_plan(tmp_path) -> None:
    pytest.importorskip("qfull_chem.femoco_ft")
    from qfull_chem.femoco_ft import emit_femoco_qpe_template
    qir_path, plan = emit_femoco_qpe_template(qir_dir=tmp_path)
    assert qir_path.exists()
    text = qir_path.read_text()
    assert "FeMoco" in text
    assert plan.toffoli_count == 6_300_000
    assert plan.qir_path == str(qir_path)
    pin = PINNED_TEST_VECTORS["femoco_thc_active_152"]
    # Plan should be in the same order of magnitude as the Azure RE pin.
    assert plan.logical_qubits == pin["logical_qubits"]
    assert plan.toffoli_count == pin["toffoli_count"]


def test_schwinger_template_emits_qir_and_plan(tmp_path) -> None:
    pytest.importorskip("qfull_hep.ft")
    from qfull_hep.ft import emit_schwinger_ft_qpe_template
    qir_path, plan = emit_schwinger_ft_qpe_template(qir_dir=tmp_path)
    assert qir_path.exists()
    assert plan.toffoli_count == 4_400_000
    assert plan.code_distance == 15
    pin = PINNED_TEST_VECTORS["schwinger_3plus1d_n128"]
    assert plan.logical_qubits == pin["logical_qubits"]
    assert plan.toffoli_count == pin["toffoli_count"]


def test_femoco_template_execute_raises() -> None:
    pytest.importorskip("qfull_chem.femoco_ft")
    from qfull_chem.femoco_ft import FemocoQPETemplate
    with pytest.raises(NotImplementedError, match="dormant"):
        FemocoQPETemplate().execute()


def test_schwinger_template_execute_raises() -> None:
    pytest.importorskip("qfull_hep.ft")
    from qfull_hep.ft import SchwingerFTTemplate
    with pytest.raises(NotImplementedError, match="dormant"):
        SchwingerFTTemplate().execute()
