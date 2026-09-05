from pathlib import Path


def test_android_acceptance_gate_tracks_required_endpoints():
    text = Path("android/PRODUCTION_ACCEPTANCE.md").read_text(encoding="utf-8")
    for path in ("/health", "/v1/events/today", "/v1/system/status", "/v1/web-intelligence/scan"):
        assert path in text
    assert "home_logo" in text
    assert "away_logo" in text
