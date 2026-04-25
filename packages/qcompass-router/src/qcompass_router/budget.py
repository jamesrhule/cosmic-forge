"""Budget models. Phase-6A: data containers only; enforcement lands in 6B."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserBudget(BaseModel):
    """Per-user cap. Enforcement is Phase-6B."""

    user_id: str
    monthly_cap_usd: float = 0.0
    spent_usd: float = 0.0
    period_start: datetime | None = None

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.monthly_cap_usd - self.spent_usd)


class ProjectBudget(BaseModel):
    """Per-project cap, optionally shared across users."""

    project_id: str
    monthly_cap_usd: float = 0.0
    spent_usd: float = 0.0
    member_user_ids: list[str] = Field(default_factory=list)
    period_start: datetime | None = None

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.monthly_cap_usd - self.spent_usd)
