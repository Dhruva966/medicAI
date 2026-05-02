"""Interdiction-brief generation endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import InterdictionBrief
from app.services import brief_generator

router = APIRouter(prefix="/vessels", tags=["briefs"])


@router.post("/{imo}/brief", response_model=InterdictionBrief)
def generate_brief(imo: str, db: Session = Depends(get_db)) -> InterdictionBrief:
    """Generate an LLM-authored interdiction brief from current evidence."""
    return brief_generator.generate(db, imo)
