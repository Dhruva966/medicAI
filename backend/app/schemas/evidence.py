"""Pydantic schemas for evidence records."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvidenceOut(BaseModel):
    """Public shape of one evidence record. Mirrors the AGENTS.md spec."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_imo: str
    detector_name: str
    title: str
    description: str
    source_type: str
    source_ref: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    geometry: dict[str, Any] = {}
    severity: str
    confidence: float
    score_contribution: int
    analyst_notes: str | None = None
    created_at: datetime
