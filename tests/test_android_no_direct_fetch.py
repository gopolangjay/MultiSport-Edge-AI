from pathlib import Path


def test_native_bridge_reinvokes_load_after_fetch_override():
    java = Path("android/app/src/main/java/za/co/multisportedge/MainActivity.java").read_text(encoding="utf-8")
    assert "window.fetch=" in java
    assert 'view.evaluateJavascript(FETCH_BRIDGE + "load();"' in java
    assert "External fetch blocked by Android API bridge" in java
