"""Ownership-graph builder.

Walks Owner.parent_owner_id and links to other vessels owned by the same
parent or marked as sanctioned. Returns a D3-friendly node/edge payload.
"""

from sqlalchemy.orm import Session

from app.schemas import OwnershipNetwork


def build(db: Session, imo: str, depth: int = 2) -> OwnershipNetwork:
    """Construct an ownership network around `imo` to `depth` hops."""
    raise NotImplementedError("network_builder.build not implemented yet")
