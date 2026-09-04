from dataclasses import dataclass


@dataclass(frozen=True)
class HandballFeatures:
    team_rating: float
    opponent_rating: float
    attack_efficiency: float
    defence_efficiency: float
    recent_form: float
    data_quality: float = 1.0


def predict(features: HandballFeatures) -> tuple[float, float]:
    edge = (
        0.32 * (features.team_rating - features.opponent_rating)
        + 0.25 * (features.attack_efficiency - 0.5)
        + 0.23 * (features.defence_efficiency - 0.5)
        + 0.20 * (features.recent_form - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
