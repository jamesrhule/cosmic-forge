"""Budget envelopes for the router.

PROMPT 6A defines the types and a `BudgetExceeded` error raised
when a request asks for real hardware with no money. PROMPT 6B
plugs these models into the router's spend tracker.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BudgetExceeded(Exception):
    """Raised when a routing decision would exceed the request budget.

    Carries an HTTP-style error code (``code``) the agent + frontend
    can branch on without parsing the message.
    """

    code: str = "BUDGET_EXCEEDED"

    def __init__(self, message: str, *, code: str = "BUDGET_EXCEEDED") -> None:
        super().__init__(message)
        self.code = code


class UserBudget(BaseModel):
    """Per-user spend envelope. Persisted later by PROMPT 6B."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    monthly_cap_usd: float = Field(ge=0.0)
    spent_usd: float = Field(default=0.0, ge=0.0)
    period_start: datetime = Field(default_factory=datetime.utcnow)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.monthly_cap_usd - self.spent_usd)


class ProjectBudget(BaseModel):
    """Aggregate envelope for a research project (multiple users)."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    monthly_cap_usd: float = Field(ge=0.0)
    spent_usd: float = Field(default=0.0, ge=0.0)
    members: list[str] = Field(default_factory=list)
    tier: Literal["free", "starter", "research", "production"] = "free"
