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
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from .auth import (
    AuthError,
    Token,
    get_auth_store,
    require_auth,
    set_active_tenant,
)
from .scans import ScanRecord, get_scan_registry


_QCOMPASS_DOMAINS = (
    "cosmology", "chemistry", "condmat", "hep",
    "nuclear", "amo", "gravity", "statmech",
)


# ── Auth dependency ─────────────────────────────────────────────


_AUTH_CODE_TO_HTTP = {
    "AUTH_REQUIRED": 401,
    "AUTH_MALFORMED": 400,
    "AUTH_INVALID": 401,
    "AUTH_EXPIRED": 401,
    "TENANT_REQUIRED": 400,
    "TENANT_MISMATCH": 403,
    "BUDGET_EXCEEDED": 402,
}


def _qcompass_auth(
    authorization: Optional[str] = Header(default=None),
    x_qcompass_tenant: Optional[str] = Header(default=None),
) -> Token:
    """FastAPI dependency: validate bearer + tenant headers.

    Bound to every ``/api/qcompass/*`` route via ``Depends``. The
    legacy ``/api/runs`` + ``/api/benchmarks`` paths remain
    unauthenticated by design (PROMPT 10 v2 §A scope).
    """
    store = get_auth_store()
    try:
        token = require_auth(
            store,
            authorization=authorization,
            tenant_header=x_qcompass_tenant,
        )
    except AuthError as exc:
        status = _AUTH_CODE_TO_HTTP.get(exc.code, 401)
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    set_active_tenant(token.tenant_id)
    return token


def _allow_dev_anonymous() -> bool:
    """Return True when the dev-mode opt-out flag is set.

    Tests that exercise the legacy unauthenticated A7 paths set
    ``QCOMPASS_DEV_ALLOW_ANONYMOUS=1``. Production env never sets
    it; A8 verifies the gate fires when unset.
    """
    return os.environ.get("QCOMPASS_DEV_ALLOW_ANONYMOUS") == "1"


def _maybe_auth_dependency():
    """Return a no-op dependency in dev-mode; the real one otherwise."""
    if _allow_dev_anonymous():
        def _passthrough() -> Optional[Token]:
            return None
        return _passthrough
    return _qcompass_auth


# ── Provenance sidecar root ───────────────────────────────────────


def _artifacts_root() -> Path:
    env = os.environ.get("UCGLE_F1_ARTIFACTS")
    base = (
        Path(env) if env
        else Path.home() / ".ucgle_f1" / "artifacts"
    )
    return base / "qcompass"


def _write_provenance(
    domain: str, run_id: str, manifest: dict, status: str,
    *, classical_hash: str = "",
) -> Path:
    """Per the PROMPT 2 contract: every dispatch writes a sidecar."""
    root = _artifacts_root() / domain
    root.mkdir(parents=True, exist_ok=True)
    sidecar = root / f"{run_id}.provenance.json"
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


# ── Domain + schema endpoints ────────────────────────────────────


def mount_qcompass_routes(app: FastAPI) -> None:
    """Mount every ``/api/qcompass/*`` + ``/ws/qcompass/*`` route."""

    auth_dep = _maybe_auth_dependency()

    @app.get(
        "/api/qcompass/domains",
        dependencies=[Depends(auth_dep)],
    )
    def list_domains() -> JSONResponse:
        try:
            core = _qcompass_core()
            domains = core.registry.list_domains()
        except HTTPException:
            domains = list(_QCOMPASS_DOMAINS)
        return JSONResponse({
            "domains": [
                {"id": d, "label": d.title()} for d in sorted(set(domains))
            ],
        })

    @app.get(
        "/api/qcompass/domains/{domain}/schema",
        dependencies=[Depends(auth_dep)],
    )
    def domain_schema(domain: str) -> JSONResponse:
        if domain not in _QCOMPASS_DOMAINS and domain != "cosmology.ucglef1":
            raise HTTPException(404, f"unknown domain {domain!r}")
        sim_cls = _resolve_simulation(domain)
        if sim_cls is None:
            return JSONResponse({"$id": f"qcompass:{domain}", "type": "object"})
        try:
            schema = sim_cls.manifest_schema()
        except Exception as exc:
            raise HTTPException(500, f"schema build failed: {exc}") from exc
        return JSONResponse(schema)

    # ── Runs ────────────────────────────────────────────────────

    @app.post(
        "/api/qcompass/domains/{domain}/runs",
        dependencies=[Depends(auth_dep)],
    )
    async def submit_run(domain: str, body: dict) -> JSONResponse:
        if domain not in _QCOMPASS_DOMAINS:
            raise HTTPException(404, f"unknown domain {domain!r}")
        manifest = body.get("manifest") or body
        run_id = body.get("runId") or f"qc_{domain}_{secrets.token_hex(6)}"
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
            domain, run_id, manifest, status, classical_hash=classical_hash,
        )
        return JSONResponse({
            "runId": run_id,
            "domain": domain,
            "status": status,
            "provenanceSidecar": str(sidecar),
            "classicalReferenceHash": classical_hash,
        }, status_code=202 if status == "submitted" else 200)

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}",
        dependencies=[Depends(auth_dep)],
    )
    def get_run(domain: str, run_id: str) -> JSONResponse:
        if domain not in _QCOMPASS_DOMAINS:
            raise HTTPException(404, f"unknown domain {domain!r}")
        sidecar = _artifacts_root() / domain / f"{run_id}.provenance.json"
        if not sidecar.exists():
            raise HTTPException(404, f"no run {run_id!r} under {domain!r}")
        try:
            payload = json.loads(sidecar.read_text())
        except json.JSONDecodeError as exc:
            raise HTTPException(500, f"corrupt sidecar: {exc}") from exc
        return JSONResponse(payload)

    @app.get(
        "/api/qcompass/domains/{domain}/runs/{run_id}/stream",
        dependencies=[Depends(auth_dep)],
    )
    async def stream_run(domain: str, run_id: str) -> EventSourceResponse:
        if domain not in _QCOMPASS_DOMAINS:
            raise HTTPException(404, f"unknown domain {domain!r}")

        async def gen() -> AsyncIterator[dict]:
            sidecar = _artifacts_root() / domain / f"{run_id}.provenance.json"
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
        dependencies=[Depends(auth_dep)],
    )
    def get_visualization(
        domain: str, run_id: str, max_frames: int = 256,
    ) -> JSONResponse:
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
        if domain not in _QCOMPASS_DOMAINS:
            raise HTTPException(404, f"unknown domain {domain!r}")
        info = viz.bake_synthetic(
            domain, run_id,
            out_dir=_artifacts_root() / domain / "viz",
        )
        raw = json.loads(Path(info["json_path"]).read_text())
        timeline = viz_schema.VisualizationTimeline.model_validate(raw)
        downsampled = downsample.target_count_decimate(
            timeline.frames, max_frames,
        )
        return JSONResponse({
            "run_id": timeline.run_id,
            "domain": timeline.domain,
            "schema_version": timeline.schema_version,
            "n_frames": len(downsampled),
            "frames": downsampled,
        })

    @app.websocket("/ws/qcompass/domains/{domain}/runs/{run_id}/visualization")
    async def ws_visualization(
        websocket: WebSocket, domain: str, run_id: str,
    ) -> None:
        # Inline auth check — FastAPI's Depends path doesn't apply to
        # WebSocket header injection here. Auth headers are looked
        # up directly off the request scope.
        if not _allow_dev_anonymous():
            store = get_auth_store()
            try:
                require_auth(
                    store,
                    authorization=websocket.headers.get("authorization"),
                    tenant_header=websocket.headers.get("x-qcompass-tenant"),
                )
            except AuthError:
                # 1008 = policy violation; the spec uses this for
                # auth-rejected WebSockets.
                await websocket.close(code=1008)
                return
        try:
            viz = importlib.import_module("cosmic_forge_viz.baker")
            viz_schema = importlib.import_module("cosmic_forge_viz.schema")
            protocol = importlib.import_module("cosmic_forge_viz.protocol")
        except ImportError:
            await websocket.close(code=1011)
            return
        if domain not in _QCOMPASS_DOMAINS:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        info = viz.bake_synthetic(
            domain, run_id,
            out_dir=_artifacts_root() / domain / "viz",
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
    """Mount every ``/api/scans/*`` route."""

    @app.get("/api/scans")
    def list_scans(
        domain: Optional[str] = None, limit: int = 100,
    ) -> JSONResponse:
        registry = get_scan_registry()
        records = registry.list_all(domain=domain, limit=limit)
        return JSONResponse({
            "scans": [r.to_envelope() for r in records],
        })

    @app.get("/api/scans/{scan_id}")
    def get_scan(scan_id: str) -> JSONResponse:
        record = get_scan_registry().get(scan_id)
        if record is None:
            raise HTTPException(404, f"no scan {scan_id!r}")
        return JSONResponse(record.to_envelope())

    @app.post("/api/scans")
    def create_scan(body: dict) -> JSONResponse:
        domain = str(body.get("domain") or "")
        kind = str(body.get("kind") or "")
        if not domain or not kind:
            raise HTTPException(422, "domain + kind are required")
        record = get_scan_registry().submit(
            domain=domain, kind=kind,
            axes=body.get("axes") or {},
            payload=body.get("payload") or {},
            provenance=body.get("provenance") or {},
        )
        return JSONResponse(record.to_envelope(), status_code=201)

    @app.delete("/api/scans/{scan_id}")
    def delete_scan(scan_id: str) -> JSONResponse:
        ok = get_scan_registry().delete(scan_id)
        if not ok:
            raise HTTPException(404, f"no scan {scan_id!r}")
        return JSONResponse({"ok": True})


__all__ = [
    "mount_qcompass_routes",
    "mount_scan_routes",
]
