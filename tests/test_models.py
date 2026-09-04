from app.models.calibration import evaluate_calibration
from app.models.sports import basketball_model, football_model, tennis_model


def test_calibration_metrics_are_bounded():
    report = evaluate_calibration([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0])
    assert report.sample_size == 4
    assert 0 <= report.brier_score <= 1
    assert report.log_loss >= 0
    assert 0 <= report.expected_calibration_error <= 1


def test_sport_models_keep_probability_and_confidence_separate():
    outputs = [
        football_model(strength_delta=3, recent_form_delta=2, home_advantage=1,
                       goal_profile_edge=2, data_quality=.95, model_agreement=.95),
        tennis_model(rating_delta=3, surface_edge=2, serve_return_edge=2,
                     recent_form_delta=1, data_quality=.95, model_agreement=.95),
        basketball_model(efficiency_delta=3, pace_matchup_edge=1, home_advantage=1,
                         recent_form_delta=2, data_quality=.95, model_agreement=.95),
    ]
    for output in outputs:
        assert 0 < output.probability < 1
        assert 0 <= output.analytical_confidence <= 100
        assert output.data_quality == .95
