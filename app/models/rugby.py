from dataclasses import dataclass


@dataclass(frozen=True)
class RugbyFeatures:
    team_rating: float
    opponent_rating: float
    attack_rating: float
    defence_rating: float
    discipline: float
    recent_form: float
    data_quality: float = 1.0


def predict(features: RugbyFeatures) -> tuple[float, float]:
    edge = (
        0.30 * (features.team_rating - features.opponent_rating)
        + 0.22 * (features.attack_rating - 0.5)
        + 0.20 * (features.defence_rating - 0.5)
        + 0.12 * (features.discipline - 0.5)
        + 0.16 * (features.recent_form - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
