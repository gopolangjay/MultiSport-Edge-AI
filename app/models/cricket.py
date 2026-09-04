from dataclasses import dataclass


@dataclass(frozen=True)
class CricketFeatures:
    batting_rating: float
    bowling_rating: float
    opponent_rating: float
    venue_fit: float
    recent_form: float
    data_quality: float = 1.0


def predict(features: CricketFeatures) -> tuple[float, float]:
    composite = 0.52 * features.batting_rating + 0.48 * features.bowling_rating
    edge = (
        0.38 * (composite - features.opponent_rating)
        + 0.27 * (features.venue_fit - 0.5)
        + 0.35 * (features.recent_form - 0.5)
    )
    probability = max(0.02, min(0.98, 0.5 + edge))
    confidence = 50 + abs(probability - 0.5) * 100 * features.data_quality
    return round(probability, 4), round(min(confidence, 99.0), 2)
