"""Router decision types.

``RouterRequest`` is intentionally a separate type from
``qcompass_core.BackendRequest`` (the existing manifest envelope).
The qcompass-core type stays byte-stable so every existing qfull-*
plugin keeps working unchanged. The router consumes
``RouterRequest`` directly; downstream calls into qcompass-core's
M14 router still use ``BackendRequest``.

We export ``BackendRequest`` as an alias of ``RouterRequest`` so
spec readers who reach for ``qcompass_router.BackendRequest`` (the
name PROMPT 6A's body uses) get the right type — but the canonical
name in code is ``RouterRequest``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RouterRequest(BaseModel):
    """Inputs the router uses to select a backend.

    The qcompass-core ``Manifest.backend_request`` envelope (with
    ``kind / target / priority / shots / seed / max_runtime_seconds``)
    is independent and untouched.
    """

    model_config = ConfigDict(extra="forbid")

    circuit_qasm: str = Field(
        default="",
        description=(
            "OpenQASM source. Empty during PROMPT 6A; PROMPT 6B uses "
            "it to route circuit-aware estimators."
        ),
    )
    shots: int = Field(default=1024, ge=1)
    budget_usd: float = Field(default=0.0, ge=0.0)
    max_wallclock_s: int = Field(default=3600, gt=0)
    min_fidelity: float = Field(default=0.95, ge=0.0, le=1.0)
    preferred_providers: list[str] = Field(default_factory=list)
    require_real_hardware: bool = False


# Spec alias so callers reading PROMPT 6A literally get the right type.
BackendRequest = RouterRequest


class TransformRecord(BaseModel):
    """Lightweight record of a transform applied during routing.

    Filled out by PROMPT 6B; PROMPT 6A only carries the empty list
    on every decision.
    """

    model_config = ConfigDict(extra="forbid")

    name: Literal["aqc_tensor", "mpf", "obp", "cutting"]
    parameters: dict[str, float | int | str | bool] = Field(default_factory=dict)
    fidelity_loss: float = 0.0
    notes: str = ""


class RoutingDecision(BaseModel):
    """The router's verdict.

    Audit ``A-router-4`` requires ``cost_estimate_usd``,
    ``queue_time_s_estimate``, and ``fidelity_estimate`` on every
    decision; we keep them required (no defaults) so missing values
    surface as Pydantic errors at construction time.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str
    backend: str
    cost_estimate_usd: float = Field(ge=0.0)
    queue_time_s_estimate: float = Field(ge=0.0)
    fidelity_estimate: float = Field(ge=0.0, le=1.0)
    transforms_applied: list[TransformRecord] = Field(default_factory=list)
    reason: str
