from pathlib import Path


def test_android_bridge_has_bounded_network_timeouts():
    java = Path("android/app/src/main/java/za/co/multisportedge/MainActivity.java").read_text(encoding="utf-8")
    assert "setConnectTimeout(15000)" in java
    assert "setReadTimeout(30000)" in java
