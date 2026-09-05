from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.metrics import calibration_report


@dataclass(frozen=True)
class SettledPrediction:
    predicted_at: datetime
    probability: float
    won: bool
    sport: str
    market: str


@dataclass(frozen=True)
class WindowPerformance:
    days: int
    sample_size: int
    hit_rate: float | None
    brier_score: float | None
    log_loss: float | None
    expected_calibration_error: float | None


def rolling_performance(
    rows: list[SettledPrediction], days: int, now: datetime | None = None
) -> WindowPerformance:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    selected = [row for row in rows if row.predicted_at >= cutoff]
    if not selected:
        return WindowPerformance(days, 0, None, None, None, None)
    probabilities = [row.probability for row in selected]
    outcomes = [1 if row.won else 0 for row in selected]
    report = calibration_report(probabilities, outcomes)
    return WindowPerformance(
        days,
        report.samples,
        report.hit_rate,
        report.brier_score,
        report.log_loss,
        report.expected_calibration_error,
    )


def standard_windows(
    rows: list[SettledPrediction], now: datetime | None = None
) -> list[WindowPerformance]:
    return [rolling_performance(rows, days, now) for days in (7, 30, 90)]
