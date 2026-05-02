"""Kinematic-anomaly detector — implausible jumps and speeds.

If a vessel's last-known position before a dark period and next-known position
after it would require a speed > 30 knots to traverse, the AIS data is lying
or the identity is being swapped mid-voyage.
"""

import math

from sqlalchemy.orm import Session

from app.detectors.types import DetectorResult, EvidencePayload
from app.models import AISGap, Vessel

NAME = "kinematic_anomaly"
WEIGHT = 120
MAX_PLAUSIBLE_KNOTS = 30.0


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    R_NM = 3440.065  # earth radius in nautical miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(a))


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    gaps = db.query(AISGap).filter(AISGap.vessel_imo == vessel.imo).all()
    evidence: list[EvidencePayload] = []
    max_value = 0.0

    for gap in gaps:
        if not all([gap.last_known_lat, gap.last_known_lon, gap.next_known_lat, gap.next_known_lon]):
            continue
        if gap.duration_hours <= 0:
            continue

        nm = _haversine_nm(
            gap.last_known_lat, gap.last_known_lon,
            gap.next_known_lat, gap.next_known_lon,
        )
        implied_knots = nm / gap.duration_hours
        if implied_knots <= MAX_PLAUSIBLE_KNOTS:
            continue

        # value scales from 0 (at MAX) to 1 (at 2x MAX)
        v = min((implied_knots - MAX_PLAUSIBLE_KNOTS) / MAX_PLAUSIBLE_KNOTS, 1.0)
        max_value = max(max_value, v)

        evidence.append(
            EvidencePayload(
                title=f"Implied speed {implied_knots:.1f} kn over {gap.duration_hours:.1f}h gap",
                description=(
                    f"Re-acquisition position is {nm:.0f} nm from last-known. "
                    f"Implied transit speed of {implied_knots:.1f} knots exceeds the "
                    f"plausible {MAX_PLAUSIBLE_KNOTS:.0f} kn ceiling for this hull class. "
                    "Either the AIS positions are spoofed or two different vessels are sharing one identity."
                ),
                source_type="ais",
                source_ref=f"aisgap://{gap.id}",
                severity="critical" if v >= 0.7 else "high",
                confidence=0.9,
                start_time=gap.start_at,
                end_time=gap.end_at,
                geometry={
                    "type": "LineString",
                    "coordinates": [
                        [gap.last_known_lon, gap.last_known_lat],
                        [gap.next_known_lon, gap.next_known_lat],
                    ],
                },
                score_contribution=round(WEIGHT * v),
            )
        )

    return DetectorResult(name=NAME, weight=WEIGHT, value=max_value, evidence=evidence)
