"""Vessel list + detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import VesselDetail, VesselOut

router = APIRouter(prefix="/vessels", tags=["vessels"])


@router.get("", response_model=list[VesselOut])
def list_vessels(db: Session = Depends(get_db)) -> list[VesselOut]:
    """Return every tracked vessel for the world map."""
    raise NotImplementedError("services.vessel_listing not implemented yet")


@router.get("/{imo}", response_model=VesselDetail)
def get_vessel(imo: str, db: Session = Depends(get_db)) -> VesselDetail:
    """Return full detail for a single vessel: identity + owner + flag history."""
    raise NotImplementedError("services.vessel_detail not implemented yet")
    # When implemented:
    #   if not vessel: raise HTTPException(404, f"vessel {imo} not found")
    _ = HTTPException  # keep import
