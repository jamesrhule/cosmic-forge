"""W1 API3: custom potentials (JAMES DECISION 17), the expression caps, the
bounded submit-time compile, submit-time refusal of potentials the worker
could not run, and the scan's validate-before-spend order.

Item IDs match ``docs/build/lanes/W1-api3.md`` and
``docs/build/evidence/W1-api3.md``. The regression tests drive HTTP, or
functions that existed on 15e4e3c (``_custom_expr``, ``compile_potential``,
``scan_parameters``, the approval store), so they also run against the base,
where they fail on the bug itself.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import psycopg
import pytest
import sympy as sp
from fastapi.testclient import TestClient

import api3_compile_helpers as helpers
from ucgle_f1.domain import Potential, RunConfig, ScanAxis, ScanSpec, ServiceError
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.potentials import _custom_expr
from ucgle_f1.m8_agent.auth import get_auth_store
from ucgle_f1.m8_agent.server import build_app

REPO = Path(__file__).resolve().parents[2]
RUN_FIXTURE = Path(__file__).resolve().parent / "data" / "gate1_run_result.json"
CANONICAL = "customPython must be one expression in phi"
DEF_FORM = "def V(<name>): return <expression>"


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


def _v2(potential: dict[str, Any]) -> dict[str, Any]:
    """A RunConfig as the Configurator builds it (its V2 couplings and reheating)."""
    v2 = json.loads((REPO / "src" / "lib" / "configDefaults.json").read_text())["v2"]
    return {"potential": potential, "couplings": dict(v2["couplings"]),
            "reheating": dict(v2["reheating"]), "precision": v2["precision"]}


def _custom(source: str, **params: float) -> dict[str, Any]:
    return {"kind": "custom", "params": {"m": 1.0e-6, "phi0": 15.0, **params}, "customPython": source}


def _submit(api: dict[str, Any], potential: dict[str, Any]) -> Any:
    return api["client"].post("/api/qcompass/domains/cosmology.ucglef1/runs",
                              json={"manifest": _v2(potential)}, headers=api["headers"])


def _bounded_post(api: dict[str, Any], potential: dict[str, Any], limit: float) -> tuple[Any, float, float]:
    """Submit on a thread; return (response or None, seconds, /healthz seconds meanwhile)."""
    out: dict[str, Any] = {}

    def post() -> None:
        t0 = time.monotonic()
        out["resp"] = _submit(api, potential)
        out["seconds"] = time.monotonic() - t0

    th = threading.Thread(target=post, daemon=True)
    th.start()
    time.sleep(0.5)
    t0 = time.monotonic()
    health = api["client"].get("/healthz")
    healthz = time.monotonic() - t0
    assert health.status_code == 200
    th.join(limit)
    return out.get("resp"), out.get("seconds", float("inf")), healthz


# ── D17: the custom-potential snippet shape ───────────────────────────

_PHI = sp.Symbol("phi", real=True)
_ACCEPTED = {
    "canonical-expression": "m**2*phi**2/2",
    "def-V-psi": "def V(psi):\n    return m**2*psi**2/2",
    "def-V-phi": "def V(phi):\n    return m**2*phi**2/2",
    "docstring-first": 'def V(psi):\n    """A quadratic potential."""\n    return m**2*psi**2/2',
    "comments": "# my potential\ndef V(x):  # x is the inflaton\n    return m**2*x**2/2  # quadratic\n",
}
_MAIN_DEFAULT = (  # main's Configurator default (src/lib/configDefaults.ts on 3d2355a)
    "# Custom inflaton potential V(psi).\n"
    "def V(psi):\n"
    "    M = 1.3e-5\n"
    "    return 0.75 * M**2 * (1.0 - 2.718281828 ** (-0.8164965809 * psi)) ** 2\n"
)
_REFUSED = {
    "multiple-statements": ("def V(psi):\n    return psi**2\n    return psi", "not Return, Return"),
    "assignment": (_MAIN_DEFAULT, "not Assign, Return"),
    "if": ("def V(psi):\n    if psi > 0:\n        return psi\n    return -psi", "not If, Return"),
    "loop": ("def V(psi):\n    for _ in range(3):\n        return psi", "not For"),
    "lambda-assignment": ("V = lambda psi: psi**2", "not Assign"),
    "lambda-expression": ("lambda psi: psi**2", "a lambda is not accepted"),
    "return-lambda": ("def V(psi):\n    return lambda x: x", "a lambda is not accepted"),
    "two-params": ("def V(psi, m):\n    return m*psi**2", "exactly one positional parameter, not 2"),
    "default-arg": ("def V(psi=1.0):\n    return psi**2", "takes no default value"),
    "decorator": ("@staticmethod\ndef V(psi):\n    return psi**2", "takes no decorators"),
    "nested-def": ("def V(psi):\n    def W(x):\n        return x\n    return W(psi)", "not FunctionDef, Return"),
    "no-return": ("def V(psi):\n    m**2*psi**2/2", "V has no 'return <expression>'"),
    "bare-return": ("def V(psi):\n    return", "exactly one 'return <expression>'"),
    "wrong-name": ("def U(psi):\n    return psi**2", "must be named V, not 'U'"),
    "phi-collision": ("def V(psi):\n    return psi**2 + phi", "uses the name 'phi' besides its parameter 'psi'"),
    "annotations": ("def V(psi: float) -> float:\n    return psi**2", "takes no annotations"),
    "varargs": ("def V(*psi):\n    return psi", "exactly one positional parameter (no *args"),
    "keyword-only": ("def V(*, psi):\n    return psi", "exactly one positional parameter (no *args"),
    "async-def": ("async def V(psi):\n    return psi", "not AsyncFunctionDef"),
    "def-and-a-call": ("def V(psi):\n    return psi**2\nV(1)", "not FunctionDef, Expr"),
    "syntax-error": ("def V(psi):\nreturn psi", "it does not parse"),
}


@pytest.mark.parametrize("case", list(_ACCEPTED), ids=list(_ACCEPTED))
def test_d17_accepted_snippets_compile_to_the_canonical_expression(case: str) -> None:
    canonical = compile_potential(Potential(**_custom(_ACCEPTED["canonical-expression"])))
    model = compile_potential(Potential(**_custom(_ACCEPTED[case])))
    assert sp.srepr(model.symbolic_V) == sp.srepr(canonical.symbolic_V)
    assert model.symbolic_V.free_symbols == {_PHI, sp.Symbol("m", real=True)}
    assert float(model.V(2.0, 1.0e-6, 15.0)) == pytest.approx(2.0e-12, rel=1e-12)


@pytest.mark.parametrize("case", list(_REFUSED), ids=list(_REFUSED))
def test_d17_any_other_snippet_is_refused_naming_the_canonical_form(case: str) -> None:
    source, why = _REFUSED[case]
    with pytest.raises(ValueError) as refused:
        compile_potential(Potential(**_custom(source)))
    msg = str(refused.value)
    assert CANONICAL in msg and DEF_FORM in msg, msg
    assert why in msg, msg


def test_d17_the_route_takes_def_v_and_answers_any_other_body_with_a_422_naming_the_canonical_form(
    api: dict[str, Any],
) -> None:
    ok = _submit(api, _custom(_ACCEPTED["def-V-psi"]))
    assert ok.status_code == 202, ok.text
    refused = _submit(api, _custom(_MAIN_DEFAULT))
    assert refused.status_code == 422, refused.text
    detail = refused.json()["detail"]
    assert detail["code"] == "INVALID_INPUT"
    assert CANONICAL in detail["message"] and DEF_FORM in detail["message"]
    # The agent's validate_config says the same, on the snippet's path.
    for source, valid in ((_ACCEPTED["def-V-psi"], True), (_MAIN_DEFAULT, False)):
        cfg = {**_v2(_custom(source)), "agent": {"conversationId": "c", "hypothesisId": "h"}}
        out = api["client"].post("/mcp/tools/validate_config", json={"config": cfg},
                                 headers=api["headers"]).json()["output"]
        assert out["valid"] is valid, out
        if not valid:
            assert [d["path"] for d in out["diagnostics"] if d["severity"] == "error"] == [
                "potential.customPython",
            ]


# ── c3-expr-caps (partial): Float magnitudes, complex arguments, float64 ──

_FLOAT_BOMBS = [
    # The round-2 WORKER verifier's payloads (scratch-verify-WORKER/cases*.txt).
    "sin(exp(1e30))", "sin(sinh(1e30))", "tanh(sin(exp(1e30)))", "sin(exp(exp(30.0)))",
    "sin(exp(2e6))", "sin(exp(1e6))", "sin(exp(1e7))", "cos(cosh(1e3*1e3))",
    "sin(9**(1/(1.0000001-1.0)))", "phi**2 + cos(exp(exp(30.0)))",
    "exp(1e30)", "sinh(1e30)", "exp(1e30)*phi**2", "sqrt(exp(1e30))",
    "sin(" + "*".join(["1e30"] * 30) + ")",
    # Found by this lane: an imaginary argument turns sin/cos into sinh/cosh,
    # and a float literal below Python's range is 0.0 to Python, not to sympy.
    "sin(cos(1e6*sqrt(-1)))", "sin(sin(1e3*sqrt(-1.0)*1e3))", "sin(1e30*sqrt(-1.0))",
    "exp(1/1e-1000)", "sin(1/1e-100000)",
]


@pytest.mark.parametrize("source", _FLOAT_BOMBS)
def test_c3_float_bombs_are_refused_quickly(source: str) -> None:
    code = (
        "import sys\n"
        "from ucgle_f1.m2_scalar.potentials import _custom_expr\n"
        "try:\n"
        "    _custom_expr(sys.argv[1])\n"
        "except ValueError as exc:\n"
        "    print('rejected:', exc)\n"
        "else:\n"
        "    print('accepted')\n"
    )
    try:
        out = subprocess.run(
            [sys.executable, "-c", code, source], capture_output=True, text=True, timeout=20, check=True,
        ).stdout
    except subprocess.TimeoutExpired:
        pytest.fail(f"parsing {source!r} did not finish: sympy evaluated an unbounded Float")
    assert out.startswith("rejected: custom potential:"), f"{source!r}: {out}"


_REAL_POTENTIALS = [
    "m**2*phi**2/2", "L**4*(1 - cos(phi/f_a))", "Rational(3, 4)*M**2*(1 - exp(-sqrt(Rational(2, 3))*phi))**2",
    "1e-10*phi**4 + 1.3e-5", "V0*(1 - (phi/mu)**4)", "tanh(phi/sqrt(6))**2", "pi*phi**2 + log(cosh(phi))",
    "exp(-2*log(phi))", "phi**(1/2) - 2.5e-3*phi", "V0*phi**2/(1.0 + phi**2)", "1/(1.0 + phi**2)",
    "V0*(1 - exp(-sqrt(2/3)*phi))**2", "m**2*phi**2/2*(1 + 0.1*sin(phi/0.01))", "V0*(1 - 1/cosh(phi))",
    "sin(phi)**2", "1/sin(phi)", "tanh(phi)**-2", "V0*log(1 + phi**2)", "exp(700*phi)", "V0*exp(-phi/0.01)",
    "sqrt(1.0 + phi**2) - 1.0", "0.75*1.3e-5**2*(1.0 - 2.718281828**(-0.8164965809*phi))**2",
    "1/(1.0 + 0.5*phi + 0.25*phi**2 + 0.125*phi**3 + 0.0625*phi**4 + 0.03*phi**5 + 0.01*phi**6)",
    "phi*sin(" + "*".join(["1e30"] * 10) + ")",
]


@pytest.mark.parametrize("source", _REAL_POTENTIALS)
def test_c3_float_caps_keep_real_potentials(source: str) -> None:
    names = {n: sp.Symbol(n, real=True) for n in ("m", "L", "f_a", "M", "V0", "mu")}
    expr = _custom_expr(source, {"phi": _PHI, **names})
    assert _PHI in expr.free_symbols


def test_c3_a_float_bomb_at_submit_is_a_quick_422_and_the_api_stays_responsive(api: dict[str, Any]) -> None:
    """On 15e4e3c the request never answered (sympy evaluating sin(exp(1e30)) in
    an API thread) and /healthz on the same process slowed to seconds."""
    resp, seconds, healthz = _bounded_post(api, _custom("phi**2 + sin(exp(1e30))"), 30.0)
    assert resp is not None, "no answer within 30 s: the API evaluated an unbounded Float"
    assert resp.status_code == 422 and resp.json()["detail"]["code"] == "INVALID_INPUT", resp.text
    assert "float64" in resp.json()["detail"]["message"]
    assert seconds < 15.0 and healthz < 1.0, (seconds, healthz)


# ── NEW MEDIUM: the submit-time compile is bounded in time and CPU ────


def _slow_compile(monkeypatch: pytest.MonkeyPatch, fn: Any, limit: float) -> None:
    """Make the compile step ``fn``: where the base tree's validate_problem called it
    (in the API process), and where check_potential hands it to its child."""
    monkeypatch.setattr("ucgle_f1.m2_scalar.potentials.compile_potential", fn)
    monkeypatch.setattr("ucgle_f1.adapters.qcompass.compile_potential", fn, raising=False)
    monkeypatch.setattr("ucgle_f1.m2_scalar.check.CUSTOM_COMPILE_TIMEOUT_SECONDS", limit, raising=False)


def test_submit_compile_of_a_custom_potential_is_stopped_at_its_time_limit(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On 15e4e3c validate_problem compiled in the API process with no limit: a
    slow compile held the request (and a core) until it finished."""
    _slow_compile(monkeypatch, helpers.spin_compile, 2.0)
    resp, seconds, healthz = _bounded_post(api, _custom("m**2*phi**2/2"), 30.0)
    assert resp is not None, "no answer within 30 s: the compile ran in the API process without a limit"
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_INPUT"
    assert "did not finish within 2 s" in detail["message"]
    assert seconds < 15.0 and healthz < 1.0, (seconds, healthz)
    assert multiprocessing.active_children() == [], "the compile process was stopped"


def test_submit_compile_child_is_cpu_limited_and_dies_with_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1.m2_scalar import check

    _slow_compile(monkeypatch, helpers.report_limits, 10.0)
    with pytest.raises(ValueError) as refused:
        check.check_potential(Potential(**_custom("m**2*phi**2/2")))
    msg = str(refused.value)
    assert "cpu=(15, 20)" in msg, msg  # ceil(10 s) + 5 s slack, hard limit 5 s above
    assert f"ppid={os.getpid()}" in msg and f"pid={os.getpid()} " not in msg, msg


def test_submit_compile_waits_for_a_free_slot_within_its_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ucgle_f1.m2_scalar import check

    monkeypatch.setattr(check, "_SLOTS", threading.BoundedSemaphore(1))
    assert check._SLOTS.acquire(timeout=1)
    try:
        with pytest.raises(ValueError, match="server is compiling other custom potentials"):
            check.check_potential(Potential(**_custom("m**2*phi**2/2")), timeout=0.5)
    finally:
        check._SLOTS.release()
    check.check_potential(Potential(**_custom("m**2*phi**2/2")))  # a free slot: accepted


# ── Critic MEDIUM: refused at submit, never a 500 ─────────────────────


@pytest.mark.parametrize(("potential", "why"), [
    (_custom("phi**2", phi=1.0), "'phi' is the field, not a parameter"),
    (_custom("log(0)*phi"), "not finite"),
    (_custom("phi**2/0"), "not finite"),
], ids=["phi-as-a-parameter", "log-0", "divide-by-0"])
def test_critic_compile_errors_are_422_not_500(
    api: dict[str, Any], potential: dict[str, Any], why: str,
) -> None:
    """On 15e4e3c these raised SyntaxError (lambdify: duplicate argument 'phi') or
    KeyError('ComplexInfinity') in validate_problem, which caught only ValueError."""
    resp = _submit(api, potential)
    assert resp.status_code == 422, (resp.status_code, resp.text[:300])
    assert resp.json()["detail"]["code"] == "INVALID_INPUT"
    assert why in resp.json()["detail"]["message"]


def _start(api: dict[str, Any], config: dict[str, Any], token: str) -> Any:
    return api["client"].post("/api/runs", json={"config": config, "approval_token": token},
                              headers=api["headers"])


def test_critic_api_runs_refuses_an_incomplete_potential_before_spending_the_token(
    api: dict[str, Any],
) -> None:
    """On 15e4e3c POST /api/runs (start_run) accepted hilltop {mu, p} without V0
    and a custom potential without phi0; each failed later in the worker."""
    from ucgle_f1.m8_agent.memory import get_store

    client, headers = api["client"], api["headers"]
    token = client.post("/api/approvals", json={"scopes": ["start_run"]}, headers=headers).json()["tokenId"]
    hyp = get_store().record_hypothesis("c_api3", "api3 hypothesis", tenant="acme").hypothesisId
    agent = {"conversationId": "c_api3", "hypothesisId": hyp}
    base = json.loads(RUN_FIXTURE.read_text())["config"]
    for potential, why in (
        ({"kind": "hilltop", "params": {"mu": 1.0e16, "p": 4}}, "missing V0"),
        ({"kind": "custom", "params": {"m": 1.0e-6}, "customPython": "m**2*phi**2/2"}, "phi0"),
        (_custom("phi**2 + sin(exp(1e30))"), "float64"),
    ):
        resp = _start(api, {**base, "potential": potential, "agent": agent}, token)
        assert resp.status_code == 422, (potential, resp.status_code, resp.text[:300])
        assert resp.json()["detail"]["code"] == "INVALID_INPUT" and why in resp.json()["detail"]["message"]
    with psycopg.connect(_url(), autocommit=True) as conn:
        assert conn.execute("select count(*) from public.runs").fetchone() == (0,)
    resp = _start(api, {**base, "agent": agent}, token)
    assert resp.status_code == 200, "the refused requests did not spend the token"


def test_critic_validate_config_reports_missing_parameters_and_compile_failures(api: dict[str, Any]) -> None:
    """On 15e4e3c validate_config answered valid=True for each of these."""
    agent = {"conversationId": "c", "hypothesisId": "h"}
    for potential, path, why in (
        ({"kind": "hilltop", "params": {"mu": 1.0e16, "p": 4}}, "potential.params", "missing V0"),
        (_custom("m**2*phi**2/2 + k*phi"), "potential.customPython", "unbound parameter(s) ['k']"),
        ({"kind": "custom", "params": {"m": 1.0e-6}, "customPython": "m**2*phi**2/2"},
         "potential.customPython", "phi0"),
    ):
        out = api["client"].post("/mcp/tools/validate_config", json={"config": {**_v2(potential), "agent": agent}},
                                 headers=api["headers"]).json()["output"]
        assert out["valid"] is False, (potential, out)
        errors = [d for d in out["diagnostics"] if d["severity"] == "error"]
        assert [d["path"] for d in errors] == [path] and why in errors[0]["message"], errors


def test_critic_mcp_validate_config_answers_a_refused_config_with_diagnostics(api: dict[str, Any]) -> None:
    """On 15e4e3c a config domain.Potential refuses (here: two forms of natural
    parameters at once) made /mcp/tools/validate_config a 500."""
    cfg = {**_v2({"kind": "natural", "params": {"f": 7e16, "f_a": 8.7, "Lambda": 0.007}}),
           "agent": {"conversationId": "c", "hypothesisId": "h"}}
    resp = api["client"].post("/mcp/tools/validate_config", json={"config": cfg}, headers=api["headers"])
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    out = resp.json()["output"]
    assert out["valid"] is False and out["normalized"] is None
    assert any(d["path"].startswith("potential") and "ambiguous" in d["message"] for d in out["diagnostics"])


# ── R2-START-ORDER residual: scan_parameters validates before spending ─


async def test_r2_scan_parameters_validates_before_spending_the_token(api: dict[str, Any]) -> None:
    """On 15e4e3c scan_parameters spent its approval first, then failed on the
    first cell (here: hilltop without V0)."""
    from ucgle_f1.m8_agent.memory import get_store
    from ucgle_f1.m8_agent.tools.simulator import scan_parameters

    store = get_store()
    base = RunConfig.model_validate({**json.loads(RUN_FIXTURE.read_text())["config"], "precision": "fast"})
    incomplete = base.model_copy(update={"potential": Potential(kind="hilltop", params={"mu": 1.0e16, "p": 4})})
    axis = ScanAxis(name="xi", path="couplings.xi", min=1.0e-3, max=1.0e-3, points=1)
    for spec in (
        ScanSpec(base=incomplete, axes=[axis]),
        ScanSpec(base=base, axes=[ScanAxis(name="nope", path="couplings.nope", min=1.0, max=1.0, points=1)]),
        ScanSpec(base=base, axes=[ScanAxis(name="xi", path="couplings.xi", min=-1.0, max=1.0, points=2,
                                           log=True)]),
    ):
        token = store.issue_approval(["scan_parameters"], 600, tenant="acme").tokenId
        with pytest.raises(Exception) as refused:  # noqa: PT011 - the base raised other types
            await scan_parameters(spec, token, tenant="acme")
        assert store.consume_approval(token, "scan_parameters", tenant="acme") is True, (
            f"the refused scan spent the token ({type(refused.value).__name__}: {refused.value})"
        )
        assert isinstance(refused.value, ServiceError) and refused.value.code == "INVALID_INPUT", refused.value
    kk = Potential(kind="natural", params={"f_a": 8.7, "Lambda": 0.0071154324599829784})
    token = store.issue_approval(["scan_parameters"], 600, tenant="acme").tokenId
    result = await scan_parameters(ScanSpec(base=base.model_copy(update={"potential": kk}), axes=[axis]),
                                   token, tenant="acme")
    assert len(result.cells) == 1
    assert store.consume_approval(token, "scan_parameters", tenant="acme") is False  # the scan spent it
