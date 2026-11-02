"""W1-PARAMS: every potential config the frontend can send is accepted by the
API request model and compiles in M2's units with every parameter bound.

The configs, each read from the file the frontend itself uses:

- the Configurator's defaults, ``src/lib/configDefaults.json``, which
  ``src/lib/configDefaults.ts`` imports for ``defaultsForPotential`` (every
  kind) and ``kawaiKimDefaults()`` (the V2 baseline, the form's initial value);
- ``public/fixtures/benchmarks.json`` ("Load from benchmark");
- the ``config`` of every ``public/fixtures/runs/*.json``;
- every ``public/fixtures/artifacts/*/config.yaml``.

"Accepted" means: ``CosmologyManifest`` (the run route's request model)
validates it, ``LeptogenesisSimulation.validate_problem`` (the route's
submit-time check) passes, and the agent's ``RunConfig`` validates it too.
"Compiles" means: ``compile_potential`` on ``Potential.engine()`` (the one
GeV → M_Pl conversion) succeeds and ``potential_args`` binds every parameter.

On 040bc36 the natural configs ({f, Lambda4}) failed with "potential
parameters missing: ['f_a', 'Lambda']", failing-run's hilltop ({phi0, Lambda})
with "['V0', 'mu']", and the hilltop default had no V0.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from omegaconf import OmegaConf

from ucgle_f1.adapters.cosmology_manifest import CosmologyManifest, to_run_config
from ucgle_f1.adapters.qcompass import LeptogenesisSimulation
from ucgle_f1.domain import RunConfig
from ucgle_f1.m2_scalar import compile_potential
from ucgle_f1.m2_scalar.trajectory import potential_args
from ucgle_f1.m7_infer.hydra_cfg import load_config
from ucgle_f1.m8_agent.auth import get_auth_store
from ucgle_f1.m8_agent.server import build_app

REPO = Path(__file__).resolve().parents[2]
DEFAULTS_JSON = REPO / "src" / "lib" / "configDefaults.json"
DEFAULTS_TS = REPO / "src" / "lib" / "configDefaults.ts"
FIXTURES = REPO / "public" / "fixtures"


def _defaults() -> dict[str, Any]:
    return json.loads(DEFAULTS_JSON.read_text(encoding="utf-8"))


def _v2(potential: dict[str, Any]) -> dict[str, Any]:
    """A RunConfig as the Configurator builds it (kawaiKimDefaults with ``potential``)."""
    v2 = _defaults()["v2"]
    return {"potential": potential, "couplings": dict(v2["couplings"]),
            "reheating": dict(v2["reheating"]), "precision": v2["precision"]}


def _custom_python() -> str:
    m = re.search(r"export const DEFAULT_CUSTOM_PYTHON = `(.*?)`;", DEFAULTS_TS.read_text(), re.S)
    assert m, "DEFAULT_CUSTOM_PYTHON not found in configDefaults.ts"
    return m.group(1)


def _frontend_configs() -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for kind, params in _defaults()["potentialParams"].items():
        if kind != "custom":  # custom: test_configurator_custom_snippet_* below
            out.append((f"defaultsForPotential({kind})", _v2({"kind": kind, "params": dict(params)})))
    out.append(("kawaiKimDefaults()", _v2({"kind": "natural",
                                           "params": dict(_defaults()["potentialParams"]["natural"])})))
    for b in json.loads((FIXTURES / "benchmarks.json").read_text())["benchmarks"]:
        out.append((f"benchmarks.json:{b['id']}", b["config"]))
    for path in sorted((FIXTURES / "runs").glob("*.json")):
        out.append((f"runs/{path.name}", json.loads(path.read_text())["config"]))
    for path in sorted((FIXTURES / "artifacts").glob("*/config.yaml")):
        cfg = OmegaConf.to_container(OmegaConf.load(path), resolve=True)  # hydra_cfg's loader
        out.append((f"artifacts/{path.parent.name}/config.yaml", cfg))  # type: ignore[arg-type]
    return out


CONFIGS = _frontend_configs()


def test_configurator_defaults_come_from_the_json() -> None:
    """One source of truth: the TS builds both defaults from configDefaults.json."""
    ts = DEFAULTS_TS.read_text(encoding="utf-8")
    assert 'import defaults from "./configDefaults.json";' in ts
    assert "return { ...defaults.potentialParams[kind] };" in ts
    assert 'params: defaultsForPotential("natural")' in ts
    assert "couplings: { ...defaults.v2.couplings }" in ts
    assert "reheating: { ...defaults.v2.reheating }" in ts
    assert set(_defaults()["potentialParams"]) == {"starobinsky", "natural", "hilltop", "custom"}
    # R19: the natural default the Configurator displays is unchanged.
    assert _defaults()["potentialParams"]["natural"] == {"f": 7e16, "Lambda4": 2.5e-7}


def test_every_frontend_config_source_is_covered() -> None:
    ids = [i for i, _ in CONFIGS]
    assert {"defaultsForPotential(starobinsky)", "defaultsForPotential(natural)",
            "defaultsForPotential(hilltop)", "kawaiKimDefaults()"} <= set(ids)
    assert sum(i.startswith("benchmarks.json:") for i in ids) == 4
    assert sum(i.startswith("runs/") for i in ids) == len(list((FIXTURES / "runs").glob("*.json")))
    assert sum(i.startswith("artifacts/") for i in ids) == 3


@pytest.mark.parametrize(("source", "config"), CONFIGS, ids=[i for i, _ in CONFIGS])
def test_frontend_config_is_accepted_and_compiles_with_every_parameter_bound(
    source: str, config: dict[str, Any],
) -> None:
    manifest = CosmologyManifest.model_validate(config)  # the run route's request model
    LeptogenesisSimulation.validate_problem(config)  # the route's submit-time check
    RunConfig.model_validate(config)  # the agent's routes take the same shape
    potential = to_run_config(manifest).potential.engine()
    model = compile_potential(potential)
    args = potential_args(model, dict(potential.params))
    assert len(args) == len(model.param_names) > 0, source
    assert all(a > 0 for a in args), (source, dict(zip(model.param_names, args)))


@pytest.mark.parametrize("path", sorted((FIXTURES / "artifacts").glob("*/config.yaml")),
                         ids=lambda p: p.parent.name)
def test_artifact_config_yaml_loads_through_the_backend_loader(path: Path) -> None:
    cfg = load_config(path)
    potential_args(compile_potential(cfg.potential.engine()), dict(cfg.potential.engine().params))


def test_configurator_custom_snippet_is_refused_with_a_clear_422_message() -> None:
    """The Configurator's custom default is a ``def V(psi)`` function (its
    linter requires one); the backend compiles one expression in phi. This is
    a source-format mismatch, not a parameter one (LEDGER, W1-PARAMS gap):
    the API refuses it at submit with a message saying what it takes."""
    config = _v2({"kind": "custom", "params": dict(_defaults()["potentialParams"]["custom"]),
                  "customPython": _custom_python()})
    CosmologyManifest.model_validate(config)  # the params ({}) are fine
    with pytest.raises(ValueError, match="customPython must be one expression in phi"):
        LeptogenesisSimulation.validate_problem(config)


# ── The run route: 202 for the V2 default, 422 for ambiguous params ───


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED-ON-JAMES:DATABASE_URL (no test Postgres)")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("UCGLE_F1_ARTIFACTS", str(tmp_path / "artifacts"))
    monkeypatch.delenv("QCOMPASS_DEV_ALLOW_ANONYMOUS", raising=False)
    tok = get_auth_store().issue("acme", scopes=["read", "run"])
    with psycopg.connect(_url(), autocommit=True) as conn:
        conn.execute("update public.tenants set subscription_tier = 'enterprise' where slug = 'acme'")
    headers = {"Authorization": f"Bearer {tok.token_id}", "X-QCompass-Tenant": "acme"}
    return TestClient(build_app()), headers


def _submit(client: TestClient, headers: dict[str, str], problem: dict[str, Any]) -> Any:
    body = {"manifest": {"domain": "cosmology", "version": "1.0", "problem": problem,
                         "backend_request": {"kind": "classical"}}}
    return client.post("/api/qcompass/domains/cosmology.ucglef1/runs", json=body, headers=headers)


def test_the_ui_v2_default_is_queued(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    config = _v2({"kind": "natural", "params": dict(_defaults()["potentialParams"]["natural"])})
    resp = _submit(client, headers, config)
    assert resp.status_code == 202, resp.json()


@pytest.mark.parametrize(("params", "message"), [
    ({"f": 7e16, "Lambda4": 2.5e-7, "f_a": 0.0287}, "ambiguous parameters"),
    ({"f": 7e16, "Lambda": 0.02}, "ambiguous parameters"),
    ({"f": -7e16, "Lambda4": 2.5e-7}, "f [GeV] must be positive"),
    ({"f": 7e16, "Lambda4": 0.0}, "Lambda4 [M_Pl^4] must be positive"),
    ({"f": 7e16}, "missing Lambda4 [M_Pl^4]"),
    ({"f": 7e16, "Lambda4": 2.5e-7, "Lambda5": 1.0}, "unknown parameter(s) ['Lambda5']"),
], ids=["both-forms", "mixed-names", "negative-f", "zero-Lambda4", "incomplete", "unknown"])
def test_bad_natural_params_are_422_invalid_input_with_a_clear_message(
    api, params: dict[str, float], message: str,  # type: ignore[no-untyped-def]
) -> None:
    client, headers = api
    resp = _submit(client, headers, _v2({"kind": "natural", "params": params}))
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_INPUT"
    assert message in detail["message"], detail["message"]
    assert "natural potential" in detail["message"]


def test_hilltop_without_v0_is_422_never_a_made_up_v0(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    resp = _submit(client, headers, _v2({"kind": "hilltop", "params": {"mu": 1e16, "p": 4}}))
    assert resp.status_code == 422
    assert "missing V0 [M_Pl^4]" in resp.json()["detail"]["message"]


def test_agent_run_route_answers_a_refused_config_with_422(api) -> None:  # type: ignore[no-untyped-def]
    client, headers = api
    config = _v2({"kind": "natural", "params": {"f": 7e16, "Lambda4": 2.5e-7, "f_a": 1.0}})
    resp = client.post("/api/runs", json={"config": config, "approval_token": "x"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_INPUT"
    assert "ambiguous parameters" in resp.json()["detail"]["message"]
