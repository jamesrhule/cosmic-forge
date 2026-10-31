"""FastAPI app builder for the visualisation service (PROMPT 7 v2 §PART B).

The factory returns a :class:`fastapi.FastAPI` instance the
M8-agent server (or a standalone ``uvicorn`` invocation) can mount
under the existing ``/api`` namespace.

Endpoints:
  GET  /api/runs/{domain}/{id}/visualization
       → full timeline JSON (downsampled to ≤256 KB by default).
  POST /api/runs/{domain}/{id}/visualization/render
       → re-bake from the provenance sidecar; returns paths.
  WS   /ws/runs/{domain}/{id}/visualization
       → ormsgpack-framed frames at the requested stride.
  SSE  /sse/runs/{domain}/{id}/visualization
       → JSON-framed frames for clients without a WS path.

FastAPI / starlette / uvicorn / websockets are SOFT-IMPORTED so
``import cosmic_forge_viz.server`` does not fail in environments
that only need the schema. Calling :func:`create_app` raises
``ImportError`` with the install hint when the deps are absent.

NOTE: this module deliberately does NOT use ``from __future__ import
annotations``. FastAPI inspects WS-handler annotations to identify
the ``WebSocket`` parameter; with stringified PEP 563 forward refs
the inspection treats the parameter as a query field and the route
silently rejects the connection.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Optional

from .baker import bake_from_provenance, bake_synthetic
from .downsample import adaptive_decimate, target_count_decimate
from .protocol import encode, envelope, sse_format
from .schema import VisualizationTimeline


_DEFAULT_DOMAIN_LIST = (
    "cosmology", "chemistry", "condmat", "hep", "nuclear", "amo",
)


def _artifacts_root() -> Path:
    env = os.environ.get("VIZ_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "viz"


def _load_timeline(domain: str, run_id: str) -> VisualizationTimeline:
    """Load a timeline from disk; bake a synthetic one if absent."""
    path = _artifacts_root() / domain / f"{run_id}.json"
    if not path.exists():
        bake_synthetic(domain, run_id)
    raw = json.loads(path.read_text())
    return VisualizationTimeline.model_validate(raw)


def create_app(*, viz_root: Optional[Path] = None) -> Any:
    """Return a configured FastAPI app.

    Raises :class:`ImportError` when fastapi / starlette aren't
    importable. Tests that don't need the HTTP layer use the
    :func:`_load_timeline` helper directly.
    """
    try:
        from fastapi import FastAPI, HTTPException, WebSocket  # type: ignore[import-not-found]
        from fastapi.responses import JSONResponse, StreamingResponse  # type: ignore[import-not-found]
    except ImportError as exc:
        msg = (
            "cosmic_forge_viz.server requires fastapi>=0.136 + "
            "uvicorn[standard]>=0.41 + websockets>=14. Install via "
            "`pip install cosmic_forge_viz[viz]` (or the backend "
            "[viz] extra once it lands)."
        )
        raise ImportError(msg) from exc

    app = FastAPI(title="cosmic-forge-viz", version="0.1.0")

    if viz_root is not None:
        os.environ["VIZ_ARTIFACTS"] = str(viz_root)

    @app.get("/api/runs/{domain}/{run_id}/visualization")
    def get_timeline(
        domain: str,
        run_id: str,
        max_frames: int = 256,
    ) -> Any:
        if domain not in _DEFAULT_DOMAIN_LIST:
            raise HTTPException(404, f"unknown domain {domain!r}")
        timeline = _load_timeline(domain, run_id)
        downsampled = target_count_decimate(timeline.frames, max_frames)
        return JSONResponse({
            "run_id": timeline.run_id,
            "domain": timeline.domain,
            "schema_version": timeline.schema_version,
            "n_frames": len(downsampled),
            "frames": downsampled,
        })

    @app.post("/api/runs/{domain}/{run_id}/visualization/render")
    def render_timeline(
        domain: str, run_id: str, payload: Optional[dict] = None,
    ) -> Any:
        if domain not in _DEFAULT_DOMAIN_LIST:
            raise HTTPException(404, f"unknown domain {domain!r}")
        if payload:
            return bake_from_provenance(domain, run_id, payload)
        return bake_synthetic(domain, run_id)

    @app.websocket("/ws/runs/{domain}/{run_id}/visualization")
    async def ws_stream(
        websocket: WebSocket, domain: str, run_id: str,
    ) -> None:
        await websocket.accept()
        timeline = _load_timeline(domain, run_id)
        await websocket.send_bytes(encode(envelope(
            "header", seq=0,
            payload={
                "run_id": timeline.run_id,
                "domain": timeline.domain,
                "n_frames": len(timeline.frames),
            },
        )))
        for seq, frame in enumerate(timeline.frames, start=1):
            await websocket.send_bytes(encode(envelope(
                "frame", seq=seq,
                tau=float(frame.get("tau", 0.0)),
                payload=frame,
            )))
            # Yield to the loop so the frontend's 60 Hz draw stays
            # smooth (≈16 ms target window).
            await asyncio.sleep(0)
        await websocket.send_bytes(encode(envelope("end")))
        # Block on a client-side close; otherwise the ASGI handler
        # returns immediately, which makes starlette emit a close
        # frame before the test client processes the queued bytes
        # (manifesting as WebSocketDisconnect on __enter__).
        try:
            await websocket.receive()
        except Exception:
            return

    @app.get("/sse/runs/{domain}/{run_id}/visualization")
    def sse_stream(domain: str, run_id: str) -> Any:
        if domain not in _DEFAULT_DOMAIN_LIST:
            raise HTTPException(404, f"unknown domain {domain!r}")
        timeline = _load_timeline(domain, run_id)
        downsampled = adaptive_decimate(timeline.frames)

        async def gen():
            yield sse_format(envelope(
                "header", seq=0,
                payload={
                    "run_id": timeline.run_id,
                    "domain": timeline.domain,
                    "n_frames": len(downsampled),
                },
            ))
            for seq, frame in enumerate(downsampled, start=1):
                yield sse_format(envelope(
                    "frame", seq=seq,
                    tau=float(frame.get("tau", 0.0)),
                    payload=frame,
                ))
                await asyncio.sleep(0)
            yield sse_format(envelope("end"))

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app
