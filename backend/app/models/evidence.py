"""Evidence ORM model — every detector emits these for analyst traceability."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Evidence(Base):
    """One discrete piece of evidence backing a deception alert.

    Mirrors the schema in AGENTS.md so every alert in the UI traces
    back to a stored, citable record.
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    score_component_id: Mapped[int | None] = mapped_column(
        ForeignKey("score_components.id"), nullable=True, index=True
    )

    detector_name: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2048))

    source_type: Mapped[str] = mapped_column(String(32))  # ais|sanctions|registry|satellite|port
    source_ref: Mapped[str] = mapped_column(String(255))

    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # GeoJSON geometry stored as JSON (works on SQLite + Postgres without PostGIS).
    # Migrate to GeoAlchemy2 Geometry when DATABASE_URL points at PostGIS.
    geometry: Mapped[dict] = mapped_column(JSON, default=dict)

    severity: Mapped[str] = mapped_column(String(16))  # low|medium|high|critical
    confidence: Mapped[float] = mapped_column(Float)  # 0..1
    score_contribution: Mapped[int] = mapped_column(Integer, default=0)
    analyst_notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    score_component: Mapped["ScoreComponent | None"] = relationship(  # noqa: F821
        "ScoreComponent", back_populates="evidence_records"
    )
