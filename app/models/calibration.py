from dataclasses import dataclass
from math import log


EPSILON = 1e-12


@dataclass(frozen=True)
class CalibrationReport:
    sample_size: int
    brier_score: float
    log_loss: float
    expected_calibration_error: float


def evaluate_calibration(probabilities: list[float], outcomes: list[int], bins: int = 10) -> CalibrationReport:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must be non-empty and equal length")
    if any(not 0 <= p <= 1 for p in probabilities):
        raise ValueError("probabilities must be between 0 and 1")
    if any(y not in (0, 1) for y in outcomes):
        raise ValueError("outcomes must contain only 0 or 1")

    n = len(probabilities)
    brier = sum((p - y) ** 2 for p, y in zip(probabilities, outcomes, strict=True)) / n
    ll = -sum(
        y * log(max(p, EPSILON)) + (1 - y) * log(max(1 - p, EPSILON))
        for p, y in zip(probabilities, outcomes, strict=True)
    ) / n

    ece = 0.0
    for i in range(bins):
        low, high = i / bins, (i + 1) / bins
        members = [
            (p, y) for p, y in zip(probabilities, outcomes, strict=True)
            if low <= p < high or (i == bins - 1 and p == 1.0)
        ]
        if not members:
            continue
        avg_p = sum(p for p, _ in members) / len(members)
        avg_y = sum(y for _, y in members) / len(members)
        ece += (len(members) / n) * abs(avg_p - avg_y)

    return CalibrationReport(n, round(brier, 6), round(ll, 6), round(ece, 6))
