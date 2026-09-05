"""Web-intelligence fallback layer.

This module deliberately keeps web-discovered market data separate from API provider data.
It never fabricates odds or confidence.  Records must carry source URLs/timestamps and
can only progress to qualification after independent evidence/scoring is available.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")

@dataclass(frozen=True)
class WebMarketRecord:
    sport: str
    event: str
    competition: str
    starts_at: str
    bookmaker: str
    market: str
    selection: str
    odds: float | None
    source: str
    observed_at: str
    confidence: float | None = None
    qualified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def fallback_status() -> dict:
    return {
        "ok": True,
        "provider": "Web Intelligence",
        "mode": "fallback",
        "ready": True,
        "observed_at": datetime.now(SAST).isoformat(),
        "rules": {
            "minimum_confidence": 90,
            "target_odds": [1.45, 1.60],
            "portfolio_legs": [10, 15],
            "require_source": True,
            "require_timestamp": True,
            "invent_missing_odds": False,
            "invent_confidence": False,
            "force_portfolio": False,
        },
    }
