"""Introspection tools."""

from __future__ import annotations

from pydantic import BaseModel

from ...domain import Capabilities, ToolSpec
from ..memory.store import APPROVAL_SCOPES


class DescribeToolInput(BaseModel):
    name: str


def list_tools() -> list[ToolSpec]:
    # Import here to avoid a cycle: tools/__init__ aggregates ours.
    from . import ALL_TOOL_SPECS
    return list(ALL_TOOL_SPECS)


def describe_tool(name: str) -> ToolSpec:
    for spec in list_tools():
        if spec.name == name:
            return spec
    from ...domain import ServiceError

    raise ServiceError("NOT_FOUND", f"no tool '{name}'")


def get_capabilities() -> Capabilities:
    from ..models.registry import list_models

    return Capabilities(
        schemaVersion="1",
        tools=[s.name for s in list_tools()],
        models=list_models(),
        # One list of approval scopes (memory.store.APPROVAL_SCOPES, R20).
        approvalScopesRequired={scope: [scope] for scope in APPROVAL_SCOPES},
        precisionPolicy={
            "default_rtol": 1e-10,
            "default_atol": 1e-12,
            "unitarity_tol": 1e-12,
            "mpmath_dps": 50,
            "max_eta_budget": 5e-3,
        },
    )


def _schema(m: type[BaseModel]) -> dict:
    return m.model_json_schema()


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="list_tools", family="introspection",
        description="Return every tool spec exposed by the server.",
        approvalRequired=False,
        inputSchema={}, outputSchema={"type": "array"},
    ),
    ToolSpec(
        name="describe_tool", family="introspection",
        description="Return a single tool spec by name.",
        approvalRequired=False,
        inputSchema=_schema(DescribeToolInput),
        outputSchema=_schema(ToolSpec),
    ),
    ToolSpec(
        name="get_capabilities", family="introspection",
        description="Return the server capability envelope.",
        approvalRequired=False,
        inputSchema={}, outputSchema=_schema(Capabilities),
    ),
]
