from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "android/app/src/main/assets/v2-shell.html"
ACTIVITY = ROOT / "android/app/src/main/java/za/co/multisportedge/MainActivity.java"


def test_android_shell_requires_all_production_endpoints():
    html = SHELL.read_text(encoding="utf-8")
    for path in (
        "/health",
        "/v1/events/today",
        "/v1/system/status",
        "/v1/web-intelligence/scan",
    ):
        assert path in html
    assert "bookmaker_counts" in html
    assert "home_logo" in html
    assert "away_logo" in html


def test_android_native_https_bridge_is_restricted_to_production_host():
    java = ACTIVITY.read_text(encoding="utf-8")
    assert 'APP_HOST = "multisport-edge-ai.onrender.com"' in java
    assert 'APP_ORIGIN = "https://" + APP_HOST' in java
    assert "@JavascriptInterface" in java
    assert "HttpURLConnection" in java
    assert "setConnectTimeout" in java
    assert "setReadTimeout" in java
    assert 'path.equals("/health") || path.startsWith("/v1/")' in java
