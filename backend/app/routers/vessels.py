"""Vessel list + detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RiskScore, Vessel
from app.schemas import VesselDetail, VesselOut

router = APIRouter(prefix="/vessels", tags=["vessels"])


def _latest_score_map(db: Session) -> dict[str, RiskScore]:
    """Return imo -> latest RiskScore for all vessels."""
    rows = db.query(RiskScore).order_by(RiskScore.vessel_imo, desc(RiskScore.computed_at)).all()
    out: dict[str, RiskScore] = {}
    for r in rows:
        if r.vessel_imo not in out:
            out[r.vessel_imo] = r
    return out


@router.get("", response_model=list[VesselOut])
def list_vessels(db: Session = Depends(get_db)) -> list[VesselOut]:
    """Return every tracked vessel for the world map, with cached score/band."""
    vessels = db.query(Vessel).order_by(Vessel.name).all()
    scores = _latest_score_map(db)
    out: list[VesselOut] = []
    for v in vessels:
        s = scores.get(v.imo)
        out.append(
            VesselOut(
                imo=v.imo,
                name=v.name,
                type=v.type,
                flag=v.flag,
                last_seen_lat=v.last_seen_lat,
                last_seen_lon=v.last_seen_lon,
                last_seen_at=v.last_seen_at,
                score=s.score if s else None,
                band=s.band if s else None,
            )
        )
    return out


@router.get("/{imo}", response_model=VesselDetail)
def get_vessel(imo: str, db: Session = Depends(get_db)) -> VesselDetail:
    """Return full detail for a single vessel: identity + owner + flag history."""
    v = db.query(Vessel).filter(Vessel.imo == imo).first()
    if not v:
        raise HTTPException(404, f"vessel {imo} not found")
    score = (
        db.query(RiskScore)
        .filter(RiskScore.vessel_imo == imo)
        .order_by(desc(RiskScore.computed_at))
        .first()
    )
    return VesselDetail(
        imo=v.imo,
        name=v.name,
        type=v.type,
        flag=v.flag,
        last_seen_lat=v.last_seen_lat,
        last_seen_lon=v.last_seen_lon,
        last_seen_at=v.last_seen_at,
        score=score.score if score else None,
        band=score.band if score else None,
        mmsi=v.mmsi,
        gross_tonnage=v.gross_tonnage,
        length_m=v.length_m,
        beam_m=v.beam_m,
        year_built=v.year_built,
        owner=v.owner,
        flag_history=v.flag_history,
    )
