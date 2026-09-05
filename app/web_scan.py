"""Automatic web-intelligence scan orchestration.

The application cannot invoke ChatGPT web search from its Render process. This module
therefore maintains a strictly sourced observation feed: observations discovered by the
web research worker are ingested, deduplicated, aged out, qualified and optimized here.
No missing odds or confidence values are synthesized.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from threading import RLock
from zoneinfo import ZoneInfo

from app.web_pipeline import build_web_portfolio, qualify_records

SAST = ZoneInfo("Africa/Johannesburg")
_LOCK = RLock()
_RECORDS: dict[str, dict] = {}
MAX_AGE = timedelta(hours=12)


def _key(r: dict) -> str:
    return "|".join(str(r.get(k, "")).strip().lower() for k in ("sport", "event", "bookmaker", "market", "selection"))


def ingest(records: list[dict]) -> dict:
    now = datetime.now(SAST)
    accepted = 0
    with _LOCK:
        for raw in records:
            if not raw.get("source_url") or not raw.get("observed_at"):
                continue
            item = dict(raw)
            item["ingested_at"] = now.isoformat()
            _RECORDS[_key(item)] = item
            accepted += 1
        _prune(now)
    return {"ok": True, "accepted": accepted, "stored": len(_RECORDS), "ingested_at": now.isoformat()}


def _prune(now: datetime) -> None:
    stale = []
    for k, r in _RECORDS.items():
        try:
            t = datetime.fromisoformat(str(r["observed_at"]).replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=SAST)
            if now.astimezone(t.tzinfo) - t > MAX_AGE:
                stale.append(k)
        except Exception:
            stale.append(k)
    for k in stale:
        _RECORDS.pop(k, None)


def snapshot() -> dict:
    now = datetime.now(SAST)
    with _LOCK:
        _prune(now)
        rows = list(_RECORDS.values())
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
        "note": "Only externally sourced observations are scanned; the service does not fabricate or scrape undocumented bookmaker endpoints.",
    }
