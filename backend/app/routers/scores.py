"""Risk-score endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ScoreOut
from app.services import scoring

router = APIRouter(prefix="/vessels", tags=["scores"])


@router.get("/{imo}/score", response_model=ScoreOut)
def get_score(imo: str, db: Session = Depends(get_db)) -> ScoreOut:
    """Compute (or fetch cached) deception score for a vessel."""
    return scoring.score_vessel(db, imo)
