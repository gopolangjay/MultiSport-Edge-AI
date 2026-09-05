"""Autonomous collector for public sportsbook market pages.

The collector records only odds that are visible in the bookmaker's public
page response. Bookmaker observations are market evidence, not analytical
confidence; independent evidence is still required before qualification.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.web_scan import ingest

SAST = ZoneInfo("Africa/Johannesburg")
SOURCES = {
    "sportingbet": "https://www.sportingbet.co.za/en/sports/football-4/betting",
    "betway": "https://www.betway.co.za/Event/LiveSport?IsLoggedIn=true",
}
USER_AGENT = "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Safari/537.36"


def _text(markup: str) -> str:
    markup = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", markup, flags=re.I)
    markup = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(markup)).strip()


def _start_iso(label: str, observed: datetime) -> str:
    label = label.strip()
    date = observed.date()
    if label.lower().startswith("tomorrow"):
        date += timedelta(days=1)
    else:
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})", label)
        if match:
            day, month, year = map(int, match.groups())
            date = date.replace(year=year, month=month, day=day)
    clock = re.search(r"(\d{1,2}):(\d{2})", label)
    hour, minute = (map(int, clock.groups()) if clock else (0, 0))
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=SAST).isoformat()


def _extract_sportingbet(markup: str, observed: datetime) -> list[dict]:
    """Extract conservative football 1X2 rows from Sportingbet's public text.

    The current public page exposes rows as team/team/date-or-day/time/BB then
    three decimal 1X2 prices. We deliberately ignore live rows and ambiguous
    fragments rather than manufacturing an event mapping.
    """
    text = _text(markup)
    price = r"(\d{1,3}(?:\.\d{1,3})?)"
    # Team names are bounded by the schedule marker. Requiring BB sharply
    # reduces accidental matches against prose/navigation text.
    pattern = re.compile(
        rf"([A-Z][A-Za-zÀ-ž0-9 .&'’/()\-]{{1,55}}?)\s+"
        rf"([A-Z][A-Za-zÀ-ž0-9 .&'’/()\-]{{1,55}}?)\s+"
        rf"((?:Today|Tomorrow)\s*/\s*\d{{1,2}}:\d{{2}}|\d{{2}}/\d{{2}}/\d{{4}}\s+\d{{1,2}}:\d{{2}})\s+BB(?:\s+\d+)?\s+"
        rf"{price}\s+{price}\s+{price}",
        re.I,
    )
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    observed_at = observed.isoformat()
    for match in pattern.finditer(text):
        home, away, schedule = (match.group(1).strip(), match.group(2).strip(), match.group(3))
        prices = [float(match.group(i)) for i in (4, 5, 6)]
        if any(not 1.0 < value <= 100 for value in prices):
            continue
        event = f"{home} vs {away}"
        starts_at = _start_iso(schedule, observed)
        for selection, odds in zip((home, "Draw", away), prices, strict=True):
            key = (event, selection, starts_at)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "sport": "football",
                "event": event,
                "competition": "Sportingbet football",
                "starts_at": starts_at,
                "bookmaker": "sportingbet",
                "market": "Match Result 1X2",
                "selection": selection,
                "odds": odds,
                "source_url": SOURCES["sportingbet"],
                "observed_at": observed_at,
                "evidence_sources": [SOURCES["sportingbet"]],
                "analytical_confidence": None,
                "research_signals": {},
                "research_notes": ["Verified public Sportingbet 1X2 observation; independent evidence required."],
            })
    return rows[:600]


async def collect_public_markets() -> dict:
    observed = datetime.now(SAST)
    results: list[dict] = []
    source_status: dict[str, dict] = {}
    timeout = httpx.Timeout(15.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for bookmaker, url in SOURCES.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                extracted = _extract_sportingbet(response.text, observed) if bookmaker == "sportingbet" else []
                results.extend(extracted)
                source_status[bookmaker] = {
                    "ok": True,
                    "http_status": response.status_code,
                    "records": len(extracted),
                    "url": url,
                    "mode": "public-page" if extracted else "reachable-no-verified-rows",
                }
            except Exception as exc:
                source_status[bookmaker] = {"ok": False, "records": 0, "url": url, "error": str(exc)[:180]}
    ingestion = ingest(results) if results else {
        "ok": True,
        "accepted": 0,
        "note": "No unambiguous public bookmaker rows extracted; no odds were fabricated.",
    }
    return {
        "ok": True,
        "observed_at": observed.isoformat(),
        "sources": source_status,
        "collected": len(results),
        "ingestion": ingestion,
        "qualification_note": "Odds collection is repaired independently of the >=90 analytical gate.",
    }
