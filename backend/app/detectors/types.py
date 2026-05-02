"""Shared types for detectors."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EvidencePayload:
    """One evidence record produced by a detector before persistence."""

    title: str
    description: str
    source_type: str  # ais|sanctions|registry|satellite|port
    source_ref: str
    severity: str = "medium"  # low|medium|high|critical
    confidence: float = 0.7
    start_time: datetime | None = None
    end_time: datetime | None = None
    geometry: dict[str, Any] = field(default_factory=dict)
    score_contribution: int = 0


@dataclass
class DetectorResult:
    """Aggregate output of a detector for one vessel."""

    name: str  # rubric component name
    weight: int  # rubric weight 0-...
    value: float  # aggregated severity 0..1
    evidence: list[EvidencePayload] = field(default_factory=list)

    @property
    def contribution(self) -> int:
        return round(self.weight * self.value)
