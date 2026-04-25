"""Routing request / decision models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from qcompass_router.transforms.record import TransformRecord


class BackendRequest(BaseModel):
    """User-facing request to route a circuit to a backend."""

    circuit_qasm: str
    shots: int = 1024
    budget_usd: float = 0.0
    max_wallclock_s: int = 3600
    min_fidelity: float = 0.95
    preferred_providers: list[str] = Field(default_factory=list)
    require_real_hardware: bool = False


class RoutingDecision(BaseModel):
    """Result of `Router.decide`.

    Phase-6A locked `transforms_applied: list[str]` (transform names).
    Phase-6B keeps that field for back-compat and adds `transform_records`
    carrying the full `TransformRecord` payload (depth_before/after,
    runtime_ms, config). Calibration metadata lives in its own optional
    field rather than being formatted into `reason`.
    """

    provider: str
    backend: str
    cost_estimate_usd: float
    queue_time_s_estimate: float
    fidelity_estimate: float
    transforms_applied: list[str] = Field(default_factory=list)
    transform_records: list[TransformRecord] = Field(default_factory=list)
    calibration: dict[str, Any] | None = None
    reason: str
