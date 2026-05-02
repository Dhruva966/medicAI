"""Dark-activity detector — extended AIS gaps, especially in known STS zones.

Source: AIS gaps from `AISGap` rows. A gap > 6h is suspicious; > 12h or
inside a known STS-transfer zone is critical.
"""

from sqlalchemy.orm import Session

from app.detectors.types import DetectorResult, EvidencePayload
from app.models import AISGap, Vessel

NAME = "dark_activity"
WEIGHT = 180


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    gaps = db.query(AISGap).filter(AISGap.vessel_imo == vessel.imo).all()
    evidence: list[EvidencePayload] = []
    max_value = 0.0

    for gap in gaps:
        if gap.duration_hours < 4:
            continue

        # Severity: scale duration into [0,1], double-weight if inside STS zone.
        v = min(gap.duration_hours / 24.0, 1.0)
        if gap.in_known_sts_zone:
            v = min(v * 1.6, 1.0)
        max_value = max(max_value, v)

        severity = (
            "critical" if v >= 0.8
            else "high" if v >= 0.55
            else "medium" if v >= 0.3
            else "low"
        )

        zone_note = " inside a known STS-transfer corridor" if gap.in_known_sts_zone else ""
        evidence.append(
            EvidencePayload(
                title=f"{gap.duration_hours:.1f}h AIS dark period{zone_note}",
                description=(
                    f"AIS transponder went silent for {gap.duration_hours:.1f}h. "
                    f"Last known position {gap.last_known_lat:.3f}, {gap.last_known_lon:.3f}. "
                    f"Re-acquired at {gap.next_known_lat:.3f}, {gap.next_known_lon:.3f}."
                    + (" Gap straddles a known ship-to-ship transfer zone." if gap.in_known_sts_zone else "")
                ),
                source_type="ais",
                source_ref=f"aisgap://{gap.id}",
                severity=severity,
                confidence=0.85 if gap.in_known_sts_zone else 0.7,
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
