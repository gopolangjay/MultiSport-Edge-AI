from dataclasses import dataclass


@dataclass(frozen=True)
class IceHockeyFeatures:
    team_rating: float
    opponent_rating: float
    expected_goal_share: float
    goalie_strength: float
    recent_form: float
    data_quality: float = 1.0


def predict(features: IceHockeyFeatures) -> tuple[float, float]:
    edge = (
        0.30 * (features.team_rating - features.opponent_rating)
        + 0.30 * (features.expected_goal_share - 0.5)
        + 0.22 * (features.goalie_strength - 0.5)
        + 0.18 * (features.recent_form - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
