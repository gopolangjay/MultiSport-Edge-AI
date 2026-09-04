from dataclasses import dataclass


@dataclass(frozen=True)
class TableTennisFeatures:
    player_rating: float
    opponent_rating: float
    recent_game_ratio: float
    serve_strength: float
    return_strength: float
    data_quality: float = 1.0


def predict(features: TableTennisFeatures) -> tuple[float, float]:
    edge = (
        0.36 * (features.player_rating - features.opponent_rating)
        + 0.22 * (features.recent_game_ratio - 0.5)
        + 0.22 * (features.serve_strength - 0.5)
        + 0.20 * (features.return_strength - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
