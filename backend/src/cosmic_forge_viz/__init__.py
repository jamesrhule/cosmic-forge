"""cosmic-forge-viz — visualization backend for QCompass runs (PROMPT 7 v2).

Serves per-run, per-domain visualization timelines:

  GET  /api/runs/{domain}/{id}/visualization        # full timeline
  POST /api/runs/{domain}/{id}/visualization/render
  WS   /ws/runs/{domain}/{id}/visualization
  SSE  /sse/runs/{domain}/{id}/visualization

The package is intentionally additive to the frozen UCGLE-F1
backend (lives under ``backend/src/cosmic_forge_viz/`` rather than
``backend/src/ucgle_f1/``). Heavy deps — fastapi>=0.136, zarr>=3,
ormsgpack, h5py, websockets, pydantic-zarr — are SOFT-IMPORTED so
``import cosmic_forge_viz`` succeeds in environments that only
need the schema layer (e.g. tests, docs build, or a frontend that
just consumes the JSON snapshots).

Public surface:

  schema.py    — BaseFrame + per-domain VisualizationFrame Pydantic types
  formulas.py  — F1-F7 active_terms rules (cosmology only)
  phases.py    — phase progression rules
  downsample.py — frame decimation
  protocol.py  — ormsgpack framing + WS / SSE wire format
  baker.py     — Zarr timeline generator
  fixtures.py  — synthetic frame generator
  server.py    — FastAPI app builder
  cli.py       — `cosmic-forge-viz bake / serve` entry point
"""

from __future__ import annotations

from .schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    DomainName,
    GravityFrame,
    HepFrame,
    NuclearFrame,
    StatmechFrame,
    VisualizationFrame,
    VisualizationTimeline,
    frame_class_for_domain,
)

__version__ = "0.1.0"

__all__ = [
    "AmoFrame",
    "BaseFrame",
    "ChemistryFrame",
    "CondmatFrame",
    "CosmologyFrame",
    "DomainName",
    "GravityFrame",
    "HepFrame",
    "NuclearFrame",
    "StatmechFrame",
    "VisualizationFrame",
    "VisualizationTimeline",
    "frame_class_for_domain",
]
