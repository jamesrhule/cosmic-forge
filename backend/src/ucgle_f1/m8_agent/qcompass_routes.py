"""QCompass HTTP + WS routes (PROMPT 8 v2 §A).

Mounted by :func:`server.build_app`. New endpoints — none of which
touch the existing ``/v1/chat`` or ``/api/runs`` paths:

  GET   /api/qcompass/domains
  GET   /api/qcompass/domains/{id}/schema
  POST  /api/qcompass/domains/{id}/runs
  GET   /api/qcompass/domains/{id}/runs/{run_id}
  GET   /api/qcompass/domains/{id}/runs/{run_id}/stream      (SSE)
  GET   /api/qcompass/domains/{id}/runs/{run_id}/visualization
  WS    /ws/qcompass/domains/{id}/runs/{run_id}/visualization

  GET   /api/scans
  GET   /api/scans/{scan_id}
  POST  /api/scans
  DELETE /api/scans/{scan_id}

The handlers SOFT-IMPORT ``qcompass_core`` / ``qcompass_bench`` /
``cosmic_forge_viz`` so the FastAPI app starts cleanly even when
the optional packages aren't installed (the endpoints then 503).

NOTE: this module deliberately does NOT use
``from __future__ import annotations`` — same reason as
:mod:`cosmic_forge_viz.server`: FastAPI's WS-handler parameter
introspection silently misroutes the ``WebSocket`` arg as a
query field when annotations are stringified.
"""

import asyncio
import importlib
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket
from sse_starlette.sse import EventSourceResponse

from .._paths import UnsafePathError, safe_component, safe_join
from .api_errors import status_for
from .api_models import (
    SSE_RESPONSES,
    DomainsResponse,
    ManifestJsonSchema,
    OkResponse,
    ProvenanceSidecar,
    ScanEnvelope,
    ScanListResponse,
    SubmitRunResponse,
    VisualizationResponse,
)
from .principal import Principal, authenticate_websocket, require_scope
from .scans import get_scan_registry

# Wire contract shared with the frontend (src/lib/domains/types.ts). The
# qcompass routes need qcompass-core; build_app soft-imports this module.
from qcompass_core import wire


_QCOMPASS_DOMAINS = (
    "cosmology", "chemistry", "condmat", "hep",
    "nuclear", "amo", "gravity", "statmech",
)

# Frontend DomainId (src/lib/domains/types.ts) <-> the short names used for
# storage paths and the plugin registry. Paths accept either form (P4-01).
_FULL_DOMAIN_ID = {
    "cosmology": "cosmology.ucglef1",
    "chemistry": "chemistry.molecular",
    "condmat": "condmat.lattice",
    "hep": "hep.lattice",
    "nuclear": "nuclear.structure",
    "amo": "amo.rydberg",
    "gravity": "gravity.syk",
    "statmech": "statmech.sampling",
}
_SHORT_DOMAIN = {full: short for short, full in _FULL_DOMAIN_ID.items()}


def _short_domain(domain: str) -> str:
    """Canonical short name for a path domain (short or full id); 404 otherwise."""
    if domain in _FULL_DOMAIN_ID:
        return domain
    if domain in _SHORT_DOMAIN:
        return _SHORT_DOMAIN[domain]
    raise HTTPException(404, f"unknown domain {domain!r}")


# ── Auth (P3-04) ──────────────────────────────────────────────
# Every route takes a Principal from principal.require_scope; storage is
# per tenant, so another tenant's run or scan is simply not found (404).


# ── Provenance sidecar root ───────────────────────────────────────


def _artifacts_root() -> Path:
    env = os.environ.get("UCGLE_F1_ARTIFACTS")
    base = (
        Path(env) if env
        else Path.home() / ".ucgle_f1" / "artifacts"
    )
    return base / "qcompass"


def _tenant_root(tenant: str) -> Path:
    """Per-tenant artifacts root (P3-04 isolation)."""
    try:
        return safe_join(_artifacts_root(), safe_component(tenant, "tenant"))
    except UnsafePathError as exc:
        raise HTTPException(400, str(exc)) from exc


def _sidecar_path(tenant: str, domain: str, run_id: str) -> Path:
    """Sidecar path for a request-supplied run id; 400 if the id is unsafe."""
    try:
        return safe_join(
            _tenant_root(tenant),
            safe_component(domain, "domain"),
            f"{safe_component(run_id, 'run id')}.provenance.json",
        )
    except UnsafePathError as exc:
        raise HTTPException(400, str(exc)) from exc


def _viz_dir(tenant: str, domain: str, run_id: str) -> Path:
    """Viz output dir for a request-supplied run id; 400 if the id is unsafe."""
    try:
        safe_component(run_id, "run id")
        return safe_join(_tenant_root(tenant), safe_component(domain, "domain"), "viz")
    except UnsafePathError as exc:
        raise HTTPException(400, str(exc)) from exc


def _write_provenance(
    tenant: str, domain: str, run_id: str, manifest: dict, status: str,
    *, classical_hash: str = "",
) -> Path:
    """Per the PROMPT 2 contract: every dispatch writes a sidecar."""
    root = safe_join(_tenant_root(tenant), safe_component(domain, "domain"))
    root.mkdir(parents=True, exist_ok=True)
    sidecar = safe_join(root, f"{safe_component(run_id, 'run id')}.provenance.json")
    sidecar.write_text(json.dumps({
        "schemaVersion": 1,
        "runId": run_id,
        "domain": domain,
        "status": status,
        "createdAt": datetime.now(UTC).isoformat(),
        "manifest": manifest,
        "provenance": {
            "classical_reference_hash": classical_hash,
            "calibration_hash": None,
            "error_mitigation": None,
        },
    }, indent=2, default=str))
    return sidecar


# ── Soft-import helpers ──────────────────────────────────────────


def _qcompass_core() -> Any:
    try:
        return importlib.import_module("qcompass_core")
    except ImportError as exc:
        raise HTTPException(
            503, f"qcompass_core not installed: {exc}",
        ) from exc


def _resolve_simulation(domain: str) -> Any:
    """Resolve a Simulation class for ``domain`` via the registry.

    Soft-fails to a sentinel result builder when the domain plugin
    isn't installed in the current env (e.g. qfull-amo missing) so
    the frontend can still exercise the configurator → run flow
    against a placeholder envelope.
    """
    try:
        core = _qcompass_core()
        return core.registry.get_simulation(domain)
    except HTTPException:
        raise
    except Exception:
        return None


# ── Stored run → frontend DomainRunResult ───────────────────────


def _run_status(status: str) -> str:
    """Sidecar status → frontend RunStatus."""
    if status == "completed":
        return "completed"
    if status == "submitted":
        return "queued"
    if status.startswith("failed"):
        return "failed"
    return "running"


def _run_label(short: str, run_id: str) -> str:
    return f"{_FULL_DOMAIN_ID[short]} · {run_id}"


def _domain_run_result(short: str, sc: ProvenanceSidecar) -> "wire.DomainRunResult":
    """Build the frontend's DomainRunResult from a stored provenance sidecar.

    P3-03 replaces the sidecar with the persisted RunResult; until then the
    payload carries the submitted manifest and the run's terminal status.
    """
    payload: dict = {"manifest": sc.manifest, "status_detail": sc.status}
    return wire.DomainRunResult(
        id=sc.runId,
        domain=_FULL_DOMAIN_ID[short],
        label=_run_label(short, sc.runId),
        status=_run_status(sc.status),
        payload=payload,
        provenance=wire.ProvenanceRecordExt(
            # As recorded: "" when the run produced no classical reference.
            classical_reference_hash=sc.provenance.classical_reference_hash,
            device_calibration_hash=sc.provenance.calibration_hash,
            error_mitigation_config=(
                sc.provenance.error_mitigation
                if isinstance(sc.provenance.error_mitigation, dict) else None
            ),
        ),
        created_at=sc.createdAt,
    )


# ── Domain + schema endpoints ────────────────────────────────────


def mount_qcompass_routes(app: FastAPI) -> None:
    """Mount every ``/api/qcompass/*`` + ``/ws/qcompass/*`` route."""

    read = require_scope("read")
    run = require_scope("run")

    @app.get(
        "/api/qcompass/domains",
        dependencies=[Depends(read)],
        response_model=DomainsResponse,
    )
    def list_domains() -> dict:
        try:
            core = _qcompass_core()
            domains = core.registry.list_domains()
        except HTTPException:
            domains = list(_QCOMPASS_DOMAINS)
        return {
            "domains": [
                {"id": d, "label": d.title()} for d in sorted(set(domains))
            ],
        }

    @app.get(
        "/api/qcompass/domains/{domain}/schema",
        dependencies=[Depends(read)],
        response_model=ManifestJsonSchema,
    )
    def domain_schema(domain: str) -> dict:
        domain = _short_domain(domain)
        sim_cls = _resolve_simulation(domain)
        if sim_cls is None:
            return {"$id": f"qcompass:{domain}", "type": "object"}
        try:
            schema = sim_cls.manifest_schema()
        except Exception as exc:
            raise HTTPException(500, f"schema build failed: {exc}") from exc
        return schema

    # ── Runs ────────────────────────────────────────────────────

    @app.post(
        "/api/qcompass/domains/{domain}/runs",
        response_model=SubmitRunResponse,
        responses={202: {"model": SubmitRunResponse, "description": "Accepted."}},
    )
    async def submit_run(
        domain: str, body: dict, response: Response,
        principal: Principal = Depends(run),
    ) -> dict:
        domain = _short_domain(domain)
        manifest = body.get("manifest") or body
        run_id = body.get("runId") or f"qc_{domain}_{secrets.token_hex(6)}"
        try:
            safe_component(str(run_id), "run id")
        except UnsafePathError as exc:
            raise HTTPException(400, str(exc)) from exc
        sim_cls = _resolve_simulation(domain)
        classical_hash = ""
        status = "submitted"
        if sim_cls is not None:
            try:
                core = _qcompass_core()
                qmanifest_cls = core.Manifest
                # Coerce the body into a Manifest if it isn't already.
                if "domain" not in manifest:
                    manifest = {
                        "domain": domain, "version": "1.0",
                        "problem": manifest,
                        "backend_request": {"kind": "classical"},
                    }
                qmanifest = qmanifest_cls.model_validate(manifest)
                sim = sim_cls()
                instance = sim.prepare(qmanifest)
                result = sim.run(instance, backend=None)
                classical_hash = getattr(result, "classical_hash", "") or ""
                status = "completed"
            except Exception as exc:
                # Surfaced for the audit; the sidecar still records the attempt.
                status = f"failed: {exc.__class__.__name__}"
        sidecar = _write_provenance(
            principal.tenant_id, domain, run_id, manifest, status,
            classical_hash=classical_hash,
        )
        response.status_code = 202 if status == "submitted" else 200
        return {
            "runId": run_id,
            "domain": domain,
            "status": status,
            "provenanceSidecar": str(sidecar),
            "classicalReferenceHash": classical_hash,
        }

    @app.get(
        "/api/qcompass/domains/{domain}/runs",
        response_model=list[wire.RunSummary],
    )
    def list_runs(
        domain: str, limit: int = 100, offset: int = 0,
        principal: Principal = Depends(read),
    ) -> list:
        short = _short_domain(domain)
        root = _tenant_root(principal.tenant_id) / short
        if not root.is_dir():
            return []
        sidecars = []
        for path in root.glob("*.provenance.json"):
            try:
                sidecars.append(ProvenanceSidecar.model_validate_json(path.read_text()))
            except ValueError:
                continue  # unreadable sidecar: skip rather than fail the list
        sidecars.sort(key=lambda sc: sc.createdAt, reverse=True)
        page = sidecars[max(0, offset): max(0, offset) + max(0, min(limit, 500))]
        return [
            wire.RunSummary(
                id=sc.runId,
                label=_run_label(short, sc.runId),
                status=_run_status(sc.status),
                domain=_FULL_DOMAIN_ID[short],
                created_at=sc.createdAt,
            )
            for sc in page
        ]

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}",
        response_model=wire.DomainRunResult,
        response_model_exclude_none=True,
    )
    def get_run(
        domain: str, run_id: str, principal: Principal = Depends(read),
    ) -> wire.DomainRunResult:
        short = _short_domain(domain)
        sidecar = _sidecar_path(principal.tenant_id, short, run_id)
        if not sidecar.exists():
            raise HTTPException(404, f"no run {run_id!r} under {domain!r}")
        try:
            sc = ProvenanceSidecar.model_validate_json(sidecar.read_text())
        except ValueError as exc:
            raise HTTPException(500, f"corrupt sidecar: {exc}") from exc
        return _domain_run_result(short, sc)

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}/stream",
        response_class=EventSourceResponse,
        responses=SSE_RESPONSES,
    )
    async def stream_run(
        domain: str, run_id: str, principal: Principal = Depends(read),
    ) -> EventSourceResponse:
        domain = _short_domain(domain)

        sidecar = _sidecar_path(principal.tenant_id, domain, run_id)

        async def gen() -> AsyncIterator[dict]:
            # Replay history first (per v2 §SSE spec).
            if sidecar.exists():
                payload = json.loads(sidecar.read_text())
                yield {"event": "history", "data": json.dumps(payload)}
            # Then live-tail status — v1 of this stream emits the
            # final status and a sentinel; richer per-frame events
            # land when each plugin grows a streaming Result.
            yield {"event": "status", "data": json.dumps({
                "status": "completed" if sidecar.exists() else "unknown",
                "at": datetime.now(UTC).isoformat(),
            })}
            yield {"event": "end", "data": "{}"}

        return EventSourceResponse(gen())

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}/visualization",
        response_model=VisualizationResponse,
    )
    def get_visualization(
        domain: str, run_id: str, max_frames: int = 256,
        principal: Principal = Depends(read),
    ) -> dict:
        try:
            viz = importlib.import_module("cosmic_forge_viz.baker")
            viz_schema = importlib.import_module("cosmic_forge_viz.schema")
            downsample = importlib.import_module(
                "cosmic_forge_viz.downsample",
            )
        except ImportError as exc:
            raise HTTPException(
                503, f"cosmic_forge_viz not installed: {exc}",
            ) from exc
        domain = _short_domain(domain)
        info = viz.bake_synthetic(
            domain, run_id,
            out_dir=_viz_dir(principal.tenant_id, domain, run_id),
        )
        raw = json.loads(Path(info["json_path"]).read_text())
        timeline = viz_schema.VisualizationTimeline.model_validate(raw)
        downsampled = downsample.target_count_decimate(
            timeline.frames, max_frames,
        )
        return {
            "run_id": timeline.run_id,
            "domain": timeline.domain,
            "schema_version": timeline.schema_version,
            "n_frames": len(downsampled),
            "frames": downsampled,
        }

    @app.websocket("/ws/qcompass/domains/{domain}/runs/{run_id}/visualization")
    async def ws_visualization(
        websocket: WebSocket, domain: str, run_id: str,
    ) -> None:
        # Same check as the HTTP routes (P3-04); closes 1008 on failure.
        principal = await authenticate_websocket(websocket, "read")
        if principal is None:
            return
        try:
            viz = importlib.import_module("cosmic_forge_viz.baker")
            viz_schema = importlib.import_module("cosmic_forge_viz.schema")
            protocol = importlib.import_module("cosmic_forge_viz.protocol")
        except ImportError:
            await websocket.close(code=1011)
            return
        try:
            domain = _short_domain(domain)
        except HTTPException:
            await websocket.close(code=1008)
            return
        try:
            viz_dir = _viz_dir(principal.tenant_id, domain, run_id)
        except HTTPException as exc:
            await websocket.close(code=1008, reason=str(exc.detail))
            return
        await websocket.accept()
        info = viz.bake_synthetic(
            domain, run_id,
            out_dir=viz_dir,
        )
        raw = json.loads(Path(info["json_path"]).read_text())
        timeline = viz_schema.VisualizationTimeline.model_validate(raw)
        await websocket.send_bytes(protocol.encode(protocol.envelope(
            "header", seq=0, payload={
                "run_id": timeline.run_id,
                "domain": timeline.domain,
                "n_frames": len(timeline.frames),
            },
        )))
        for seq, frame in enumerate(timeline.frames, start=1):
            await websocket.send_bytes(protocol.encode(protocol.envelope(
                "frame", seq=seq,
                tau=float(frame.get("tau", 0.0)),
                payload=frame,
            )))
            await asyncio.sleep(0)
        await websocket.send_bytes(protocol.encode(protocol.envelope("end")))
        # Hold the channel open until the client disconnects so
        # starlette's TestClient processes the queued bytes (matches
        # the cosmic_forge_viz.server pattern).
        try:
            await websocket.receive()
        except Exception:
            return


def mount_scan_routes(app: FastAPI) -> None:
    """Mount the scan routes under ``/api/qcompass/scans`` (the path the
    frontend calls, P4-01) and the original ``/api/scans`` alias."""
    for prefix in ("/api/qcompass/scans", "/api/scans"):
        _mount_scan_routes_at(app, prefix)


def _mount_scan_routes_at(app: FastAPI, prefix: str) -> None:

    read = require_scope("read")
    run = require_scope("run")

    @app.get(prefix, response_model=ScanListResponse)
    def list_scans(
        domain: Optional[str] = None, limit: int = 100,
        principal: Principal = Depends(read),
    ) -> dict:
        registry = get_scan_registry()
        records = registry.list_all(domain=domain, limit=limit, tenant_id=principal.tenant_id)
        return {
            "scans": [r.to_envelope() for r in records],
        }

    @app.get(prefix + "/{scan_id}", response_model=ScanEnvelope)
    def get_scan(scan_id: str, principal: Principal = Depends(read)) -> dict:
        record = get_scan_registry().get(scan_id, tenant_id=principal.tenant_id)
        if record is None:
            raise HTTPException(404, f"no scan {scan_id!r}")
        return record.to_envelope()

    @app.post(prefix, response_model=ScanEnvelope, status_code=201)
    def create_scan(body: dict, principal: Principal = Depends(run)) -> dict:
        domain = str(body.get("domain") or "")
        kind = str(body.get("kind") or "")
        if not domain or not kind:
            raise HTTPException(422, "domain + kind are required")
        record = get_scan_registry().submit(
            tenant_id=principal.tenant_id,
            domain=domain, kind=kind,
            axes=body.get("axes") or {},
            payload=body.get("payload") or {},
            provenance=body.get("provenance") or {},
        )
        return record.to_envelope()

    @app.delete(prefix + "/{scan_id}", response_model=OkResponse)
    def delete_scan(scan_id: str, principal: Principal = Depends(run)) -> dict:
        ok = get_scan_registry().delete(scan_id, tenant_id=principal.tenant_id)
        if not ok:
            raise HTTPException(404, f"no scan {scan_id!r}")
        return {"ok": True}



__all__ = [
    "mount_qcompass_routes",
    "mount_scan_routes",
]
