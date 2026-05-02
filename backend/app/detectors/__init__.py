"""Deception detectors. Each module exports `detect(db, vessel) -> DetectorResult`."""

from app.detectors import (
    dark_activity,
    identity_inconsistency,
    kinematic_anomaly,
    route_plausibility,
    sanctions_match,
    sts_proximity,
)
from app.detectors.types import DetectorResult, EvidencePayload

ALL_DETECTORS = [
    dark_activity,
    kinematic_anomaly,
    sts_proximity,
    sanctions_match,
    identity_inconsistency,
    route_plausibility,
]

__all__ = ["ALL_DETECTORS", "DetectorResult", "EvidencePayload"]
