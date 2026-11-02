"""W1 round 4, lane R4-API: compile capacity, the compile child's limits and
parameter names, and the scan's caps and approval order (items 3 to 5).

Item IDs match ``docs/build/lanes/W1-r4-api.md``. All are the round-3B API3
verifier's LOW findings.

* R4-3: the 4 compile slots were global, the wait for one came out of the
  10 s compile limit (a trivial potential was told "simplify the
  expression"), and a capacity refusal was a 422 INVALID_INPUT.
* R4-4: the compile child had no memory limit and normal priority, and
  custom parameter names reached ``sympy.symbols`` unvalidated
  (``'a:9999999'`` is ten million Symbols).
* R4-5: ``scan_parameters`` validated every cell before checking its
  approval, and ``ScanSpec`` had no size cap.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api3_compile_helpers as helpers
from ucgle_f1.domain import EnginePotential, Potential, RunConfig, ScanAxis, ScanSpec, ServiceError
from ucgle_f1.m2_scalar import check, compile_potential, potentials
from ucgle_f1.m8_agent.auth import get_auth_store
from ucgle_f1.m8_agent.server import build_app

REPO = Path(__file__).resolve().parents[2]
RUN_FIXTURE = Path(__file__).resolve().parent / "data" / "gate1_run_result.json"


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """An enterprise tenant (acme) with a run-scope API key, production mode."""
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_ENV", raising=False)
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    store = get_auth_store()
    tok = store.issue("acme", scopes=["read", "run"])
    store.ensure_tenant("acme")
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("update public.tenants set subscription_tier = 'enterprise' where slug = 'acme'")
    return {
        "client": TestClient(build_app()),
        "headers": {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"},
    }


def _custom(source: str = "m**2*phi**2/2", **params: float) -> dict[str, Any]:
    return {"kind": "custom", "params": {"m": 1.0e-6, "phi0": 15.0, **params}, "customPython": source}


def _submit(api: dict[str, Any], potential: dict[str, Any]) -> Any:
    v2 = json.loads((REPO / "src" / "lib" / "configDefaults.json").read_text())["v2"]
    manifest = {"potential": potential, "couplings": dict(v2["couplings"]),
                "reheating": dict(v2["reheating"]), "precision": v2["precision"]}
    return api["client"].post("/api/qcompass/domains/cosmology.ucglef1/runs",
                              json={"manifest": manifest}, headers=api["headers"])


# ── R4-3: capacity is not the input's fault ──────────────────────────


def test_r4_3_waiting_for_a_slot_does_not_eat_the_compile_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 0c4848f the deadline started before the slot wait: with the only slot
    held for 4.5 s, a 5 s limit left 0.5 s for a ~1 s compile, and the trivial
    potential was refused as 'did not finish within 5 s; simplify the expression'."""
    monkeypatch.setattr(check, "_SLOTS", threading.BoundedSemaphore(1))
    monkeypatch.setattr(check, "CUSTOM_COMPILE_WAIT_SECONDS", 8.0, raising=False)
    assert check._SLOTS.acquire(timeout=1)
    releaser = threading.Timer(4.5, check._SLOTS.release)
    releaser.start()
    try:
        t0 = time.monotonic()
        check.check_potential(Potential(**_custom()), timeout=5.0)
        assert time.monotonic() - t0 >= 4.5  # it did wait for the slot
    finally:
        releaser.join()


def test_r4_3_a_full_server_is_a_503_with_retry_after_not_a_422(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On 0c4848f this was 422 INVALID_INPUT although the input was fine."""
    monkeypatch.setattr(check, "_SLOTS", threading.BoundedSemaphore(1))
    monkeypatch.setattr(check, "CUSTOM_COMPILE_WAIT_SECONDS", 0.3, raising=False)
    assert check._SLOTS.acquire(timeout=1)
    try:
        resp = _submit(api, _custom())
    finally:
        check._SLOTS.release()
    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAVAILABLE"
    assert "compiling other custom potentials" in detail["message"]
    assert "simplify" not in detail["message"]
    assert resp.headers["Retry-After"] == str(check.CAPACITY_RETRY_AFTER_SECONDS)
    assert _submit(api, _custom()).status_code == 202  # a free slot: accepted


def test_r4_3_one_tenant_cannot_hold_every_slot(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two of acme's checks hold slots; acme's third is a 429 at once, while
    another tenant still gets a slot. On 0c4848f there was no per-tenant share:
    acme's third took a third slot."""
    monkeypatch.setattr(potentials, "compile_potential", helpers.slow_real_compile)
    pot = Potential(**_custom())
    held: list[BaseException | None] = []

    def hold() -> None:
        try:
            check.check_potential(pot, tenant="acme")
            held.append(None)
        except BaseException as exc:  # noqa: BLE001 - reported below
            held.append(exc)

    holders = [threading.Thread(target=hold) for _ in range(check.MAX_COMPILES_PER_TENANT)]
    for th in holders:
        th.start()
    time.sleep(1.0)  # both are compiling (each holds its slot for HOLD_SECONDS)
    try:
        t0 = time.monotonic()
        resp = _submit(api, _custom())  # acme's request, over HTTP
        assert time.monotonic() - t0 < 1.0, "a tenant over its share is refused at once"
        assert resp.status_code == 429, resp.text
        assert resp.json()["detail"]["code"] == "RATE_LIMITED"
        assert resp.headers["Retry-After"] == str(check.CAPACITY_RETRY_AFTER_SECONDS)
        check.check_potential(pot, tenant="other-tenant")  # another tenant: a free slot
    finally:
        for th in holders:
            th.join()
    assert held == [None] * check.MAX_COMPILES_PER_TENANT
    assert check._TENANT_ACTIVE == {}


def test_r4_3_capacity_refusals_are_not_config_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    """validate_config (start_run, MCP) passes a capacity refusal up (503/429);
    it does not report the config as invalid."""
    from ucgle_f1.m8_agent.tools import simulator

    monkeypatch.setattr(check, "_SLOTS", threading.BoundedSemaphore(1))
    monkeypatch.setattr(check, "CUSTOM_COMPILE_WAIT_SECONDS", 0.2, raising=False)
    base = RunConfig.model_validate({**json.loads(RUN_FIXTURE.read_text())["config"], "precision": "fast"})
    cfg = base.model_copy(update={"potential": Potential(**_custom())})
    assert check._SLOTS.acquire(timeout=1)
    try:
        with pytest.raises(check.CompileCapacityError) as refused:
            simulator.validate_config(cfg)
    finally:
        check._SLOTS.release()
    assert refused.value.code == "UNAVAILABLE"
    assert simulator.validate_config(cfg).valid


# ── R4-4: the child's memory and priority, and parameter names ───────


def _child_refusal(monkeypatch: pytest.MonkeyPatch, fn: Any) -> str:
    monkeypatch.setattr(potentials, "compile_potential", fn)
    with pytest.raises(ValueError) as refused:
        check.check_potential(Potential(**_custom()))
    return str(refused.value)


def test_r4_4_compile_child_has_an_address_space_cap_and_a_lower_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    msg = _child_refusal(monkeypatch, helpers.report_memory_and_priority)
    found = re.search(r"as=\((-?\d+), (-?\d+)\) vmsize=(\d+) nice=(\d+)", msg)
    assert found, msg
    soft, hard, vmsize, nice = (int(x) for x in found.groups())
    assert soft == hard and soft != -1, msg  # RLIM_INFINITY is -1
    assert vmsize < soft <= vmsize + check.COMPILE_ADDRESS_SPACE_HEADROOM_BYTES, msg
    assert nice == min(19, os.nice(0) + check.COMPILE_NICENESS), msg


def test_r4_4_a_memory_bomb_in_the_child_is_refused_quickly(monkeypatch: pytest.MonkeyPatch) -> None:
    t0 = time.monotonic()
    msg = _child_refusal(monkeypatch, helpers.allocate_compile)
    assert "MemoryError" in msg, msg
    assert time.monotonic() - t0 < 8.0


@pytest.mark.parametrize("name", [
    "a:9999999", "x:3", "a b", "x,y", "1a", "lambda", "a-b", "", "phi", "ｍ", "a" * 65,
])
def test_r4_4_custom_parameter_names_must_be_identifiers(name: str) -> None:
    """On 0c4848f 'a:9999999' reached sympy.symbols (ten million Symbols, 11 s and
    ~400 MB per request in the child) and 'a b' a confusing 'missing ['(a, b)']'."""
    t0 = time.monotonic()
    with pytest.raises(ValidationError) as refused:
        Potential(kind="custom", params={"phi0": 1.0, name: 1.0}, customPython="phi**2")
    assert time.monotonic() - t0 < 0.5
    text = str(refused.value)
    assert ("must be identifiers" in text) or ("'phi' is the field" in text), text


@pytest.mark.parametrize("name", ["m", "V0", "f_a", "_x", "Lambda4", "α", "lam2", "a" * 64])
def test_r4_4_identifier_parameter_names_are_accepted(name: str) -> None:
    pot = Potential(kind="custom", params={"phi0": 1.0, name: 2.0}, customPython=f"{name}*phi**2")
    model = compile_potential(pot)
    args = [dict(pot.params)[n] for n in model.param_names]
    assert float(model.V(3.0, *args)) == pytest.approx(18.0)


def test_r4_4_compile_never_parses_a_parameter_name_as_a_range() -> None:
    """Defence in depth below the model: one Symbol per name, at once."""
    pot = EnginePotential.model_construct(
        kind="custom", params={"a:9999999": 1.0, "phi0": 1.0}, customPython="phi**2",
    )
    t0 = time.monotonic()
    model = compile_potential(pot)
    assert time.monotonic() - t0 < 2.0
    assert model.param_names == ("a:9999999", "phi0")


def test_r4_4_too_many_custom_parameters_are_refused() -> None:
    params = {f"p{i}": 1.0 for i in range(65)}
    with pytest.raises(ValidationError, match="at most 64 parameters"):
        Potential(kind="custom", params=params, customPython="phi**2")


# ── R4-5: the scan's caps and its approval order ─────────────────────


def _base() -> RunConfig:
    return RunConfig.model_validate({**json.loads(RUN_FIXTURE.read_text())["config"], "precision": "fast"})


def test_r4_5_scan_spec_caps_axes_points_and_cells() -> None:
    base = _base()
    with pytest.raises(ValidationError):
        ScanAxis(name="xi", path="couplings.xi", min=1e-3, max=1e-2, points=10**6)
    with pytest.raises(ValidationError):
        ScanAxis(name="xi", path="couplings.xi", min=1e-3, max=1e-2, points=0)
    axis = {"name": "xi", "path": "couplings.xi", "min": 1e-3, "max": 1e-2, "points": 10}
    with pytest.raises(ValidationError, match="at most 256 cells"):
        ScanSpec(base=base, axes=[ScanAxis(**axis)] * 3)  # 1000 cells
    with pytest.raises(ValidationError):
        ScanSpec(base=base, axes=[ScanAxis(**{**axis, "points": 1})] * 5)  # 5 axes
    nine = {**axis, "points": 9, "log": True}
    assert len(ScanSpec(base=base, axes=[ScanAxis(**nine), ScanAxis(**nine)]).axes) == 2  # the agent's 81


async def test_r4_5_a_bogus_token_is_refused_before_any_cell_is_validated(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On 0c4848f the scan validated (and compiled) every distinct cell first."""
    from ucgle_f1.m8_agent.tools import simulator

    calls: list[str] = []
    real = simulator.check_potential
    monkeypatch.setattr(simulator, "check_potential", lambda pot, **kw: calls.append(pot.kind) or real(pot, **kw))
    base = _base().model_copy(update={"potential": Potential(**_custom())})
    spec = ScanSpec(base=base, axes=[
        ScanAxis(name="m", path="potential.params.m", min=1e-7, max=1e-5, points=16, log=True),
        ScanAxis(name="xi", path="couplings.xi", min=1e-3, max=1e-2, points=16),
    ])  # 256 cells, 16 distinct custom potentials
    t0 = time.monotonic()
    with pytest.raises(ServiceError) as refused:
        await simulator.scan_parameters(spec, "appr_not-a-token", tenant="acme")
    assert refused.value.code == "APPROVAL_REQUIRED"
    assert time.monotonic() - t0 < 1.0 and calls == [], (time.monotonic() - t0, len(calls))


async def test_r4_5_a_valid_token_survives_a_refused_scan_and_is_spent_by_one_that_runs(
    api: dict[str, Any],
) -> None:
    from ucgle_f1.m8_agent.memory import get_store
    from ucgle_f1.m8_agent.tools.simulator import scan_parameters

    store = get_store()
    token = store.issue_approval(["scan_parameters"], 600, tenant="acme").tokenId
    assert store.approval_is_valid(token, "scan_parameters", tenant="acme")
    assert not store.approval_is_valid(token, "start_run", tenant="acme")
    assert not store.approval_is_valid(token, "scan_parameters", tenant="other-tenant")
    bad = ScanSpec(base=_base(), axes=[ScanAxis(name="nope", path="couplings.nope", min=1.0, max=1.0, points=1)])
    with pytest.raises(ServiceError, match="scan cell"):
        await scan_parameters(bad, token, tenant="acme")
    assert store.approval_is_valid(token, "scan_parameters", tenant="acme")  # not spent
    kk = Potential(kind="natural", params={"f_a": 8.7, "Lambda": 0.0071154324599829784})
    axis = ScanAxis(name="xi", path="couplings.xi", min=1.0e-3, max=1.0e-3, points=1)
    result = await scan_parameters(ScanSpec(base=_base().model_copy(update={"potential": kk}), axes=[axis]),
                                   token, tenant="acme")
    assert len(result.cells) == 1
    assert not store.approval_is_valid(token, "scan_parameters", tenant="acme")  # spent


def test_r4_5_a_couplings_axis_compiles_the_potential_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 0c4848f the dedupe key was the whole config: one compile per xi value."""
    from ucgle_f1.m8_agent.tools import simulator

    calls: list[str] = []
    real = simulator.check_potential
    monkeypatch.setattr(simulator, "check_potential", lambda pot, **kw: calls.append(pot.kind) or real(pot, **kw))
    base = _base().model_copy(update={"potential": Potential(**_custom())})
    spec = ScanSpec(base=base, axes=[ScanAxis(name="xi", path="couplings.xi", min=1e-3, max=1e-2, points=3)])
    cells = simulator._scan_cells(spec)
    assert len(cells) == 3
    assert calls == ["custom"]
