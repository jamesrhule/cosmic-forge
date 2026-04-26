"""cosmic-forge-viz: per-domain visualization streaming + bake.

Sibling Python package living under `backend/src/`. Installed via the
`backend` package's `[viz]` optional extras so that the core ucgle_f1
stack is unchanged when visualization deps (fastapi, zarr, ormsgpack)
aren't wanted.

Public surface:
  * `schema` — Pydantic per-domain VisualizationFrame types.
  * `baker` — Zarr timeline writer.
  * `fixtures` — synthetic frame generators (used by tests + the index
    route's empty-state demo runs).
  * `protocol` — msgpack framing for the WS endpoint.
  * `formulas` — UCGLE F1–F7 active_terms rules.
  * `phases` — phase-tag helpers.
  * `downsample` — frame-level decimation for low-bandwidth clients.
  * `server` — FastAPI app factory (WS + SSE + REST).
  * `cli` — `cosmic-forge-viz` typer command.
"""

from __future__ import annotations

from cosmic_forge_viz.schema import (
    AmoFrame,
    BaseFrame,
    ChemistryFrame,
    CondmatFrame,
    CosmologyFrame,
    Domain,
    HepFrame,
    NuclearFrame,
    VisualizationManifest,
    frame_for_domain,
)

__all__ = [
    "AmoFrame",
    "BaseFrame",
    "ChemistryFrame",
    "CondmatFrame",
    "CosmologyFrame",
    "Domain",
    "HepFrame",
    "NuclearFrame",
    "VisualizationManifest",
    "frame_for_domain",
]

__version__ = "0.1.0"
