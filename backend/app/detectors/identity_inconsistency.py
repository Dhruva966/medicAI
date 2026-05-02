"""Identity-inconsistency detector — flag-hopping and identity drift."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.detectors.types import DetectorResult, EvidencePayload
from app.models import FlagHistory, Vessel

NAME = "identity_inconsistency"
WEIGHT = 110

# Convenience flags (Liberia, Panama, Marshall Islands, etc.) carry more weight.
FLAGS_OF_CONVENIENCE = {
    "Liberia", "Panama", "Marshall Islands", "Cook Islands", "Comoros",
    "Cameroon", "Sierra Leone", "Saint Kitts and Nevis", "Mongolia",
    "Tanzania", "Togo", "Gabon",
}


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    history = (
        db.query(FlagHistory)
        .filter(FlagHistory.vessel_imo == vessel.imo)
        .order_by(FlagHistory.start_date.desc())
        .all()
    )
    evidence: list[EvidencePayload] = []
    max_value = 0.0

    if len(history) >= 2:
        # Count flag changes within the past 12 months.
        if history[0].start_date is not None:
            twelve_mo = history[0].start_date - timedelta(days=365)
            recent = [h for h in history if h.start_date and h.start_date >= twelve_mo]
            n_changes = max(len(recent) - 1, 0)
        else:
            n_changes = 0

        if n_changes >= 2:
            v = min(0.55 + 0.15 * (n_changes - 2), 1.0)
            max_value = max(max_value, v)
            evidence.append(
                EvidencePayload(
                    title=f"{n_changes} flag changes in 12 months",
                    description=(
                        f"Recent flag sequence: "
                        + " → ".join(reversed([h.flag for h in history[: n_changes + 1]]))
                        + ". Rapid flag-hopping is a documented sanctions-evasion tactic."
                    ),
                    source_type="registry",
                    source_ref="equasis://flag-history",
                    severity="high",
                    confidence=0.85,
                    score_contribution=round(WEIGHT * v),
                )
            )

        # Current flag is a flag of convenience after a non-FOC history.
        cur = history[0].flag
        prev_flags = {h.flag for h in history[1:]}
        if cur in FLAGS_OF_CONVENIENCE and prev_flags and not prev_flags.issubset(FLAGS_OF_CONVENIENCE):
            v = 0.5
            max_value = max(max_value, v)
            evidence.append(
                EvidencePayload(
                    title=f"Switched to flag of convenience ({cur})",
                    description=(
                        f"Vessel re-flagged from {sorted(prev_flags)} to {cur}, a recognized "
                        "flag-of-convenience jurisdiction."
                    ),
                    source_type="registry",
                    source_ref="equasis://flag-history",
                    severity="medium",
                    confidence=0.75,
                    score_contribution=round(WEIGHT * v),
                )
            )

    # Missing or weak identity (no MMSI, generic name) — light signal.
    if not vessel.mmsi:
        v = 0.25
        max_value = max(max_value, v)
        evidence.append(
            EvidencePayload(
                title="MMSI not on record",
                description="No MMSI recorded for this vessel — partial identity coverage.",
                source_type="registry",
                source_ref="equasis://identity",
                severity="low",
                confidence=0.6,
                score_contribution=round(WEIGHT * v),
            )
        )

    return DetectorResult(name=NAME, weight=WEIGHT, value=max_value, evidence=evidence)
