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
from typing import Literal, Optional

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from qcompass_core import wire

from .._paths import UnsafePathError, safe_component, safe_join
from .auth import AuthError, get_auth_store, require_auth
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


def _role_for(scopes: tuple[str, ...]) -> Literal["admin", "member", "viewer"]:
    names = {s.split(":")[-1] for s in scopes}
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
    def list_tenants(
        authorization: Optional[str] = Header(default=None),
        x_qcompass_tenant: Optional[str] = Header(default=None),
    ) -> list[Tenant]:
        # Tenants the caller's credential belongs to. P3-04 extends this to
        # every tenant_members row of a Supabase user.
        if not authorization:
            raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "bearer token required"})
        try:
            token = require_auth(
                get_auth_store(), authorization=authorization, tenant_header=x_qcompass_tenant,
            )
        except AuthError as exc:
            from .api_errors import status_for

            raise HTTPException(
                status_for(exc.code), detail={"code": exc.code, "message": str(exc)},
            ) from exc
        return [Tenant(id=token.tenant_id, label=token.tenant_id, role=_role_for(token.scopes))]

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
