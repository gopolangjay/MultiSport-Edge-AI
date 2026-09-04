from datetime import datetime, timezone

from app.calibration import CalibrationPoint, ProbabilityCalibrator
from app.domain import Bookmaker, Candidate, PortfolioRequest, Sport
from app.features import EvidenceFeatures, analytical_confidence, implied_probability
from app.normalization import normalize_football_odds
from app.optimizer import optimize_portfolio


def test_normalizes_provider_odds():
    payload = [{"fixture":{"id":7},"bookmakers":[{"id":1,"name":"Book","bets":[{"id":5,"name":"Goals Over/Under","values":[{"value":"Over 0.5","odd":"1.04"}]}]}]}]
    quote = normalize_football_odds(payload)[0]
    assert quote.fixture_id == 7
    assert quote.line == "0.5"
    assert quote.decimal_odds == 1.04


def test_confidence_is_not_probability():
    features = EvidenceFeatures(.94, implied_probability(1.08), 30, .95, .9, .95, .98, .94, .08)
    confidence = analytical_confidence(features)
    assert 0 <= confidence <= 100
    assert confidence != features.model_probability


def test_calibrator_interpolates():
    c = ProbabilityCalibrator([CalibrationPoint(.8,.76), CalibrationPoint(.95,.91)])
    assert .76 < c.calibrate(.9) < .91


def test_beam_optimizer_finds_target():
    now = datetime.now(timezone.utc)
    candidates = [Candidate(id=str(i), sport=Sport.FOOTBALL, event_id=str(i), event_name=f"E{i}", starts_at=now, market="total", selection="over", bookmaker=Bookmaker.BETWAY, decimal_odds=1.04, calibrated_probability=.95, analytical_confidence=95, data_quality=.95) for i in range(12)]
    result = optimize_portfolio(PortfolioRequest(candidates=candidates))
    assert result.status == "QUALIFIED"
    assert 1.45 <= result.combined_odds <= 1.60
