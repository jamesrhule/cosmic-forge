"""Bake a per-run visualisation timeline to disk (PROMPT 7 v2 §PART B).

The baker takes a run's classical/quantum result (or a synthetic
fixture) and emits a Zarr-backed timeline at
``${VIZ_ARTIFACTS}/<domain>/<id>.zarr`` plus a JSON snapshot at
``<id>.json`` so the frontend can fetch a static slice without
spinning up the WS channel.

Zarr is soft-imported: if the wheel is unavailable the baker falls
back to a JSON-only payload (still served by the REST endpoint).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .fixtures import build_synthetic_timeline
from .schema import VisualizationTimeline


def _default_artifacts_root() -> Path:
    env = os.environ.get("VIZ_ARTIFACTS")
    if env:
        return Path(env)
    return Path.home() / ".qcompass" / "viz"


def bake_synthetic(
    domain: str,
    run_id: str,
    *,
    out_dir: Path | None = None,
    n_frames: int = 60,
    tau_max: float = 60.0,
    couplings: dict[str, float] | None = None,
    model_domain: str = "1+1D_toy",
) -> dict[str, Any]:
    """Bake a synthetic timeline and persist a JSON snapshot.

    Returns the output paths and basic shape stats. Zarr serialisation
    is attempted last; failure is non-fatal (JSON path is the canonical
    one for v1 of the visualisation pipeline).
    """
    out_dir = out_dir or (_default_artifacts_root() / domain)
    out_dir.mkdir(parents=True, exist_ok=True)

    timeline = build_synthetic_timeline(
        domain, run_id,
        n_frames=n_frames, tau_max=tau_max,
        couplings=couplings, model_domain=model_domain,
    )

    json_path = out_dir / f"{run_id}.json"
    json_path.write_text(timeline.model_dump_json(indent=2))

    zarr_path: Path | None = None
    try:
        import zarr  # type: ignore[import-not-found]
        zarr_path = out_dir / f"{run_id}.zarr"
        _write_zarr(timeline, zarr_path, zarr_module=zarr)
    except ImportError:
        zarr_path = None
    except Exception:  # pragma: no cover — corrupted zarr install
        zarr_path = None

    return {
        "domain": domain,
        "run_id": run_id,
        "json_path": str(json_path),
        "zarr_path": str(zarr_path) if zarr_path else None,
        "n_frames": len(timeline.frames),
    }


def _write_zarr(
    timeline: VisualizationTimeline, path: Path, *, zarr_module: Any,
) -> None:
    """Write a flat record per frame (lazy zarr import already done)."""
    root = zarr_module.open(str(path), mode="w")
    root.attrs["run_id"] = timeline.run_id
    root.attrs["domain"] = timeline.domain
    root.attrs["schema_version"] = timeline.schema_version
    root.attrs["n_frames"] = len(timeline.frames)
    # Single dataset of JSON-serialised frames keeps the schema
    # fully forward-compatible with the v2 frame type union.
    blob = json.dumps(timeline.frames, separators=(",", ":")).encode("utf-8")
    root.create_dataset("frames_json", data=[blob], dtype=object)


def bake_from_provenance(
    domain: str,
    run_id: str,
    provenance_payload: dict[str, Any],
    *,
    out_dir: Path | None = None,
    n_frames: int = 60,
    tau_max: float = 60.0,
) -> dict[str, Any]:
    """Hook for the v2 §POST /visualization/render endpoint.

    The provenance sidecar's ``manifest.problem`` carries the
    couplings / kind / model_domain dimensions the synthetic
    builder consumes. Real numerical baking lands when each plugin
    grows a per-frame ``Result.timeline()`` accessor.
    """
    manifest = provenance_payload.get("manifest", {})
    problem = manifest.get("problem", {})
    couplings = (
        problem.get("couplings")
        if isinstance(problem.get("couplings"), dict) else None
    )
    model_domain = (
        provenance_payload.get("model_domain") or "1+1D_toy"
    )
    return bake_synthetic(
        domain, run_id,
        out_dir=out_dir,
        n_frames=n_frames, tau_max=tau_max,
        couplings=couplings,
        model_domain=str(model_domain),
    )
