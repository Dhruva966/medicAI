"""Evasion-pattern classifier.

Tags vessels with named playbook patterns based on combinations of detector
signals. Used as a labelling layer on top of the rubric.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.detectors import ALL_DETECTORS
from app.models import Vessel


@dataclass
class PlaybookHit:
    name: str
    confidence: float
    evidence: dict


def classify(db: Session, vessel: Vessel) -> list[PlaybookHit]:
    """Return all named playbook patterns this vessel matches."""
    signals: dict[str, float] = {}
    for module in ALL_DETECTORS:
        r = module.detect(db, vessel)
        signals[r.name] = r.value

    hits: list[PlaybookHit] = []

    # Dark-transfer: prolonged AIS gap + STS proximity event.
    if signals.get("dark_activity", 0) >= 0.4 and signals.get("sts_proximity", 0) >= 0.4:
        hits.append(
            PlaybookHit(
                name="dark_transfer",
                confidence=min((signals["dark_activity"] + signals["sts_proximity"]) / 2 + 0.1, 0.95),
                evidence={"dark": signals["dark_activity"], "sts": signals["sts_proximity"]},
            )
        )

    # Flag-hop laundering: identity inconsistencies + sanctions exposure.
    if signals.get("identity_inconsistency", 0) >= 0.5 and signals.get("sanctions_match", 0) >= 0.3:
        hits.append(
            PlaybookHit(
                name="flag_hop_laundering",
                confidence=min(
                    (signals["identity_inconsistency"] + signals["sanctions_match"]) / 2 + 0.05, 0.9
                ),
                evidence={
                    "identity": signals["identity_inconsistency"],
                    "sanctions": signals["sanctions_match"],
                },
            )
        )

    # Identity-swap: kinematic anomaly (positions don't match) + identity issues.
    if signals.get("kinematic_anomaly", 0) >= 0.5 and signals.get("identity_inconsistency", 0) >= 0.3:
        hits.append(
            PlaybookHit(
                name="identity_swap",
                confidence=min(
                    (signals["kinematic_anomaly"] + signals["identity_inconsistency"]) / 2, 0.92
                ),
                evidence={
                    "kinematic": signals["kinematic_anomaly"],
                    "identity": signals["identity_inconsistency"],
                },
            )
        )

    return hits
