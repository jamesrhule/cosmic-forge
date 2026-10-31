"""Frontend ↔ backend endpoint contract (P4-01).

1. Every ``@endpoint`` annotation in ``src/services/**/*.ts`` has a backend
   route with the same path and method (``SSE GET`` = GET; ``WS`` = WebSocket).
2. Every run fixture under ``public/fixtures/<domain>/runs/*.json`` validates
   against the response model of ``GET /api/qcompass/domains/{domain}/runs/{id}``
   and round-trips unchanged.
3. The tenants, literature and verdict data validate against their routes'
   response models; the backend's literature copies equal the frontend's
   offline fixtures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("qcompass_core")

from fastapi.routing import APIRoute, APIWebSocketRoute
from pydantic import TypeAdapter

from ucgle_f1.m8_agent.server import build_app

REPO = Path(__file__).resolve().parents[2]
SERVICES = REPO / "src" / "services"
FIXTURES = REPO / "public" / "fixtures"
DATA = REPO / "backend" / "src" / "ucgle_f1" / "m8_agent" / "data"

_ANNOTATION = re.compile(r"@endpoint\s+(?:(SSE)\s+)?(?:(WS)\s+)?(GET|POST|PUT|PATCH|DELETE)?\s*(/\S+)")


def _norm(path: str) -> str:
    path = path.split("?", 1)[0].rstrip("/")
    return re.sub(r"\{[^}]+\}", "{}", path)


def _annotations() -> list[tuple[str, str, str]]:
    found = []
    for ts in sorted(SERVICES.rglob("*.ts")):
        for m in _ANNOTATION.finditer(ts.read_text(encoding="utf-8")):
            _sse, ws, method, path = m.groups()
            kind = "WS" if ws else (method or "GET")
            found.append((kind, _norm(path), f"{ts.relative_to(REPO)}: {m.group(0)}"))
    return found


ANNOTATIONS = _annotations()


@pytest.fixture(scope="module")
def app():
    return build_app()


def _routes(app) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for r in app.routes:
        if isinstance(r, APIRoute):
            for m in r.methods:
                out.add((m, _norm(r.path)))
        elif isinstance(r, APIWebSocketRoute):
            out.add(("WS", _norm(r.path)))
    return out


def test_annotations_were_found() -> None:
    assert len(ANNOTATIONS) >= 14, ANNOTATIONS


@pytest.mark.parametrize(("kind", "path", "where"), ANNOTATIONS, ids=[a[2].split(": ", 1)[1] for a in ANNOTATIONS])
def test_every_annotated_endpoint_has_a_route(app, kind: str, path: str, where: str) -> None:
    assert (kind, path) in _routes(app), f"no backend route for {where}"


def _response_model(app, method: str, path: str) -> Any:
    for r in app.routes:
        if isinstance(r, APIRoute) and method in r.methods and _norm(r.path) == _norm(path):
            assert r.response_model is not None, f"{method} {path} has no response_model"
            return r.response_model
    raise AssertionError(f"no route {method} {path}")


RUN_FIXTURES = sorted(FIXTURES.glob("*/runs/*.json"))


@pytest.mark.parametrize("fixture", RUN_FIXTURES, ids=[f"{p.parent.parent.name}/{p.stem}" for p in RUN_FIXTURES])
def test_run_fixture_validates_against_get_run_model(app, fixture: Path) -> None:
    model = _response_model(app, "GET", "/api/qcompass/domains/{domain}/runs/{run_id}")
    blob = json.loads(fixture.read_text(encoding="utf-8"))
    parsed = TypeAdapter(model).validate_python(blob)
    assert TypeAdapter(model).dump_python(parsed, mode="json", exclude_unset=True) == blob


def test_run_list_model_accepts_fixture_summaries(app) -> None:
    model = _response_model(app, "GET", "/api/qcompass/domains/{domain}/runs")
    summaries = []
    for fixture in RUN_FIXTURES:
        b = json.loads(fixture.read_text(encoding="utf-8"))
        summaries.append({k: b[k] for k in ("id", "label", "status", "domain", "created_at")})
    TypeAdapter(model).validate_python(summaries)


def test_tenants_fixture_matches_tenants_model(app) -> None:
    model = _response_model(app, "GET", "/api/qcompass/tenants")
    TypeAdapter(model).validate_python(json.loads((FIXTURES / "auth" / "tenants.json").read_text()))


@pytest.mark.parametrize(("route", "fixture", "data"), [
    ("/api/qcompass/literature/lattice-qcd", "lattice-qcd-references.json", "lattice-qcd.json"),
    ("/api/qcompass/literature/nuclear", "nuclear-references.json", "nuclear.json"),
])
def test_literature_backend_copy_matches_frontend_fixture(app, route: str, fixture: str, data: str) -> None:
    model = _response_model(app, "GET", route)
    front = json.loads((FIXTURES / "literature" / fixture).read_text())
    back = json.loads((DATA / "literature" / data).read_text())
    assert back == front, f"{data} drifted from public/fixtures/literature/{fixture}"
    TypeAdapter(model).validate_python(back)


def test_verdict_data_matches_verdict_model(app) -> None:
    import yaml

    model = _response_model(app, "GET", "/api/verdict/{verdict_id}")
    for path in sorted((DATA / "verdicts").glob("*.yaml")):
        TypeAdapter(model).validate_python(yaml.safe_load(path.read_text()))


def test_no_verdict_data_ships_as_a_public_static_file() -> None:
    # Correction 9: verdict data is admin-only and served by the API.
    assert not (FIXTURES / "verdict").exists() or not any((FIXTURES / "verdict").iterdir())
