"""Pydantic schemas for risk scores."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ScoreComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    weight: int
    value: float
    contribution: int
    evidence: dict[str, Any] = {}


class ScoreOut(BaseModel):
    """Full per-vessel score with rubric breakdown."""

    model_config = ConfigDict(from_attributes=True)

    vessel_imo: str
    score: int  # 0-1000
    band: str  # low | medium | high | critical
    computed_at: datetime
    components: list[ScoreComponentOut] = []
