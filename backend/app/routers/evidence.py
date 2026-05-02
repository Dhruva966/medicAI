"""Evidence-timeline endpoint — every alert traces back to stored records."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Evidence
from app.schemas import EvidenceOut

router = APIRouter(prefix="/vessels", tags=["evidence"])


@router.get("/{imo}/evidence", response_model=list[EvidenceOut])
def list_evidence(imo: str, db: Session = Depends(get_db)) -> list[Evidence]:
    """All evidence records for a vessel ordered by start_time descending."""
    return (
        db.query(Evidence)
        .filter(Evidence.vessel_imo == imo)
        .order_by(Evidence.start_time.is_(None), Evidence.start_time.desc(), Evidence.id.desc())
        .all()
    )
