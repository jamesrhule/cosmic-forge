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

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
from sse_starlette.sse import EventSourceResponse

from .._paths import UnsafePathError, safe_component, safe_join
from .api_errors import invalid_input, status_for
from .api_models import (
    SSE_RESPONSES,
    DomainsResponse,
    ManifestJsonSchema,
    OkResponse,
    ScanEnvelope,
    ScanListResponse,
    SubmitRunResponse,
    VisualizationResponse,
)
from sqlalchemy.exc import IntegrityError

from ..domain import ServiceError
from ..jobs import TERMINAL_RUN_STATUSES, get_queue
from .auth import get_auth_store
from .principal import Principal, authenticate_websocket, require_scope
from .scans import get_scan_registry
from .settings import STREAM_TERMINAL_GRACE_SECONDS, StreamBound

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


def _ended_status(queue: Any, run_id: str, tenant_uuid: str) -> dict[str, Any] | None:
    """A terminal status event for a run that ended without one (SF1), else None."""
    ended = queue.ended(run_id, tenant_uuid=tenant_uuid, grace_seconds=STREAM_TERMINAL_GRACE_SECONDS)
    if ended is None:
        return None
    status, at = ended
    return {"type": "status", "status": status, "at": at.isoformat()}


def _short_domain(domain: str) -> str:
    """Canonical short name for a path domain (short or full id); 404 otherwise."""
    # Return the allowlist's own string, never the caller's (CodeQL path taint).
    for short, full in _FULL_DOMAIN_ID.items():
        if domain in (short, full):
            return short
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


def _sidecar_ref(sidecar: Path) -> str:
    """The sidecar's path relative to the artifacts root (``UCGLE_F1_ARTIFACTS``)."""
    return sidecar.relative_to(_artifacts_root().parent).as_posix()


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
    """Resolve a Simulation class for ``domain`` via the registry (None if
    the plugin isn't installed in this API image)."""
    _qcompass_core()  # 503 when qcompass-core is missing
    from ..worker import resolve_simulation

    try:
        return resolve_simulation(domain)
    except Exception:
        return None


# ── Stored run → frontend DomainRunResult ───────────────────────


_NEW_RUN_ID_ATTEMPTS = 3


def _new_run_id(domain: str) -> str:
    """A fresh server-side run id (the primary key of ``public.runs``)."""
    return f"qc_{domain}_{secrets.token_hex(6)}"


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)


def _run_status(status: str) -> str:
    """``public.run_status`` → frontend RunStatus (no "canceled" there)."""
    if status in {"queued", "running", "completed"}:
        return status
    return "failed"


def _run_label(short: str, run_id: str) -> str:
    return f"{_FULL_DOMAIN_ID[short]} · {run_id}"


def _domain_run_result(
    short: str, rec: Any, stored: dict | None, prov_row: dict | None = None,
) -> "wire.DomainRunResult":
    """Build the frontend's DomainRunResult from the Postgres run (P3-03).

    ``payload`` is the worker's stored result (``public.run_results``),
    returned as stored; before the run finishes it carries the submitted
    manifest and the run's status.
    """
    payload: dict = stored if stored is not None else {
        "manifest": rec.config.get("manifest"), "status_detail": rec.status,
    }
    prov_row = prov_row or {}
    return wire.DomainRunResult(
        id=rec.id,
        domain=_FULL_DOMAIN_ID[short],
        label=rec.label or _run_label(short, rec.id),
        status=_run_status(rec.status),
        payload=payload,
        provenance=wire.ProvenanceRecordExt(
            # As recorded: "" when the run produced no classical reference.
            classical_reference_hash=str(
                prov_row.get("classical_reference_hash")
                or payload.get("classical_reference_hash", "") or "",
            ),
            device_calibration_hash=prov_row.get("calibration_hash"),
            error_mitigation_config=(
                prov_row.get("error_mitigation")
                if isinstance(prov_row.get("error_mitigation"), dict) else None
            ),
        ),
        created_at=rec.created_at.isoformat(),
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
        status_code=202,
        responses={202: {"model": SubmitRunResponse, "description": "Accepted and queued."}},
    )
    async def submit_run(
        domain: str, body: dict, principal: Principal = Depends(run),
    ) -> dict:
        """Validate, enqueue a ``qcompass.run`` job and return 202 (P3-02).

        The simulation never runs inside the request: a worker claims the
        job, and progress streams from ``…/runs/{run_id}/stream``.
        """
        domain = _short_domain(domain)
        manifest = body.get("manifest") or body
        # SEC-L2 (round 2): the run's id is always generated here. A runId in
        # the body is the caller's alias for it, unique within the caller's
        # tenant only, so no tenant can take or probe another tenant's names.
        alias = body.get("runId")
        if alias is not None:
            try:
                alias = safe_component(str(alias), "run id")
            except UnsafePathError as exc:
                raise HTTPException(400, str(exc)) from exc
        core = _qcompass_core()
        if "domain" not in manifest:
            manifest = {
                "domain": domain, "version": "1.0",
                "problem": manifest,
                "backend_request": {"kind": "classical"},
            }
        try:
            core.Manifest.model_validate(manifest)
        except ValueError as exc:
            raise HTTPException(
                422, detail={"code": "INVALID_INPUT", "message": f"invalid manifest: {exc}"},
            ) from exc
        # W1-PARAMS: a plugin that can check its problem does so here, so a
        # config the worker would refuse is a 422 now, not a failed run later.
        validate_problem = getattr(_resolve_simulation(domain), "validate_problem", None)
        if validate_problem is not None:
            try:
                await asyncio.to_thread(validate_problem, manifest.get("problem"))
            except ValueError as exc:
                raise invalid_input(exc, f"{domain} problem") from exc
        tenant_uuid = await asyncio.to_thread(get_auth_store().ensure_tenant, principal.tenant_id)
        for attempt in range(_NEW_RUN_ID_ATTEMPTS):
            run_id = _new_run_id(domain)
            try:
                await asyncio.to_thread(
                    get_queue().enqueue_run,
                    run_id=run_id, tenant_uuid=tenant_uuid, kind="qcompass.run",
                    payload={"domain": domain, "manifest": manifest},
                    label=_run_label(domain, alias or run_id),
                    config={"domain": domain, "kind": "qcompass.run", "manifest": manifest},
                    client_run_id=alias,
                )
                break
            except IntegrityError as exc:
                if _violated_constraint(exc) == "runs_tenant_client_run_id_key":
                    # The caller's own tenant already uses this alias.
                    raise HTTPException(
                        409, detail={
                            "code": "CONFLICT",
                            "message": "runId is already used in this tenant; choose another runId or omit it",
                        },
                    ) from exc
                if attempt + 1 == _NEW_RUN_ID_ATTEMPTS:
                    raise
            except ServiceError as exc:  # plan limits (P3-05): 429 / 402
                raise HTTPException(status_for(exc.code), detail=exc.to_dict()) from exc
        # The dispatch record (PROMPT 2 contract); Postgres holds the run.
        sidecar = _write_provenance(principal.tenant_id, domain, run_id, manifest, "submitted")
        return {
            "runId": run_id,
            "clientRunId": alias,
            "domain": domain,
            "status": "queued",
            # SEC-L4: a logical reference, never the server's filesystem path.
            "provenanceSidecar": _sidecar_ref(sidecar),
            "classicalReferenceHash": "",
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
        tenant = get_auth_store().resolve_tenant(principal.tenant_id)
        if tenant is None:
            return []
        records = get_queue().list_runs(
            tenant_uuid=tenant[0], domain=short,
            limit=max(0, min(limit, 500)), offset=max(0, offset),
        )
        return [
            wire.RunSummary(
                id=rec.id,
                label=rec.label or _run_label(short, rec.id),
                status=_run_status(rec.status),
                domain=_FULL_DOMAIN_ID[short],
                created_at=rec.created_at.isoformat(),
            )
            for rec in records
        ]

    def _stored_run(principal: Principal, short: str, run_id: str) -> Any:
        try:
            safe_component(run_id, "run id")  # one id grammar for paths and rows
        except UnsafePathError as exc:
            raise HTTPException(400, str(exc)) from exc
        tenant = get_auth_store().resolve_tenant(principal.tenant_id)
        rec = get_queue().get_run(run_id, tenant_uuid=tenant[0]) if tenant else None
        if rec is None or rec.config.get("domain") != short:
            raise HTTPException(404, f"no run {run_id!r} under {short!r}")
        return rec

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}",
        response_model=wire.DomainRunResult,
        response_model_exclude_none=True,
    )
    def get_run(
        domain: str, run_id: str, principal: Principal = Depends(read),
    ) -> wire.DomainRunResult:
        short = _short_domain(domain)
        rec = _stored_run(principal, short, run_id)
        queue = get_queue()
        return _domain_run_result(
            short, rec,
            queue.result(rec.id, tenant_uuid=rec.tenant_id),
            queue.provenance(rec.id, tenant_uuid=rec.tenant_id),
        )

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}/stream",
        response_class=EventSourceResponse,
        responses=SSE_RESPONSES,
    )
    async def stream_run(
        domain: str, run_id: str, principal: Principal = Depends(read),
    ) -> EventSourceResponse:
        short = _short_domain(domain)
        rec = await asyncio.to_thread(_stored_run, principal, short, run_id)

        async def gen() -> AsyncIterator[dict]:
            # Replay history first (v2 SSE spec), then tail the worker's
            # events from Postgres until the run ends.
            yield {"event": "history", "data": json.dumps({
                "runId": rec.id, "domain": short, "manifest": rec.config.get("manifest"),
                "createdAt": rec.created_at.isoformat(),
            })}
            after = 0
            queue = get_queue()
            bound = StreamBound()  # SF1: never poll forever
            while True:
                events = await asyncio.to_thread(
                    queue.events, rec.id, after_id=after, tenant_uuid=rec.tenant_id,
                )
                if events:
                    bound.saw_event()
                for ev in events:
                    after = ev.id
                    if ev.type == "heartbeat":  # worker liveness: keeps the stream from idling
                        continue
                    yield {"event": ev.type, "data": json.dumps(ev.payload)}
                    if ev.type == "status" and ev.payload.get("status") in TERMINAL_RUN_STATUSES:
                        yield {"event": "end", "data": "{}"}
                        return
                if (reason := bound.expired()) is not None:
                    yield {"event": "error", "data": json.dumps({"code": "STREAM_ABORTED", "message": reason})}
                    yield {"event": "end", "data": "{}"}
                    return
                if not events and bound.run_check_due():
                    ended = await asyncio.to_thread(_ended_status, queue, rec.id, rec.tenant_id)
                    if ended is not None:
                        yield {"event": "status", "data": json.dumps(ended)}
                        yield {"event": "end", "data": "{}"}
                        return
                await asyncio.sleep(0.2)

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
        # SEC-L4: only a run of the caller's tenant (404 otherwise, as for
        # GET …/runs/{run_id}); nothing is written for an unknown id.
        rec = _stored_run(principal, domain, run_id)
        info = viz.bake_synthetic(
            domain, rec.id,
            out_dir=_viz_dir(principal.tenant_id, domain, rec.id),
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
            # B2 (R7): bake_synthetic until P4-04; labelled, never passed off as computed.
            "synthetic": True,
            "source": "synthetic-bake",
        }

    @app.websocket("/ws/qcompass/domains/{domain}/runs/{run_id}/events")
    async def ws_run_events(websocket: WebSocket, domain: str, run_id: str) -> None:
        """The run's progress events over WebSocket (same rows as the SSE stream)."""
        principal = await authenticate_websocket(websocket, "read")
        if principal is None:
            return
        try:
            short = _short_domain(domain)
            rec = await asyncio.to_thread(_stored_run, principal, short, run_id)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue = get_queue()
        after = 0
        bound = StreamBound()  # SF1: never poll forever
        while True:
            events = await asyncio.to_thread(
                queue.events, rec.id, after_id=after, tenant_uuid=rec.tenant_id,
            )
            if events:
                bound.saw_event()
            for ev in events:
                after = ev.id
                if ev.type == "heartbeat":  # worker liveness: keeps the stream from idling
                    continue
                await websocket.send_json({"event": ev.type, "data": ev.payload})
                if ev.type == "status" and ev.payload.get("status") in TERMINAL_RUN_STATUSES:
                    await websocket.close(code=1000)
                    return
            if (reason := bound.expired()) is not None:
                await websocket.send_json({"event": "error", "data": {"code": "STREAM_ABORTED", "message": reason}})
                await websocket.close(code=1000)
                return
            if not events and bound.run_check_due():
                ended = await asyncio.to_thread(_ended_status, queue, rec.id, rec.tenant_id)
                if ended is not None:
                    await websocket.send_json({"event": "status", "data": ended})
                    await websocket.close(code=1000)
                    return
            await asyncio.sleep(0.2)

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
            _viz_dir(principal.tenant_id, domain, run_id)
        except HTTPException as exc:
            await websocket.close(code=1008, reason=str(exc.detail))
            return
        try:
            # SEC-L4: the run must exist in the caller's tenant.
            rec = await asyncio.to_thread(_stored_run, principal, domain, run_id)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        info = viz.bake_synthetic(
            domain, rec.id,
            out_dir=_viz_dir(principal.tenant_id, domain, rec.id),
        )
        raw = json.loads(Path(info["json_path"]).read_text())
        timeline = viz_schema.VisualizationTimeline.model_validate(raw)
        await websocket.send_bytes(protocol.encode(protocol.envelope(
            "header", seq=0, payload={
                "run_id": timeline.run_id,
                "domain": timeline.domain,
                "n_frames": len(timeline.frames),
                "synthetic": True,
                "source": "synthetic-bake",
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
