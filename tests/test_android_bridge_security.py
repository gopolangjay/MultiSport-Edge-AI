from pathlib import Path


def test_android_bridge_has_fixed_https_origin_and_path_allowlist():
    java = Path("android/app/src/main/java/za/co/multisportedge/MainActivity.java").read_text(encoding="utf-8")
    assert 'private static final String APP_HOST = "multisport-edge-ai.onrender.com"' in java
    assert 'private static final String APP_ORIGIN = "https://" + APP_HOST' in java
    assert "new URL(APP_ORIGIN + path)" in java
    assert "path_not_allowed" in java
