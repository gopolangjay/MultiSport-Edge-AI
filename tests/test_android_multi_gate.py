from pathlib import Path


def test_android_multi_never_fabricates_unqualified_selections():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    assert "QUALIFIED_PORTFOLIO" in html
    assert "No selections are fabricated" in html
    assert "1.45–1.60" in html
