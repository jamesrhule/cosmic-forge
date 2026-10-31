"""Typed response models for every HTTP route (P3-06).

Each route declares ``response_model=`` with one of these (or a domain
model from ``ucgle_f1.domain``), so the OpenAPI document is complete and
responses are validated on the way out. Streaming routes (SSE) and
``/metrics`` declare their media type instead.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Generic ────────────────────────────────────────────────────


class OkResponse(_Out):
    ok: Literal[True] = True


class HealthResponse(_Out):
    status: Literal["ok"] = "ok"


class ReadinessCheck(_Out):
    ok: bool
    detail: str = ""


class ReadinessResponse(_Out):
    status: Literal["ready", "not_ready"]
    checks: dict[str, ReadinessCheck]


# ── Legacy /api/runs, approvals, MCP ───────────────────────────


class StartRunResponse(_Out):
    runId: str


class ApprovalResponse(_Out):
    tokenId: str
    scopes: list[str]
    expiresAt: str | None


class ToolInvocationResponse(_Out):
    ok: Literal[True] = True
    output: JsonValue = Field(description="The tool's own result model, serialised.")


# ── /api/qcompass ──────────────────────────────────────────────


class DomainEntry(_Out):
    id: str
    label: str


class DomainsResponse(_Out):
    domains: list[DomainEntry]


class ManifestJsonSchema(RootModel[dict[str, JsonValue]]):
    """A domain's manifest JSON Schema document."""


class SubmitRunResponse(_Out):
    runId: str
    domain: str
    status: str
    provenanceSidecar: str
    classicalReferenceHash: str


class SidecarProvenance(_Out):
    classical_reference_hash: str
    calibration_hash: str | None = None
    error_mitigation: JsonValue = None


class ProvenanceSidecar(_Out):
    schemaVersion: int
    runId: str
    domain: str
    status: str
    createdAt: str
    manifest: JsonValue
    provenance: SidecarProvenance


class VisualizationResponse(_Out):
    run_id: str
    domain: str
    schema_version: int
    n_frames: int
    frames: list[dict[str, JsonValue]]


# ── /api/scans ─────────────────────────────────────────────────


class ScanEnvelope(_Out):
    scanId: str
    domain: str
    kind: str
    axes: dict[str, JsonValue]
    payload: dict[str, JsonValue]
    provenance: dict[str, JsonValue]
    createdAt: str


class ScanListResponse(_Out):
    scans: list[ScanEnvelope]


# ── Media types for non-JSON routes ────────────────────────────


SSE_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "Server-sent event stream.",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    },
}


__all__ = [
    "ApprovalResponse",
    "DomainEntry",
    "DomainsResponse",
    "HealthResponse",
    "ManifestJsonSchema",
    "OkResponse",
    "ProvenanceSidecar",
    "ReadinessCheck",
    "ReadinessResponse",
    "SSE_RESPONSES",
    "ScanEnvelope",
    "ScanListResponse",
    "SidecarProvenance",
    "StartRunResponse",
    "SubmitRunResponse",
    "ToolInvocationResponse",
    "VisualizationResponse",
]
