"""Pydantic schemas for vessels, owners, and the ownership graph."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str | None = None
    shell_company: bool = False
    sanctioned: bool = False
    sanctioned_at: datetime | None = None
    parent_owner_id: int | None = None


class FlagHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flag: str
    start_date: datetime
    end_date: datetime | None = None


class VesselOut(BaseModel):
    """Lightweight vessel record for list views and the map.

    Score / band are populated from the latest RiskScore when available so
    the map can color markers without a per-vessel round-trip.
    """

    model_config = ConfigDict(from_attributes=True)

    imo: str
    name: str
    type: str
    flag: str
    last_seen_lat: float | None = None
    last_seen_lon: float | None = None
    last_seen_at: datetime | None = None
    score: int | None = None
    band: str | None = None


class VesselDetail(VesselOut):
    """Full vessel detail with owner and flag history."""

    mmsi: str | None = None
    gross_tonnage: int | None = None
    length_m: float | None = None
    beam_m: float | None = None
    year_built: int | None = None
    owner: OwnerOut | None = None
    flag_history: list[FlagHistoryOut] = []


class OwnershipEdge(BaseModel):
    source: str  # node id (vessel imo or owner-{id})
    target: str
    relation: str  # "owns", "subsidiary_of", "linked_to_sanctioned"


class OwnershipNode(BaseModel):
    id: str
    label: str
    kind: str  # "vessel" | "owner" | "sanctioned_vessel"
    sanctioned: bool = False


class OwnershipNetwork(BaseModel):
    """Output of /vessels/{imo}/network — D3-friendly graph payload."""

    nodes: list[OwnershipNode]
    edges: list[OwnershipEdge]
