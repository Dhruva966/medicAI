"""Deception-score rubric engine.

Reads vessel events, applies weighted components from docs/SCORING_RUBRIC.md,
persists a RiskScore + ScoreComponent rows, and returns the response schema.
"""

from sqlalchemy.orm import Session

from app.schemas import ScoreOut


# Rubric definition. Weights sum to 1000.
RUBRIC: dict[str, int] = {
    "ais_gap": 150,
    "flag_hopping": 100,
    "ownership_shell": 150,
    "sts_proximity": 150,
    "route_implausible": 100,
    "sanctions_neighbor": 100,
    "identity_mismatch": 100,
    "sar_visual_mismatch": 100,
    "dark_port_call": 50,
}


def band_for(score: int) -> str:
    if score >= 800:
        return "critical"
    if score >= 550:
        return "high"
    if score >= 250:
        return "medium"
    return "low"


def score_vessel(db: Session, imo: str) -> ScoreOut:
    """Compute the score for one vessel and persist it.

    Each component evaluator returns (value: float in 0..1, evidence: dict).
    contribution = round(weight * value).
    """
    raise NotImplementedError("scoring.score_vessel not implemented yet")
