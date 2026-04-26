"""FastAPI app factory: REST + SSE + WS.

Endpoints (under the configurable base path, default ``/``):

  GET  /api/runs/{domain}/{id}/manifest
       → JSON manifest (`VisualizationManifest`).
  GET  /api/runs/{domain}/{id}/visualization
       → full timeline as a JSON array of frames.
  POST /api/runs/{domain}/{id}/visualization/render
       → render-job acknowledgement; the live ingest layer that turns
         this into a queued render job is out of scope for the viz
         package, so this endpoint just confirms the run exists.
  GET  /sse/runs/{domain}/{id}/visualization
       → SSE stream of JSON frames (one event per frame, ``event: done``
         at the end).
  WS   /ws/runs/{domain}/{id}/visualization
       → msgpack-encoded frames (or JSON-encoded if `ormsgpack` is
         not installed); a final ``__done__`` text message marks the
         end of the stream.

Frames are sourced from `cosmic_forge_viz.fixtures` until a real
ingest layer hooks ucgle_f1 / qcompass-router runs into the manifest
store.

`fastapi`, `starlette`, and `sse_starlette` are soft-imported inside
`create_app()` so that simply importing this module without the
``viz`` extras installed is harmless.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from cosmic_forge_viz.downsample import downsample_frames
from cosmic_forge_viz.fixtures import synthesize_frames, synthesize_manifest
from cosmic_forge_viz.protocol import encode_frame
from cosmic_forge_viz.schema import BaseFrame, VisualizationManifest

# WebSocket type annotation needs to be resolvable at module import
# time so FastAPI's `get_type_hints()` finds it; fall back to `Any`
# when fastapi isn't installed (the soft-import path).
try:
    from fastapi import WebSocket as _FastapiWebSocket  # type: ignore[import-not-found]

    WebSocket = _FastapiWebSocket
except ImportError:  # pragma: no cover - exercised when extras absent
    if TYPE_CHECKING:
        from fastapi import WebSocket  # noqa: F401
    else:
        WebSocket = Any  # type: ignore[assignment, misc]

_VALID_DOMAINS = {"cosmology", "chemistry", "condmat", "hep", "nuclear", "amo"}


def _frames_for(domain: str, run_id: str, total: int) -> list[BaseFrame]:
    """Synthesize a deterministic frame list keyed off `run_id`.

    Live runs will replace this with a manifest-store lookup; the
    fixture path keeps the API exercised during dev + tests.
    """
    seed = hash(run_id) & 0xFFFFFFFF
    variant = "F1"
    if domain == "cosmology" and run_id.startswith("ucgle-f"):
        # Honour `ucgle-f3-…` style run IDs.
        try:
            variant = "F" + run_id.split("-")[1][1:]
        except (IndexError, ValueError):
            variant = "F1"
    return list(
        synthesize_frames(
            domain,
            total_frames=total,
            seed=seed,
            formula_variant=variant,
        )
    )


def _manifest_for(domain: str, run_id: str, total: int) -> VisualizationManifest:
    variant: str | None = None
    if domain == "cosmology":
        variant = "F1"
        if run_id.startswith("ucgle-f"):
            try:
                variant = "F" + run_id.split("-")[1][1:]
            except (IndexError, ValueError):
                variant = "F1"
    return synthesize_manifest(
        domain=domain,
        run_id=run_id,
        total_frames=total,
        formula_variant=variant,
    )


def create_app(*, default_total_frames: int = 60) -> Any:
    """Build and return the FastAPI app.

    Soft-imports fastapi inside the call so the module can be imported
    without the ``viz`` extras installed.
    """
    try:
        from fastapi import FastAPI, HTTPException, Query, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from sse_starlette.sse import EventSourceResponse
    except ImportError as exc:  # pragma: no cover - exercised by unit tests
        raise RuntimeError(
            "cosmic_forge_viz.server requires the `viz` extras "
            "(`pip install cosmic-forge[viz]`)."
        ) from exc

    app = FastAPI(
        title="cosmic-forge-viz",
        version="0.1.0",
        description="Cross-domain visualization streaming for the cosmic-forge stack.",
    )

    # The frontend dev server runs on a different port; allow it to talk
    # to the viz API without round-tripping through a proxy.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    def _check_domain(domain: str) -> None:
        if domain not in _VALID_DOMAINS:
            raise HTTPException(status_code=404, detail=f"unknown domain {domain!r}")

    @app.get("/api/runs/{domain}/{run_id}/manifest")
    def get_manifest(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=2000),
    ) -> JSONResponse:
        _check_domain(domain)
        manifest = _manifest_for(domain, run_id, total)
        return JSONResponse(manifest.model_dump(mode="json"))

    @app.get("/api/runs/{domain}/{run_id}/visualization")
    def get_full_timeline(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=2000),
        max_frames: int | None = Query(default=None, ge=1, le=2000),
    ) -> JSONResponse:
        _check_domain(domain)
        frames = _frames_for(domain, run_id, total)
        if max_frames is not None and max_frames < len(frames):
            frames = downsample_frames(frames, max_frames)
        return JSONResponse(
            {
                "manifest": _manifest_for(domain, run_id, total).model_dump(mode="json"),
                "frames": [f.model_dump(mode="json") for f in frames],
            }
        )

    @app.post("/api/runs/{domain}/{run_id}/visualization/render")
    def post_render(domain: str, run_id: str) -> JSONResponse:
        _check_domain(domain)
        # Live ingest path is out of scope; ack so the frontend's render
        # button has something to call.
        return JSONResponse(
            {"run_id": run_id, "domain": domain, "status": "queued"},
            status_code=202,
        )

    @app.get("/sse/runs/{domain}/{run_id}/visualization")
    async def sse_visualization(
        domain: str,
        run_id: str,
        total: int = Query(default_total_frames, ge=1, le=2000),
        fps: float = Query(0.0, ge=0.0, le=240.0),
    ) -> Any:
        _check_domain(domain)
        frames = _frames_for(domain, run_id, total)

        async def event_gen() -> Any:
            delay = 0.0 if fps <= 0 else 1.0 / fps
            for f in frames:
                yield {
                    "event": "frame",
                    "data": json.dumps(f.model_dump(mode="json")),
                }
                if delay > 0:
                    await asyncio.sleep(delay)
            yield {"event": "done", "data": "{}"}

        return EventSourceResponse(event_gen())

    @app.websocket("/ws/runs/{domain}/{run_id}/visualization")
    async def ws_visualization(
        websocket: WebSocket,
        domain: str,
        run_id: str,
    ) -> None:
        if domain not in _VALID_DOMAINS:
            await websocket.close(code=1008, reason=f"unknown domain {domain!r}")
            return
        await websocket.accept()
        try:
            params = websocket.query_params
            try:
                total = int(params.get("total", default_total_frames))
            except ValueError:
                total = default_total_frames
            try:
                fps = float(params.get("fps", "0"))
            except ValueError:
                fps = 0.0

            frames = _frames_for(domain, run_id, total)
            delay = 0.0 if fps <= 0 else 1.0 / fps
            for f in frames:
                await websocket.send_bytes(encode_frame(f))
                if delay > 0:
                    await asyncio.sleep(delay)
            await websocket.send_text("__done__")
        except WebSocketDisconnect:
            return
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    return app


__all__ = ["create_app"]
