"""Route-plausibility detector — port history vs current course.

Hackathon-grade heuristic: if the vessel's recent port-call history is
dominated by a region that doesn't match its current last-known position,
flag as implausible. This is intentionally simple — replace with proper
shortest-path-over-water reasoning later.
"""

import math

from sqlalchemy.orm import Session

from app.detectors.types import DetectorResult, EvidencePayload
from app.models import PortCall, Vessel

NAME = "route_plausibility"
WEIGHT = 100

# Rough port-coordinates for common ports referenced in the seed scenario.
PORT_COORDS: dict[str, tuple[float, float]] = {
    "Novorossiysk": (44.72, 37.78),
    "Primorsk": (60.36, 28.62),
    "Ust-Luga": (59.66, 28.40),
    "Kozmino": (42.78, 133.07),
    "Sikka": (22.43, 69.83),
    "Vadinar": (22.45, 69.74),
    "Singapore": (1.27, 103.75),
    "Fujairah": (25.12, 56.34),
    "Rotterdam": (51.92, 4.48),
    "Houston": (29.73, -95.26),
    "Long Beach": (33.74, -118.20),
    "Shanghai": (31.34, 121.65),
    "Yokohama": (35.45, 139.65),
    "Lagos": (6.43, 3.40),
}


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R_NM = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(a))


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    if vessel.last_seen_lat is None or vessel.last_seen_lon is None:
        return DetectorResult(name=NAME, weight=WEIGHT, value=0.0)

    calls = (
        db.query(PortCall)
        .filter(PortCall.vessel_imo == vessel.imo)
        .order_by(PortCall.arrival_at.desc())
        .limit(5)
        .all()
    )
    if not calls:
        return DetectorResult(name=NAME, weight=WEIGHT, value=0.0)

    # Distance from last-known position to nearest port the vessel has called recently.
    coords = [PORT_COORDS.get(c.port_name) for c in calls]
    coords = [c for c in coords if c]
    if not coords:
        return DetectorResult(name=NAME, weight=WEIGHT, value=0.0)

    nearest_nm = min(
        _haversine_nm(vessel.last_seen_lat, vessel.last_seen_lon, lat, lon)
        for lat, lon in coords
    )

    # Implausible if last-known is > 4000 nm from any recently-called port.
    if nearest_nm <= 4000:
        return DetectorResult(name=NAME, weight=WEIGHT, value=0.0)

    v = min((nearest_nm - 4000) / 4000, 1.0)
    visited = ", ".join(sorted({c.port_name for c in calls}))
    return DetectorResult(
        name=NAME,
        weight=WEIGHT,
        value=v,
        evidence=[
            EvidencePayload(
                title=f"Last-known {nearest_nm:.0f} nm from any recent port",
                description=(
                    f"Recent port history: {visited}. Last AIS fix at "
                    f"{vessel.last_seen_lat:.3f}, {vessel.last_seen_lon:.3f} sits "
                    f"{nearest_nm:.0f} nm from the nearest of those — inconsistent with "
                    "the vessel's stated trade pattern."
                ),
                source_type="ais",
                source_ref=f"vessel://{vessel.imo}/last-fix",
                severity="high" if v >= 0.6 else "medium",
                confidence=0.7,
                geometry={
                    "type": "Point",
                    "coordinates": [vessel.last_seen_lon, vessel.last_seen_lat],
                },
                score_contribution=round(WEIGHT * v),
            )
        ],
    )
