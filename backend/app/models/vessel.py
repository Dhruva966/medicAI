"""Vessel, Owner, and FlagHistory ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Owner(Base):
    """A registered (or shell) owner of one or more vessels."""

    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shell_company: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctioned: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctioned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parent_owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("owners.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    parent: Mapped["Owner | None"] = relationship(
        "Owner", remote_side="Owner.id", backref="subsidiaries"
    )
    vessels: Mapped[list["Vessel"]] = relationship("Vessel", back_populates="owner")


class Vessel(Base):
    """A merchant vessel tracked by ShadowFleet."""

    __tablename__ = "vessels"

    imo: Mapped[str] = mapped_column(String(16), primary_key=True)
    mmsi: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(64))  # tanker, cargo, bulker, etc.
    flag: Mapped[str] = mapped_column(String(64), index=True)
    gross_tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    beam_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)

    owner_id: Mapped[int | None] = mapped_column(ForeignKey("owners.id"), nullable=True)

    last_seen_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["Owner | None"] = relationship("Owner", back_populates="vessels")
    flag_history: Mapped[list["FlagHistory"]] = relationship(
        "FlagHistory", back_populates="vessel", cascade="all, delete-orphan"
    )


class FlagHistory(Base):
    """Historical flag-state record for a vessel — flag-hopping is a deception signal."""

    __tablename__ = "flag_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_imo: Mapped[str] = mapped_column(
        ForeignKey("vessels.imo"), index=True
    )
    flag: Mapped[str] = mapped_column(String(64))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="flag_history")
