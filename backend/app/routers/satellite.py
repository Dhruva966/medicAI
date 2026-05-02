"""Satellite (SAR) overlay endpoint."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.clients import copernicus

router = APIRouter(prefix="/vessels", tags=["satellite"])


@router.get("/{imo}/sar")
def get_sar_overlay(imo: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return SAR overlay metadata (image URL + bounding box) for a vessel's last gap."""
    return copernicus.get_sar_overlay(imo)
