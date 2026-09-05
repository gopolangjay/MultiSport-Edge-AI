from pathlib import Path


def test_android_results_are_driven_by_returned_scores():
    html = Path("android/app/src/main/assets/v2-shell.html").read_text(encoding="utf-8")
    assert "resultsBody" in html
    assert "e.home_score!=null" in html
    assert "No settled scores returned yet" in html
