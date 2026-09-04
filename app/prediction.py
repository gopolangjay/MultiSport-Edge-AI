from pydantic import BaseModel, Field


class PredictionEvidence(BaseModel):
    historical_probability: float = Field(ge=0, le=1)
    recent_form_probability: float = Field(ge=0, le=1)
    matchup_probability: float = Field(ge=0, le=1)
    market_specific_probability: float = Field(ge=0, le=1)
    model_agreement: float = Field(ge=0, le=1)
    data_quality: float = Field(ge=0, le=1)
    sample_size_factor: float = Field(ge=0, le=1)


class PredictionScore(BaseModel):
    calibrated_probability: float
    analytical_confidence: float
    qualifies: bool
    evidence_quality: float


def score_prediction(e: PredictionEvidence, min_confidence: float = 90.0) -> PredictionScore:
    # MVP deterministic ensemble. These weights are configuration/model parameters, not claims
    # of real-world accuracy. Historical calibration will replace/tune them as results accrue.
    probability = (
        e.historical_probability * 0.25
        + e.recent_form_probability * 0.20
        + e.matchup_probability * 0.15
        + e.market_specific_probability * 0.25
        + e.model_agreement * 0.15
    )
    evidence_quality = (e.data_quality * 0.65) + (e.sample_size_factor * 0.35)

    # Confidence is deliberately separate from probability. Poor evidence can only reduce it.
    confidence = probability * 100 * (0.75 + 0.25 * evidence_quality)
    confidence = min(confidence, probability * 100)

    return PredictionScore(
        calibrated_probability=round(probability, 6),
        analytical_confidence=round(confidence, 2),
        qualifies=confidence >= min_confidence and evidence_quality >= 0.70,
        evidence_quality=round(evidence_quality, 4),
    )
