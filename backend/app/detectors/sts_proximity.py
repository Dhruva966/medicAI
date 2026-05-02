"""STS-proximity detector — low-speed close encounters in open water."""

from sqlalchemy.orm import Session

from app.detectors.types import DetectorResult, EvidencePayload
from app.models import Encounter, STSTransfer, Vessel

NAME = "sts_proximity"
WEIGHT = 150


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    encounters = (
        db.query(Encounter)
        .filter(
            (Encounter.vessel_a_imo == vessel.imo) | (Encounter.vessel_b_imo == vessel.imo)
        )
        .all()
    )
    evidence: list[EvidencePayload] = []
    max_value = 0.0

    for enc in encounters:
        if enc.in_port:
            continue
        if enc.duration_hours < 0.5:
            continue

        partner = enc.vessel_b_imo if enc.vessel_a_imo == vessel.imo else enc.vessel_a_imo
        sts: STSTransfer | None = enc.sts_transfer

        # Severity: long duration + classified transfer + known zone all push higher.
        v = min(enc.duration_hours / 6.0, 1.0)
        if sts and sts.in_known_zone:
            v = min(v + 0.3, 1.0)
        if sts and sts.transfer_type == "oil":
            v = min(v + 0.2, 1.0)
        max_value = max(max_value, v)

        sev = "critical" if v >= 0.85 else "high" if v >= 0.6 else "medium"
        sts_note = ""
        if sts:
            vol = f", est. {sts.estimated_volume:.0f} t" if sts.estimated_volume else ""
            sts_note = f" Classified as {sts.transfer_type} STS{vol}."
            if sts.in_known_zone:
                sts_note += " Inside a known STS-transfer corridor."

        evidence.append(
            EvidencePayload(
                title=f"{enc.duration_hours:.1f}h open-water encounter with IMO {partner}",
                description=(
                    f"Low-speed proximity event lasting {enc.duration_hours:.1f}h at "
                    f"{enc.lat:.3f}, {enc.lon:.3f}. No port-call recorded for either vessel "
                    f"during this window.{sts_note}"
                ),
                source_type="ais",
                source_ref=f"encounter://{enc.id}",
                severity=sev,
                confidence=0.8 if sts else 0.65,
                start_time=enc.start_at,
                end_time=enc.end_at,
                geometry={"type": "Point", "coordinates": [enc.lon, enc.lat]},
                score_contribution=round(WEIGHT * v),
            )
        )

    return DetectorResult(name=NAME, weight=WEIGHT, value=max_value, evidence=evidence)
