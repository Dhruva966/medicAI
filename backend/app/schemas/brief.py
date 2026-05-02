"""Pydantic schemas for the LLM-generated interdiction brief."""

from datetime import datetime

from pydantic import BaseModel


class InterdictionBrief(BaseModel):
    """Structured output of the brief generator."""

    vessel_imo: str
    generated_at: datetime
    headline: str
    summary: str
    evidence: list[str]
    recommended_action: str
    confidence: float  # 0..1
    raw_markdown: str
