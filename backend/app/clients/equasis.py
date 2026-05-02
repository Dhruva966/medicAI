"""Equasis — vessel ownership and flag history.

NEEDS-SETUP-FOR-PRODUCTION:
  Equasis is registration-gated and has no public API. Real production
  integration involves either (a) a manual session-cookie capture stored
  in EQUASIS_SESSION, or (b) a partnership / commercial data feed.

  For v1 we read both ownership and flag history straight from our own
  Owner / FlagHistory tables which are populated by the seed scenario.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import FlagHistory, Owner, Vessel


def get_owner_chain(db: Session, imo: str) -> list[dict[str, Any]]:
    """Return the ownership chain for a vessel, root → leaf."""
    vessel = db.query(Vessel).filter(Vessel.imo == imo).first()
    if not vessel or not vessel.owner_id:
        return []

    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    cur: Owner | None = vessel.owner

    while cur and cur.id not in seen:
        seen.add(cur.id)
        chain.append(
            {
                "id": cur.id,
                "name": cur.name,
                "country": cur.country,
                "shell_company": cur.shell_company,
                "sanctioned": cur.sanctioned,
            }
        )
        if not cur.parent_owner_id:
            break
        cur = db.query(Owner).filter(Owner.id == cur.parent_owner_id).first()

    return chain


def get_flag_history(db: Session, imo: str) -> list[dict[str, Any]]:
    """Return flag-state history, most-recent first."""
    rows = (
        db.query(FlagHistory)
        .filter(FlagHistory.vessel_imo == imo)
        .order_by(FlagHistory.start_date.desc())
        .all()
    )
    return [
        {
            "flag": r.flag,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
        }
        for r in rows
    ]
