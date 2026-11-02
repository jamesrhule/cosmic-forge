"""Gate 0 review: 6A/6B router APIs restored on the unified router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import qcompass_router
from qcompass_router import PricingEngine, ProjectBudget, Router, UserBudget
from qcompass_router.transforms import cutting, mpf, obp


def test_project_budget_accepts_6b_member_user_ids_and_defaults() -> None:
    b = ProjectBudget(project_id="p", member_user_ids=["u1", "u2"], spent_usd=3.0, monthly_cap_usd=10.0)
    assert b.members == ["u1", "u2"]
    assert b.member_user_ids == ["u1", "u2"]
    assert b.remaining_usd == 7.0
    assert ProjectBudget(project_id="p").monthly_cap_usd == 0.0
    assert ProjectBudget(project_id="p", members=["a"]).member_user_ids == ["a"]
    with pytest.raises(ValueError):
        ProjectBudget(project_id="p", unknown_field=1)


def test_user_budget_6a_defaults() -> None:
    u = UserBudget(user_id="u")
    assert u.monthly_cap_usd == 0.0
    assert u.remaining_usd == 0.0
    assert UserBudget(user_id="u", period_start=None).period_start is None


def test_router_default_pricing_engine_and_property(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCOMPASS_PRICING_CACHE", str(tmp_path))
    r = Router(providers=[])
    assert isinstance(r.pricing, PricingEngine)
    assert r.free_tier_ledger is r.pricing.ledger
    engine = PricingEngine(cache_dir=tmp_path)
    assert Router(providers=[], pricing=engine).pricing is engine


def test_router_seed_path_accepts_only_package_seed(tmp_path: Path) -> None:
    from importlib import resources

    seed = Path(str(resources.files("qcompass_router.fixtures").joinpath("pricing_seed.yaml")))
    Router(providers=[], seed_path=seed)
    other = tmp_path / "seed.yaml"
    other.write_text("providers: {}\n")
    with pytest.raises(ValueError, match="package pricing seed"):
        Router(providers=[], seed_path=other)


def test_top_level_apply_transforms_export() -> None:
    assert "apply_transforms" in qcompass_router.__all__
    assert qcompass_router.apply_transforms is qcompass_router.transforms.apply_transforms


@pytest.mark.parametrize(("mod", "addon_mod", "fn_name"), [
    (cutting, "qiskit_addon_cutting", "cut_wires"),
    (obp, "qiskit_addon_obp", "backpropagate"),
    (mpf, "qiskit_addon_mpf", "trotter_circuit"),
])
def test_module_apply_forwards_kwargs_to_addon(
    monkeypatch: pytest.MonkeyPatch, mod: Any, addon_mod: str, fn_name: str,
) -> None:
    seen: dict[str, Any] = {}

    class _Addon:
        pass

    def _fn(circuit: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        return circuit

    setattr(_Addon, fn_name, staticmethod(_fn))
    monkeypatch.setattr("qcompass_router.transforms._common.try_import", lambda name: _Addon if name == addon_mod else None)
    _, record = mod.apply("OPENQASM 2.0;", custom_option=3)
    assert seen == {"custom_option": 3}
    assert record.parameters["custom_option"] == 3


@pytest.mark.parametrize(("mod", "addon_mod", "fn_name", "named"), [
    (cutting, "qiskit_addon_cutting", "cut_wires", {"max_subcircuit_width": 4}),
    (obp, "qiskit_addon_obp", "backpropagate", {"threshold": 0.01}),
    (mpf, "qiskit_addon_mpf", "trotter_circuit", {"order": 2}),
])
def test_module_apply_forwards_named_parameters_like_6b(
    monkeypatch: pytest.MonkeyPatch, mod: Any, addon_mod: str, fn_name: str, named: dict[str, Any],
) -> None:
    seen: dict[str, Any] = {}

    class _Addon:
        pass

    def _fn(circuit: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        return circuit

    setattr(_Addon, fn_name, staticmethod(_fn))
    monkeypatch.setattr("qcompass_router.transforms._common.try_import", lambda name: _Addon if name == addon_mod else None)
    _, record = mod.apply("OPENQASM 2.0;", **named)
    assert seen == named
    for k, v in named.items():
        assert record.parameters[k] == v


def test_aqc_tensor_apply_forwards_kwargs_to_optimise(monkeypatch: pytest.MonkeyPatch) -> None:
    from qcompass_router.transforms import aqc_tensor

    seen: dict[str, Any] = {}

    class _Addon:
        @staticmethod
        def generate_ansatz_from_circuit(circuit: Any) -> str:
            return "target"

        @staticmethod
        def MaximizeStateFidelity(*, target: Any, ansatz: Any) -> tuple[Any, Any]:
            return (target, ansatz)

        @staticmethod
        def optimise(objective: Any, **kwargs: Any) -> str:
            seen.update(kwargs)
            return "compiled"

    monkeypatch.setattr("qcompass_router.transforms._common.try_import", lambda name: _Addon if name == "qiskit_addon_aqc_tensor" else None)
    out, record = aqc_tensor.apply("OPENQASM 2.0;", foo=1, target_fidelity=0.9)
    assert out == "compiled"
    assert seen == {"foo": 1, "target_fidelity": 0.9}
    assert record.parameters["foo"] == 1
    aqc_tensor.apply_aqc_tensor("OPENQASM 2.0;", maxiter=5)
    assert seen["maxiter"] == 5
