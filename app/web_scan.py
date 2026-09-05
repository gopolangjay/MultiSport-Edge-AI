"""Web-intelligence scan orchestration backed by persistent storage."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.web_pipeline import build_web_portfolio, qualify_records
from app.web_store import ingest as store_ingest, records as stored_records

SAST = ZoneInfo("Africa/Johannesburg")


def ingest(records: list[dict]) -> dict:
    return store_ingest(records)


def snapshot() -> dict:
    now = datetime.now(SAST)
    rows = stored_records()
    qualification = qualify_records(rows)
    portfolio = build_web_portfolio(rows)
    return {
        "ok": True,
        "mode": "web-intelligence",
        "observed_records": len(rows),
        "qualified_records": len(qualification["qualified"]),
        "portfolio": portfolio,
        "records": rows[:100],
        "generated_at": now.isoformat(),
        "freshness_window_minutes": 120,
        "note": "Only sourced observations are scanned; stale observations are removed and no missing odds or confidence values are fabricated.",
    }
