from dataclasses import dataclass
from math import exp


def logistic(x: float) -> float:
    return 1.0 / (1.0 + exp(-x))


def clamp_probability(value: float) -> float:
    return min(0.995, max(0.005, value))


@dataclass(frozen=True)
class ModelOutput:
    probability: float
    data_quality: float
    analytical_confidence: float
    factors: dict[str, float]


def _confidence(probability: float, quality: float, agreement: float) -> float:
    # Confidence is deliberately distinct from probability. It rewards evidence quality
    # and model agreement while remaining bounded and auditable.
    certainty = abs(probability - 0.5) * 2.0
    return round(100 * (0.60 * certainty + 0.25 * quality + 0.15 * agreement), 2)


def football_model(*, strength_delta: float, recent_form_delta: float, home_advantage: float,
                   goal_profile_edge: float, data_quality: float, model_agreement: float) -> ModelOutput:
    score = (0.42 * strength_delta + 0.22 * recent_form_delta + 0.14 * home_advantage
             + 0.22 * goal_profile_edge)
    p = clamp_probability(logistic(score))
    factors = {"strength": strength_delta, "form": recent_form_delta,
               "home_advantage": home_advantage, "goal_profile": goal_profile_edge}
    return ModelOutput(p, data_quality, _confidence(p, data_quality, model_agreement), factors)


def tennis_model(*, rating_delta: float, surface_edge: float, serve_return_edge: float,
                 recent_form_delta: float, data_quality: float, model_agreement: float) -> ModelOutput:
    score = 0.40 * rating_delta + 0.24 * surface_edge + 0.24 * serve_return_edge + 0.12 * recent_form_delta
    p = clamp_probability(logistic(score))
    factors = {"rating": rating_delta, "surface": surface_edge,
               "serve_return": serve_return_edge, "form": recent_form_delta}
    return ModelOutput(p, data_quality, _confidence(p, data_quality, model_agreement), factors)


def basketball_model(*, efficiency_delta: float, pace_matchup_edge: float, home_advantage: float,
                     recent_form_delta: float, data_quality: float, model_agreement: float) -> ModelOutput:
    score = 0.48 * efficiency_delta + 0.18 * pace_matchup_edge + 0.16 * home_advantage + 0.18 * recent_form_delta
    p = clamp_probability(logistic(score))
    factors = {"efficiency": efficiency_delta, "pace": pace_matchup_edge,
               "home_advantage": home_advantage, "form": recent_form_delta}
    return ModelOutput(p, data_quality, _confidence(p, data_quality, model_agreement), factors)
