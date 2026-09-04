from datetime import datetime, timezone

from app.domain import Sport
from app.ingestion import RawMarketQuote, best_price, normalize_quote
from app.prediction import PredictionEvidence, score_prediction


def raw(provider: str, odds: float) -> RawMarketQuote:
    return RawMarketQuote(
        provider=provider,
        provider_event_id=f"{provider}-1",
        sport=Sport.FOOTBALL,
        competition="Example League",
        home_or_participant_a="Alpha FC",
        away_or_participant_b="Beta FC",
        starts_at=datetime(2026, 9, 5, 14, 0, tzinfo=timezone.utc),
        market="Over 0.5 goals",
        selection="Over",
        line=0.5,
        decimal_odds=odds,
    )


def test_normalizes_equivalent_bookmaker_quotes_and_selects_best_price():
    betway = normalize_quote(raw("betway", 1.05))
    sportingbet = normalize_quote(raw("sportingbet", 1.07))
    assert betway.market_key == sportingbet.market_key
    assert best_price([betway, sportingbet]).bookmaker.value == "sportingbet"


def test_confidence_is_not_allowed_to_exceed_probability_percentage():
    score = score_prediction(
        PredictionEvidence(
            historical_probability=0.95,
            recent_form_probability=0.94,
            matchup_probability=0.93,
            market_specific_probability=0.96,
            model_agreement=0.95,
            data_quality=0.90,
            sample_size_factor=0.90,
        )
    )
    assert score.analytical_confidence <= score.calibrated_probability * 100
    assert score.qualifies
