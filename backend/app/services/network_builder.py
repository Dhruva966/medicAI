"""Ownership-graph builder.

Walks Owner.parent_owner_id and links to other vessels owned by the same
parent. Returns a D3-friendly node/edge payload.
"""

from sqlalchemy.orm import Session

from app.models import Owner, Vessel
from app.schemas import OwnershipNetwork
from app.schemas.vessel import OwnershipEdge, OwnershipNode


def _owner_node_id(o: Owner) -> str:
    return f"owner-{o.id}"


def _vessel_node_id(v: Vessel) -> str:
    return f"vessel-{v.imo}"


def build(db: Session, imo: str, depth: int = 2) -> OwnershipNetwork:
    root = db.query(Vessel).filter(Vessel.imo == imo).first()
    if not root:
        return OwnershipNetwork(nodes=[], edges=[])

    nodes: dict[str, OwnershipNode] = {}
    edges: list[OwnershipEdge] = []

    nodes[_vessel_node_id(root)] = OwnershipNode(
        id=_vessel_node_id(root),
        label=root.name,
        kind="sanctioned_vessel" if _is_sdn(root) else "vessel",
        sanctioned=_is_sdn(root),
    )

    visited_owner_ids: set[int] = set()

    def expand_owner(owner: Owner | None, prev_node_id: str, hop: int) -> None:
        if not owner or hop > depth or owner.id in visited_owner_ids:
            return
        visited_owner_ids.add(owner.id)

        oid = _owner_node_id(owner)
        nodes[oid] = OwnershipNode(
            id=oid,
            label=owner.name,
            kind="owner",
            sanctioned=owner.sanctioned,
        )
        edges.append(OwnershipEdge(source=prev_node_id, target=oid, relation="owns" if hop == 0 else "subsidiary_of"))

        # Sister vessels owned by the same owner.
        sisters = db.query(Vessel).filter(Vessel.owner_id == owner.id, Vessel.imo != root.imo).all()
        for s in sisters:
            sid = _vessel_node_id(s)
            kind = "sanctioned_vessel" if _is_sdn(s) else "vessel"
            nodes[sid] = OwnershipNode(id=sid, label=s.name, kind=kind, sanctioned=_is_sdn(s))
            edges.append(OwnershipEdge(source=oid, target=sid, relation="owns"))
            if _is_sdn(s):
                edges.append(
                    OwnershipEdge(source=_vessel_node_id(root), target=sid, relation="linked_to_sanctioned")
                )

        # Parent owner.
        if owner.parent_owner_id:
            parent = db.query(Owner).filter(Owner.id == owner.parent_owner_id).first()
            expand_owner(parent, oid, hop + 1)

    if root.owner:
        expand_owner(root.owner, _vessel_node_id(root), 0)

    return OwnershipNetwork(nodes=list(nodes.values()), edges=edges)


def _is_sdn(v: Vessel) -> bool:
    """Derive sanctioned status from owner chain or direct vessel listing."""
    from app.clients import ofac

    if ofac.is_sanctioned_vessel(v.imo):
        return True
    cur = v.owner
    seen: set[int] = set()
    while cur and cur.id not in seen:
        seen.add(cur.id)
        if cur.sanctioned:
            return True
        cur = None  # one-level for lookup brevity; deep walk happens elsewhere
    return False
