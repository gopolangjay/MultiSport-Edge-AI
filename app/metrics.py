from dataclasses import dataclass
from math import log


@dataclass(frozen=True)
class CalibrationReport:
    samples: int
    hit_rate: float
    brier_score: float
    log_loss: float
    expected_calibration_error: float


def calibration_report(probabilities: list[float], outcomes: list[int], bins: int = 10) -> CalibrationReport:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must have equal non-zero length")
    clipped = [min(max(p, 1e-9), 1 - 1e-9) for p in probabilities]
    n = len(clipped)
    hit_rate = sum(outcomes) / n
    brier = sum((p - y) ** 2 for p, y in zip(clipped, outcomes)) / n
    ll = -sum(y * log(p) + (1 - y) * log(1 - p) for p, y in zip(clipped, outcomes)) / n

    ece = 0.0
    for idx in range(bins):
        lo, hi = idx / bins, (idx + 1) / bins
        bucket = [(p, y) for p, y in zip(clipped, outcomes) if lo <= p < hi or (idx == bins - 1 and p == 1)]
        if not bucket:
            continue
        avg_p = sum(p for p, _ in bucket) / len(bucket)
        avg_y = sum(y for _, y in bucket) / len(bucket)
        ece += len(bucket) / n * abs(avg_p - avg_y)

    return CalibrationReport(n, round(hit_rate, 4), round(brier, 6), round(ll, 6), round(ece, 6))
