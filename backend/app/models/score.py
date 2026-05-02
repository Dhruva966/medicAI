"""Risk-score ORM models."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RiskScore(Base):
    """A computed deception score for a vessel at a point in time."""

    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_imo: Mapped[str] = mapped_column(ForeignKey("vessels.imo"), index=True)
    score: Mapped[int] = mapped_column(Integer)  # 0-1000
    band: Mapped[str] = mapped_column(String(16))  # low | medium | high | critical
    recommendation: Mapped[str] = mapped_column(String(64))  # monitor | investigate | sanctions review | notify command
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    components: Mapped[list["ScoreComponent"]] = relationship(
        "ScoreComponent",
        back_populates="score",
        cascade="all, delete-orphan",
    )


class ScoreComponent(Base):
    """One rubric component of a RiskScore — see docs/SCORING_RUBRIC.md."""

    __tablename__ = "score_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score_id: Mapped[int] = mapped_column(ForeignKey("risk_scores.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))  # ais_gap, flag_hopping, etc.
    weight: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)  # 0..1
    contribution: Mapped[int] = mapped_column(Integer)  # weight * value, rounded

    score: Mapped["RiskScore"] = relationship("RiskScore", back_populates="components")
    evidence_records: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        "Evidence", back_populates="score_component"
    )
