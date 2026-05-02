"""Evasion-pattern classifier.

Tags vessels with named playbooks like:
- 'dark_transfer'        AIS gap + STS proximity + return to port
- 'flag_hop_laundering'  ≥2 flag changes + ownership change + STS event
- 'identity_swap'        MMSI/IMO/name desync across sources
"""

from dataclasses import dataclass
from sqlalchemy.orm import Session


@dataclass
class PlaybookHit:
    name: str
    confidence: float  # 0..1
    evidence: dict


def classify(db: Session, imo: str) -> list[PlaybookHit]:
    """Return all playbook patterns this vessel matches."""
    raise NotImplementedError("playbook_matcher.classify not implemented yet")
