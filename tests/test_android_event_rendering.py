from pathlib import Path


def test_android_event_rendering_consumes_provider_logo_fields():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    assert "eventCard" in html
    assert "e.home_logo" in html
    assert "e.away_logo" in html
    assert "sportButtons" in html
    assert "filterSport" in html
    assert "Match Intelligence" in html
