"""cosmic-forge-viz — per-domain visualization streaming + bake.

Sibling package of ``ucgle_f1`` under ``backend/src/``, installed via
the backend ``[viz]`` extras. Heavy deps (fastapi, zarr, ormsgpack) are
soft-imported so ``import cosmic_forge_viz`` works for schema-only
consumers.

Public surface:

  schema.py     — BaseFrame + per-domain frame types, manifest, timeline
  formulas.py   — UCGLE F1–F7 active-term rules + cross-domain registry
  phases.py     — phase progression rules
  downsample.py — frame decimation
  protocol.py   — envelope framing (msgpack / JSON) for WS + SSE
  baker.py      — JSON snapshot + Zarr v3 store writer/readers
  fixtures.py   — deterministic synthetic frame generators
  server.py     — FastAPI app factory (REST + SSE + WS)
  cli.py        — ``cosmic-forge-viz bake / demo / serve / check``
"""

from __future__ import annotations

from .schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    Domain,
    DomainName,
    GravityFrame,
    HepFrame,
    NuclearFrame,
    ParticleObservableEntry,
    Phase,
    StatmechFrame,
    VisualizationFrame,
    VisualizationManifest,
    VisualizationTimeline,
    frame_class_for_domain,
    frame_for_domain,
)

__version__ = "0.1.0"

__all__ = [
    "AmoFrame",
    "BaseFrame",
    "ChemistryFrame",
    "CondmatFrame",
    "CosmologyFrame",
    "Domain",
    "DomainName",
    "GravityFrame",
    "HepFrame",
    "NuclearFrame",
    "ParticleObservableEntry",
    "Phase",
    "StatmechFrame",
    "VisualizationFrame",
    "VisualizationManifest",
    "VisualizationTimeline",
    "frame_class_for_domain",
    "frame_for_domain",
]
