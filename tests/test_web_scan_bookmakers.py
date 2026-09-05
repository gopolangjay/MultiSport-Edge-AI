from app import web_scan


def test_snapshot_exposes_separate_bookmaker_counts(monkeypatch):
    monkeypatch.setattr(
        web_scan,
        "stored_records",
        lambda: [
            {"bookmaker": "sportingbet"},
            {"bookmaker": "SportingBet"},
            {"bookmaker": "betway"},
        ],
    )
    monkeypatch.setattr(web_scan, "qualify_records", lambda rows: {"qualified": []})
    monkeypatch.setattr(web_scan, "build_web_portfolio", lambda rows: {"status": "NO_QUALIFIED_PORTFOLIO"})
    data = web_scan.snapshot()
    assert data["bookmaker_counts"] == {"sportingbet": 2, "betway": 1}
    assert data["observed_records"] == 3
