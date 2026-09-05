from pathlib import Path


def test_android_ui_shows_real_endpoint_connection_state():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    for marker in ("pHealth", "pEvents", "pSystem", "pScan", "apiState"):
        assert marker in html
    assert "CONNECTING" in html
    assert "Production API connection failed" in html
    assert "Promise.all" in html
