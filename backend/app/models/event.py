"""Event-style ORM models — AIS gaps, encounters, port calls, STS transfers."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AISGap(Base):
    """A period where a vessel's AIS transponder was off or not received."""

    __tablename__ = "ais_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    duration_hours: Mapped[float] = mapped_column(Float)

    last_known_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_known_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_known_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_known_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    in_known_sts_zone: Mapped[bool] = mapped_column(Boolean, default=False)


class Encounter(Base):
    """Two vessels in close proximity in open water — possible STS transfer."""

    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_a_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    vessel_b_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    duration_hours: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    in_port: Mapped[bool] = mapped_column(Boolean, default=False)

    sts_transfer: Mapped["STSTransfer | None"] = relationship(
        "STSTransfer", back_populates="encounter", uselist=False
    )


class PortCall(Base):
    """A vessel's arrival and departure at a named port."""

    __tablename__ = "port_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    port_name: Mapped[str] = mapped_column(String(255))
    port_country: Mapped[str] = mapped_column(String(64))
    arrival_at: Mapped[datetime] = mapped_column(DateTime)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class STSTransfer(Base):
    """A classified ship-to-ship transfer associated with a specific Encounter."""

    __tablename__ = "sts_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"), unique=True)
    transfer_type: Mapped[str] = mapped_column(String(64))  # oil, cargo, unknown
    estimated_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    in_known_zone: Mapped[bool] = mapped_column(Boolean, default=False)

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="sts_transfer")
