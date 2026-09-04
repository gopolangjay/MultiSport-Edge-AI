from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceFeatures:
    model_probability: float
    market_probability: float | None
    sample_size: int
    recent_form_strength: float
    opponent_fit: float
    availability_quality: float
    data_completeness: float
    model_agreement: float
    volatility: float

    @property
    def market_edge(self) -> float | None:
        if self.market_probability is None:
            return None
        return self.model_probability - self.market_probability


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal_odds must be greater than 1")
    return 1.0 / decimal_odds


def analytical_confidence(features: EvidenceFeatures) -> float:
    sample_score = min(features.sample_size / 30.0, 1.0)
    score = (
        0.20 * sample_score
        + 0.16 * features.recent_form_strength
        + 0.12 * features.opponent_fit
        + 0.14 * features.availability_quality
        + 0.18 * features.data_completeness
        + 0.15 * features.model_agreement
        + 0.05 * (1.0 - features.volatility)
    )
    return round(max(0.0, min(1.0, score)) * 100.0, 2)
