from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationPoint:
    predicted: float
    observed: float


class ProbabilityCalibrator:
    """Lightweight monotonic interpolation over historical calibration bins.

    It deliberately falls back to the raw probability until enough settled
    history exists. This keeps analytical confidence separate from probability.
    """

    def __init__(self, points: list[CalibrationPoint] | None = None) -> None:
        self.points = sorted(points or [], key=lambda p: p.predicted)

    def calibrate(self, probability: float) -> float:
        p = max(0.001, min(0.999, probability))
        if len(self.points) < 2:
            return p
        if p <= self.points[0].predicted:
            return max(0.001, min(0.999, self.points[0].observed))
        if p >= self.points[-1].predicted:
            return max(0.001, min(0.999, self.points[-1].observed))
        for left, right in zip(self.points, self.points[1:]):
            if left.predicted <= p <= right.predicted:
                span = right.predicted - left.predicted
                weight = 0.0 if span == 0 else (p - left.predicted) / span
                observed = left.observed + weight * (right.observed - left.observed)
                return max(0.001, min(0.999, observed))
        return p
