from app.metrics import calibration_report


def test_perfect_predictions_have_zero_brier_and_ece():
    report = calibration_report([1.0, 0.0, 1.0, 0.0], [1, 0, 1, 0])
    assert report.brier_score == 0.0
    assert report.expected_calibration_error == 0.0


def test_overconfidence_is_penalized():
    good = calibration_report([0.8, 0.8, 0.2, 0.2], [1, 1, 0, 0])
    bad = calibration_report([0.99, 0.99, 0.99, 0.99], [1, 0, 0, 0])
    assert bad.brier_score > good.brier_score
    assert bad.log_loss > good.log_loss
