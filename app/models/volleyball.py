from dataclasses import dataclass


@dataclass(frozen=True)
class VolleyballFeatures:
    team_rating: float
    opponent_rating: float
    recent_set_ratio: float
    attack_efficiency: float
    reception_quality: float
    data_quality: float = 1.0


def predict(features: VolleyballFeatures) -> tuple[float, float]:
    edge = (
        0.34 * (features.team_rating - features.opponent_rating)
        + 0.24 * (features.recent_set_ratio - 0.5)
        + 0.22 * (features.attack_efficiency - 0.5)
        + 0.20 * (features.reception_quality - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
