from dataclasses import dataclass


@dataclass(frozen=True)
class BaseballFeatures:
    batting_strength: float
    opponent_pitching_strength: float
    starting_pitcher_strength: float
    bullpen_strength: float
    park_factor: float
    recent_form: float
    data_quality: float = 1.0


def predict(features: BaseballFeatures) -> tuple[float, float]:
    edge = (
        0.25 * (features.batting_strength - features.opponent_pitching_strength)
        + 0.27 * (features.starting_pitcher_strength - 0.5)
        + 0.18 * (features.bullpen_strength - 0.5)
        + 0.12 * (features.park_factor - 0.5)
        + 0.18 * (features.recent_form - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
