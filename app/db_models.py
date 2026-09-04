from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRecord(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_event_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    sport: Mapped[str] = mapped_column(String(40), index=True)
    competition: Mapped[str | None] = mapped_column(String(160), index=True)
    home_or_player_a: Mapped[str] = mapped_column(String(180))
    away_or_player_b: Mapped[str] = mapped_column(String(180))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String(40), index=True)
    market: Mapped[str] = mapped_column(String(160), index=True)
    selection: Mapped[str] = mapped_column(String(200))
    line: Mapped[str | None] = mapped_column(String(80))
    decimal_odds: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PredictionRecord(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("event_id", "model_version", "market", "selection"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    market: Mapped[str] = mapped_column(String(160))
    selection: Mapped[str] = mapped_column(String(200))
    calibrated_probability: Mapped[float] = mapped_column(Float)
    analytical_confidence: Mapped[float] = mapped_column(Float, index=True)
    data_quality: Mapped[float] = mapped_column(Float)
    rationale_json: Mapped[str | None] = mapped_column(Text)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResultRecord(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_status: Mapped[str] = mapped_column(String(60))
    score_or_result: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SettlementRecord(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), unique=True, index=True)
    outcome: Mapped[str] = mapped_column(String(24), index=True)  # won/lost/void/unresolved
    settlement_source: Mapped[str] = mapped_column(String(80))
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PortfolioRunRecord(Base):
    __tablename__ = "portfolio_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    bookmaker: Mapped[str | None] = mapped_column(String(40))
    combined_odds: Mapped[float | None] = mapped_column(Float)
    average_confidence: Mapped[float | None] = mapped_column(Float)
    leg_count: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CalibrationMetric(Base):
    __tablename__ = "calibration_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    sport: Mapped[str | None] = mapped_column(String(40), index=True)
    market: Mapped[str | None] = mapped_column(String(160), index=True)
    sample_size: Mapped[int] = mapped_column(Integer)
    brier_score: Mapped[float | None] = mapped_column(Float)
    log_loss: Mapped[float | None] = mapped_column(Float)
    expected_calibration_error: Mapped[float | None] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
