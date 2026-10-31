"""FastAPI app factory: REST + SSE + WS for per-run visualization.

Endpoints (``{domain}`` is one of the six original domains; gravity and
statmech are served by the M8 ``/api/qcompass/...`` routes):

  GET  /api/runs/{domain}/{id}/manifest?total=
       → ``VisualizationManifest`` JSON.
  GET  /api/runs/{domain}/{id}/visualization?total=&max_frames=
       → ``{run_id, domain, schema_version, synthetic, n_frames,
          manifest, frames}``.
  POST /api/runs/{domain}/{id}/visualization/render
       → with a provenance JSON body: bake now, 200 + bake info.
         Without a body: 202 ``{"status": "queued"}``; the synthetic
         bake runs as a background task when a viz root is configured.
  GET  /sse/runs/{domain}/{id}/visualization?total=&fps=&max_frames=
       → named SSE events ``header``, ``frame`` × N, ``done``; each
         ``data:`` is one line of compact JSON (frame events carry the
         bare frame dict).
  WS   /ws/runs/{domain}/{id}/visualization?total=&fps=
       → binary envelopes (``protocol.envelope``) ``header``,
         ``frame`` × N, ``end``; msgpack when ormsgpack is installed,
         else JSON.

Frame source: the baked JSON snapshot ``<viz_root>/<domain>/<id>.json``
if present, else ``total`` deterministic synthetic frames (flagged
``synthetic``). The viz root is ``create_app(viz_root=...)``, else
``$VIZ_ARTIFACTS``, else none (synthesis only, nothing persisted).

fastapi / starlette are soft-imported inside :func:`create_app`.

NOTE: this module deliberately does NOT use ``from __future__ import
annotations``: FastAPI inspects the WS handler's annotations to find
the ``WebSocket`` parameter, and a stringified annotation makes it a
query field instead.
"""

import asyncio
import os
from pathlib import Path
from typing import Any

from .baker import bake_from_provenance, bake_synthetic, manifest_for_timeline
from .downsample import adaptive_decimate, downsample_frames
from .fixtures import stable_seed, synthesize_frames, synthesize_manifest
from .protocol import encode, envelope, sse_event
from .schema import VisualizationManifest, VisualizationTimeline

try:
    from fastapi import WebSocket  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - extras absent
    WebSocket = Any  # type: ignore[assignment, misc]

VALID_DOMAINS = ("cosmology", "chemistry", "condmat", "hep", "nuclear", "amo")
_MAX_TOTAL = 2000


def _variant_for(domain: str, run_id: str) -> str | None:
    """Formula variant for a cosmology run; honours ``ucgle-fN-…`` run IDs."""
    if domain != "cosmology":
        return None
    if run_id.startswith("ucgle-f"):
        token = run_id.split("-")[1][1:] if "-" in run_id else ""
        if token.isdigit() and 1 <= int(token) <= 7:
            return f"F{token}"
    return "F1"


class _Source:
    """Frames (as JSON dicts) + manifest for one run."""

    def __init__(
        self, frames: list[dict[str, Any]], manifest: VisualizationManifest, synthetic: bool,
        schema_version: int = 1,
    ) -> None:
        self.frames = frames
        self.manifest = manifest
        self.synthetic = synthetic
        self.schema_version = schema_version


def _resolve_root(viz_root: Path | None) -> Path | None:
    if viz_root is not None:
        return Path(viz_root)
    env = os.environ.get("VIZ_ARTIFACTS")
    return Path(env) if env else None


def _load_source(root: Path | None, domain: str, run_id: str, total: int) -> _Source:
    if root is not None:
        path = root / domain / f"{run_id}.json"
        if path.exists():
            timeline = VisualizationTimeline.model_validate_json(path.read_text())
            return _Source(
                timeline.frames,
                manifest_for_timeline(timeline, bake_uri=str(path)),
                timeline.synthetic,
                timeline.schema_version,
            )
    variant = _variant_for(domain, run_id)
    frames = synthesize_frames(
        domain,
        total_frames=total,
        seed=stable_seed(run_id),
        formula_variant=variant or "F1",
    )
    manifest = synthesize_manifest(
        domain=domain,
        run_id=run_id,
        total_frames=total,
        seed=stable_seed(run_id),
        formula_variant=variant,
    )
    return _Source([f.model_dump(mode="json") for f in frames], manifest, True)


def _header_payload(src: _Source, n_frames: int) -> dict[str, Any]:
    return {
        "run_id": src.manifest.run_id,
        "domain": src.manifest.domain,
        "n_frames": n_frames,
        "synthetic": src.synthetic,
        "manifest": src.manifest.model_dump(mode="json"),
    }


def create_app(*, viz_root: Path | None = None, default_total_frames: int = 60) -> Any:
    """Build the FastAPI app (raises ``ImportError`` without the viz extras)."""
    try:
        from fastapi import (  # type: ignore[import-not-found]
            BackgroundTasks,
            Body,
            FastAPI,
            HTTPException,
            Query,
        )
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-not-found]
        from fastapi.responses import (  # type: ignore[import-not-found]
            JSONResponse,
            StreamingResponse,
        )
    except ImportError as exc:
        raise ImportError(
            "cosmic_forge_viz.server requires the backend `viz` extras "
            "(`pip install -e 'backend[viz]'`)."
        ) from exc

    app = FastAPI(
        title="cosmic-forge-viz",
        version="0.1.0",
        description="Cross-domain visualization streaming for the cosmic-forge stack.",
    )
    # The frontend dev server runs on another port.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    def _root() -> Path | None:
        return _resolve_root(viz_root)

    def _check_domain(domain: str) -> None:
        if domain not in VALID_DOMAINS:
            raise HTTPException(status_code=404, detail=f"unknown domain {domain!r}")

    @app.get("/api/runs/{domain}/{run_id}/manifest")
    def get_manifest(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=_MAX_TOTAL),
    ) -> Any:
        _check_domain(domain)
        src = _load_source(_root(), domain, run_id, total)
        return JSONResponse(src.manifest.model_dump(mode="json"))

    @app.get("/api/runs/{domain}/{run_id}/visualization")
    def get_timeline(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=_MAX_TOTAL),
        max_frames: int | None = Query(default=None, ge=0, le=_MAX_TOTAL),
    ) -> Any:
        _check_domain(domain)
        src = _load_source(_root(), domain, run_id, total)
        frames = src.frames
        if max_frames is not None:
            frames = downsample_frames(frames, max_frames)
        return JSONResponse({
            "run_id": src.manifest.run_id,
            "domain": src.manifest.domain,
            "schema_version": src.schema_version,
            "synthetic": src.synthetic,
            "n_frames": len(frames),
            "manifest": src.manifest.model_dump(mode="json"),
            "frames": frames,
        })

    @app.post("/api/runs/{domain}/{run_id}/visualization/render")
    def render_timeline(
        domain: str,
        run_id: str,
        background: BackgroundTasks,
        payload: dict | None = Body(default=None),
    ) -> Any:
        _check_domain(domain)
        root = _root()
        if payload:
            out_dir = root / domain if root is not None else None
            return JSONResponse(bake_from_provenance(domain, run_id, payload, out_dir=out_dir))
        if root is not None:
            background.add_task(
                bake_synthetic, domain, run_id,
                out_dir=root / domain, n_frames=default_total_frames,
                formula_variant=_variant_for(domain, run_id) or "F1",
            )
        return JSONResponse(
            {"run_id": run_id, "domain": domain, "status": "queued"},
            status_code=202,
        )

    @app.get("/sse/runs/{domain}/{run_id}/visualization")
    def sse_stream(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=_MAX_TOTAL),
        fps: float = Query(0.0, ge=0.0, le=240.0),
        max_frames: int | None = Query(default=None, ge=0, le=_MAX_TOTAL),
    ) -> Any:
        _check_domain(domain)
        src = _load_source(_root(), domain, run_id, total)
        frames = (
            downsample_frames(src.frames, max_frames)
            if max_frames is not None
            else adaptive_decimate(src.frames)
        )
        delay = 0.0 if fps <= 0 else 1.0 / fps

        async def gen() -> Any:
            yield sse_event("header", _header_payload(src, len(frames)))
            for frame in frames:
                yield sse_event("frame", frame)
                await asyncio.sleep(delay)
            yield sse_event("done", {})

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @app.websocket("/ws/runs/{domain}/{run_id}/visualization")
    async def ws_stream(websocket: WebSocket, domain: str, run_id: str) -> None:
        if domain not in VALID_DOMAINS:
            await websocket.close(code=1008, reason=f"unknown domain {domain!r}")
            return
        await websocket.accept()
        params = websocket.query_params
        try:
            total = max(1, min(_MAX_TOTAL, int(params.get("total", default_total_frames))))
        except ValueError:
            total = default_total_frames
        try:
            fps = float(params.get("fps", "0"))
        except ValueError:
            fps = 0.0
        delay = 0.0 if fps <= 0 else 1.0 / fps
        src = _load_source(_root(), domain, run_id, total)
        try:
            await websocket.send_bytes(
                encode(envelope("header", seq=0, payload=_header_payload(src, len(src.frames))))
            )
            for seq, frame in enumerate(src.frames, start=1):
                await websocket.send_bytes(encode(envelope(
                    "frame", seq=seq, tau=float(frame.get("tau", 0.0)), payload=frame,
                )))
                # Yield to the loop (keeps a 60 Hz client draw smooth).
                await asyncio.sleep(delay)
            await websocket.send_bytes(encode(envelope("end", seq=len(src.frames) + 1)))
            # Hold the channel until the client closes; returning at once
            # makes starlette close before the client drains queued bytes.
            await websocket.receive()
        except Exception:
            return

    return app


__all__ = ["VALID_DOMAINS", "create_app"]
