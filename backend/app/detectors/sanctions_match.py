"""Sanctions-match detector — direct OFAC SDN hits and N-hop ownership proximity."""

from sqlalchemy.orm import Session

from app.clients import ofac
from app.detectors.types import DetectorResult, EvidencePayload
from app.models import Owner, Vessel

NAME = "sanctions_match"
WEIGHT = 200


def _walk_owner_chain(db: Session, owner: Owner | None, max_depth: int = 4) -> list[Owner]:
    """Walk parent_owner_id chain. Returns ordered list ending at the root."""
    chain: list[Owner] = []
    seen: set[int] = set()
    cur = owner
    while cur and cur.id not in seen and len(chain) < max_depth:
        chain.append(cur)
        seen.add(cur.id)
        if not cur.parent_owner_id:
            break
        cur = db.query(Owner).filter(Owner.id == cur.parent_owner_id).first()
    return chain


def detect(db: Session, vessel: Vessel) -> DetectorResult:
    evidence: list[EvidencePayload] = []
    max_value = 0.0

    # Direct vessel-IMO hit on SDN list.
    if ofac.is_sanctioned_vessel(vessel.imo):
        max_value = 1.0
        evidence.append(
            EvidencePayload(
                title=f"Vessel IMO {vessel.imo} on OFAC SDN list",
                description=(
                    f"Vessel {vessel.name} (IMO {vessel.imo}) is directly listed on the "
                    "OFAC Specially Designated Nationals (SDN) list."
                ),
                source_type="sanctions",
                source_ref="ofac://sdn/vessel",
                severity="critical",
                confidence=0.99,
                score_contribution=WEIGHT,
            )
        )

    # Owner-chain walk: any sanctioned ancestor.
    chain = _walk_owner_chain(db, vessel.owner)
    for hop, owner in enumerate(chain):
        if owner.sanctioned:
            v = max(0.95 - 0.15 * hop, 0.5)
            max_value = max(max_value, v)
            rel = "registered owner" if hop == 0 else f"owner-chain hop {hop}"
            evidence.append(
                EvidencePayload(
                    title=f"Sanctioned entity in {rel}: {owner.name}",
                    description=(
                        f"{owner.name}{' (' + owner.country + ')' if owner.country else ''} "
                        f"appears in the OFAC SDN list and sits {hop} hop(s) up the ownership chain."
                    ),
                    source_type="sanctions",
                    source_ref=f"ofac://sdn/owner/{owner.id}",
                    severity="critical" if hop == 0 else "high",
                    confidence=0.92,
                    score_contribution=round(WEIGHT * v),
                )
            )

        if owner.shell_company:
            v = 0.55
            max_value = max(max_value, v)
            evidence.append(
                EvidencePayload(
                    title=f"Shell-company owner: {owner.name}",
                    description=(
                        f"{owner.name} is flagged as a shell company — opaque structure, "
                        "minimal operating footprint."
                    ),
                    source_type="registry",
                    source_ref=f"equasis://owner/{owner.id}",
                    severity="medium",
                    confidence=0.7,
                    score_contribution=round(WEIGHT * v),
                )
            )

    return DetectorResult(name=NAME, weight=WEIGHT, value=max_value, evidence=evidence)
