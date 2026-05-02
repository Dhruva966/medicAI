"""Ownership-network endpoint — feeds the D3 force-directed graph."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import OwnershipNetwork
from app.services import network_builder

router = APIRouter(prefix="/vessels", tags=["network"])


@router.get("/{imo}/network", response_model=OwnershipNetwork)
def get_network(imo: str, depth: int = 2, db: Session = Depends(get_db)) -> OwnershipNetwork:
    """Build the ownership graph rooted at this vessel up to N hops."""
    return network_builder.build(db, imo, depth=depth)
