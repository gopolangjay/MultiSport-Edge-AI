from pathlib import Path


def test_shell_and_native_bridge_use_same_production_hostname():
    host = "multisport-edge-ai.onrender.com"
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    java = Path("android/app/src/main/java/za/co/multisportedge/MainActivity.java").read_text(encoding="utf-8")
    assert host in html
    assert host in java
