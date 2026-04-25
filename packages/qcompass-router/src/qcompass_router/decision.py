"""Routing request / decision models."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    """Result of `Router.decide`."""

    provider: str
    backend: str
    cost_estimate_usd: float
    queue_time_s_estimate: float
    fidelity_estimate: float
    transforms_applied: list[str] = Field(default_factory=list)
    reason: str
