from pathlib import Path


def test_android_live_ui_uses_required_endpoints_and_backend_schema():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    for path in ("/health", "/v1/events/today", "/v1/system/status", "/v1/web-intelligence/scan"):
        assert path in html
    for marker in ("pHealth", "pEvents", "pSystem", "pScan", "apiState"):
        assert marker in html
    assert "scan.bookmaker_counts" in html
    assert "e.home_logo" in html and "e.away_logo" in html
    assert "QUALIFIED_PORTFOLIO" in html
    assert "No selections are fabricated" in html
