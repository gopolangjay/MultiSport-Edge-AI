"""Web-intelligence scan orchestration backed by persistent storage."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.web_pipeline import build_web_portfolio, qualify_records
from app.web_store import ingest as store_ingest
from app.web_store import records as stored_records

SAST = ZoneInfo("Africa/Johannesburg")
BOOKMAKERS = ("sportingbet", "betway")


def ingest(records: list[dict]) -> dict:
    return store_ingest(records)


def snapshot() -> dict:
    now = datetime.now(SAST)
    rows = stored_records()
    qualification = qualify_records(rows)
    portfolio = build_web_portfolio(rows)
    bookmaker_counts = {
        bookmaker: sum(1 for row in rows if str(row.get("bookmaker", "")).lower() == bookmaker)
        for bookmaker in BOOKMAKERS
    }
    return {
        "ok": True,
        "mode": "web-intelligence",
        "observed_records": len(rows),
        "bookmaker_counts": bookmaker_counts,
        "qualified_records": len(qualification["qualified"]),
        "portfolio": portfolio,
        "records": rows[:100],
        "generated_at": now.isoformat(),
        "freshness_window_minutes": 120,
        "note": (
            "Sportingbet and Betway observations remain separate by bookmaker; only sourced "
            "observations are scanned and no missing odds or confidence values are fabricated."
        ),
    }
