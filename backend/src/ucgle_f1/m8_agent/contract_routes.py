"""Endpoints the frontend calls that the backend lacked (P4-01).

- ``GET /api/qcompass/tenants``: tenants the caller belongs to.
- ``GET /api/qcompass/verdict``, ``GET /api/verdict/{id}``: Phase-3
  verdict reports, admin only (correction 9). Data lives with the backend
  (``data/verdicts/*.yaml`` or ``QCOMPASS_VERDICT_DIR``), not under the
  frontend's public static files.
- ``GET /api/qcompass/literature/lattice-qcd`` and ``/nuclear``: reference
  values for the compare-to-literature sheets.

Shapes are the frontend's (``src/services/qcompass/*.ts``); verdicts use
``qcompass_core.wire.VerdictSample``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from qcompass_core import wire

from .._paths import UnsafePathError, safe_component, safe_join
from .auth import get_auth_store
from .principal import Principal, require_scope
from .supabase_auth import SupabaseUser, require_supabase_admin

_DATA = Path(__file__).resolve().parent / "data"


class Tenant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    role: Literal["admin", "member", "viewer"]


class LiteratureReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observable: str
    value: float
    uncertainty: float
    units: str
    source_label: str
    arxiv_id: str
    notes: str | None = None


def _role_for(scopes: frozenset[str]) -> Literal["admin", "member", "viewer"]:
    names = set(scopes)
    if "admin" in names:
        return "admin"
    if names & {"run", "write", "qpu"}:
        return "member"
    return "viewer"


def _verdict_dir() -> Path:
    env = os.environ.get("QCOMPASS_VERDICT_DIR")
    return Path(env) if env else _DATA / "verdicts"


def _load_verdict(path: Path) -> wire.VerdictSample:
    return wire.VerdictSample.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=4)
def _literature(name: str) -> list[LiteratureReference]:
    data = json.loads((_DATA / "literature" / f"{name}.json").read_text(encoding="utf-8"))
    return [LiteratureReference.model_validate(r) for r in data]


def mount_contract_routes(app: FastAPI) -> None:
    @app.get("/api/qcompass/tenants", response_model=list[Tenant])
    def list_tenants(principal: Principal = Depends(require_scope("read"))) -> list[Tenant]:
        """Tenants the caller can act in (P3-04).

        A Supabase user gets every ``tenant_members`` row; an API key or the
        dev principal gets its one tenant.
        """
        if principal.kind == "supabase":
            return [
                Tenant(id=tid, label=tid, role=role)  # type: ignore[arg-type]
                for tid, role in get_auth_store().memberships(principal.subject)
            ]
        return [Tenant(id=principal.tenant_id, label=principal.tenant_id, role=_role_for(principal.scopes))]

    @app.get(
        "/api/qcompass/verdict",
        response_model=wire.VerdictSample,
        response_model_exclude_none=True,
    )
    def latest_verdict(
        _admin: SupabaseUser = Depends(require_supabase_admin),
    ) -> wire.VerdictSample:
        reports = [_load_verdict(p) for p in sorted(_verdict_dir().glob("*.yaml"))]
        if not reports:
            raise HTTPException(404, "no verdict report")
        return max(reports, key=lambda r: r.generated_at)

    @app.get(
        "/api/verdict/{verdict_id}",
        response_model=wire.VerdictSample,
        response_model_exclude_none=True,
    )
    def get_verdict(
        verdict_id: str,
        _admin: SupabaseUser = Depends(require_supabase_admin),
    ) -> wire.VerdictSample:
        try:
            path = safe_join(_verdict_dir(), f"{safe_component(verdict_id, 'verdict id')}.yaml")
        except UnsafePathError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not path.exists():
            raise HTTPException(404, f"no verdict {verdict_id!r}")
        return _load_verdict(path)

    @app.get("/api/qcompass/literature/lattice-qcd", response_model=list[LiteratureReference],
             response_model_exclude_none=True)
    def lattice_qcd_references() -> list[LiteratureReference]:
        return _literature("lattice-qcd")

    @app.get("/api/qcompass/literature/nuclear", response_model=list[LiteratureReference],
             response_model_exclude_none=True)
    def nuclear_references() -> list[LiteratureReference]:
        return _literature("nuclear")


__all__ = ["LiteratureReference", "Tenant", "mount_contract_routes"]
