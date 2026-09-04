from datetime import datetime, timedelta, timezone

from app.bookmaker_matching import discover_target_bookmakers
from app.performance import SettledPrediction, standard_windows


def test_discovers_target_bookmakers_without_hardcoded_ids():
    matches = discover_target_bookmakers([{"id": 11, "name": "Betway"}, {"id": 12, "name": "Other"}, {"id": 13, "name": "SportingBet"}])
    assert {(m.target, m.provider_id) for m in matches} == {("betway", 11), ("sportingbet", 13)}


def test_standard_performance_windows():
    now = datetime.now(timezone.utc)
    rows = [
        SettledPrediction(now - timedelta(days=1), .9, True, "football", "goals"),
        SettledPrediction(now - timedelta(days=10), .8, False, "football", "goals"),
        SettledPrediction(now - timedelta(days=50), .7, True, "tennis", "winner"),
    ]
    windows = standard_windows(rows, now)
    assert [w.days for w in windows] == [7, 30, 90]
    assert [w.sample_size for w in windows] == [1, 2, 3]
