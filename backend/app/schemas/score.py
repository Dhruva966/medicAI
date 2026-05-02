"""Pydantic schemas for risk scores."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.evidence import EvidenceOut


class ScoreComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    weight: int
    value: float
    contribution: int
    evidence_records: list[EvidenceOut] = []


class ScoreOut(BaseModel):
    """Full per-vessel score with rubric breakdown and evidence."""

    model_config = ConfigDict(from_attributes=True)

    vessel_imo: str
    score: int  # 0-1000
    band: str  # low | medium | high | critical
    recommendation: str
    computed_at: datetime
    components: list[ScoreComponentOut] = []
