"""TransformRecord: one entry per applied circuit transform."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TransformName = Literal["aqc_tensor", "mpf", "obp", "cutting"]


class TransformRecord(BaseModel):
    """Result of applying a single transform to a circuit."""

    model_config = ConfigDict(frozen=True)

    name: TransformName
    config: dict[str, Any] = Field(default_factory=dict)
    depth_before: int = 0
    depth_after: int = 0
    runtime_ms: float = 0.0
