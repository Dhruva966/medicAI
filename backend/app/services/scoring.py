"""Deception-score rubric engine.

Runs every detector against a vessel, persists ScoreComponent + Evidence
rows, and returns the combined ScoreOut.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.detectors import ALL_DETECTORS
from app.models import Evidence, RiskScore, ScoreComponent, Vessel
from app.schemas import ScoreOut


# Maximum possible from the six implemented detectors. The total score is
# normalized to 0-1000 in the response.
RUBRIC_MAX = sum(d.WEIGHT for d in ALL_DETECTORS)


def band_for(score_0_1000: int) -> str:
    if score_0_1000 >= 800:
        return "critical"
    if score_0_1000 >= 550:
        return "high"
    if score_0_1000 >= 250:
        return "medium"
    return "low"


def recommendation_for(band: str) -> str:
    return {
        "critical": "notify command",
        "high": "sanctions review",
        "medium": "investigate",
        "low": "monitor",
    }[band]


def score_vessel(db: Session, imo: str) -> ScoreOut:
    """Compute (or recompute) the deception score for one vessel."""
    vessel = db.query(Vessel).filter(Vessel.imo == imo).first()
    if not vessel:
        raise HTTPException(404, f"vessel {imo} not found")

    # Drop any prior score so the response represents the current state.
    prior = db.query(RiskScore).filter(RiskScore.vessel_imo == imo).all()
    for p in prior:
        db.delete(p)
    db.query(Evidence).filter(Evidence.vessel_imo == imo).delete()
    db.flush()

    raw_total = 0
    components: list[ScoreComponent] = []
    evidences: list[tuple[ScoreComponent, list[Evidence]]] = []

    for module in ALL_DETECTORS:
        result = module.detect(db, vessel)
        raw_total += result.contribution

        sc = ScoreComponent(
            name=result.name,
            weight=result.weight,
            value=result.value,
            contribution=result.contribution,
        )
        components.append(sc)

        ev_rows = [
            Evidence(
                vessel_imo=vessel.imo,
                detector_name=result.name,
                title=p.title,
                description=p.description,
                source_type=p.source_type,
                source_ref=p.source_ref,
                start_time=p.start_time,
                end_time=p.end_time,
                geometry=p.geometry,
                severity=p.severity,
                confidence=p.confidence,
                score_contribution=p.score_contribution,
            )
            for p in result.evidence
        ]
        evidences.append((sc, ev_rows))

    # Normalize to 0-1000 against the maximum the implemented detectors can produce.
    total_0_1000 = round(raw_total * 1000 / RUBRIC_MAX) if RUBRIC_MAX else 0
    total_0_1000 = max(0, min(total_0_1000, 1000))

    band = band_for(total_0_1000)
    score = RiskScore(
        vessel_imo=vessel.imo,
        score=total_0_1000,
        band=band,
        recommendation=recommendation_for(band),
    )
    score.components = components
    db.add(score)
    db.flush()  # populate component IDs

    for sc, ev_rows in evidences:
        for ev in ev_rows:
            ev.score_component_id = sc.id
            db.add(ev)

    db.commit()
    db.refresh(score)
    return ScoreOut.model_validate(score)
