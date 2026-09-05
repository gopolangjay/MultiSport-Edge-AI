from pathlib import Path


def test_android_scanner_maps_backend_bookmaker_counts():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    assert "scan.bookmaker_counts" in html
    assert "book('sportingbet')" in html
    assert "book('betway')" in html
