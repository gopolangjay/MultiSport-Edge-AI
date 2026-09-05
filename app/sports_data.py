"""Reliable public sports schedule/results provider.

Uses TheSportsDB's documented V1 API (free key 123) for fixture/result discovery.
This layer is deliberately separate from bookmaker odds and model qualification.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date

import httpx

BASE = "https://www.thesportsdb.com/api/v1/json/123/eventsday.php"
SPORTS = ("Soccer", "Tennis", "Basketball", "Rugby", "Cricket", "Ice_Hockey", "Baseball", "Volleyball", "Handball")
CACHE_TTL_SECONDS = 300
STALE_TTL_SECONDS = 21600
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = asyncio.Lock()


def _normalise(event: dict) -> dict:
    home = event.get("strHomeTeam") or "TBC"
    away = event.get("strAwayTeam") or "TBC"
    hs, aws = event.get("intHomeScore"), event.get("intAwayScore")
    status = event.get("strStatus") or "Scheduled"
    if hs is not None and aws is not None:
        status = f"{hs} - {aws}"
    return {
        "id": event.get("idEvent"),
        "sport": event.get("strSport") or "Sport",
        "league": event.get("strLeague") or "",
        "event": event.get("strEvent") or f"{home} vs {away}",
        "home": home,
        "away": away,
        "home_team_id": event.get("idHomeTeam"),
        "away_team_id": event.get("idAwayTeam"),
        "home_logo": event.get("strHomeTeamBadge"),
        "away_logo": event.get("strAwayTeamBadge"),
        "league_logo": event.get("strLeagueBadge"),
        "event_image": event.get("strThumb"),
        "date": event.get("dateEvent"),
        "time": event.get("strTime") or "",
        "status": status,
        "home_score": hs,
        "away_score": aws,
        "venue": event.get("strVenue") or "",
        "source": "TheSportsDB",
    }


async def _sport_day(client: httpx.AsyncClient, target: date, sport: str) -> tuple[str, list[dict], str | None]:
    try:
        r = await client.get(BASE, params={"d": target.isoformat(), "s": sport})
        r.raise_for_status()
        payload = r.json()
        return sport, [_normalise(x) for x in (payload.get("events") or [])], None
    except Exception as exc:
        return sport, [], str(exc)[:160]


async def _fetch_day(target: date) -> dict:
    timeout = httpx.Timeout(15.0, connect=8.0)
    headers = {"User-Agent": "MultiSportEdgeAI/2.1"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        # Keep provider pressure low: the free API is sensitive to bursts.
        chunks = []
        for sport in SPORTS:
            chunks.append(await _sport_day(client, target, sport))
            await asyncio.sleep(0.12)
    events: list[dict] = []
    sources: dict[str, dict] = {}
    for sport, rows, error in chunks:
        events.extend(rows)
        sources[sport] = {"ok": error is None, "count": len(rows), **({"error": error} if error else {})}
    events.sort(key=lambda x: (x.get("time") or "99:99", x.get("sport") or ""))
    return {
        "ok": any(v["ok"] for v in sources.values()),
        "date": target.isoformat(),
        "count": len(events),
        "events": events,
        "sources": sources,
        "provider": "TheSportsDB documented V1 API",
        "cache": "fresh",
        "note": "Fixture/result discovery only. Bookmaker odds and >=90 model qualification remain separate.",
    }


async def events_for_day(target: date) -> dict:
    key = target.isoformat()
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return {**cached[1], "cache": "hit"}

    async with _CACHE_LOCK:
        now = time.monotonic()
        cached = _CACHE.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return {**cached[1], "cache": "hit"}

        fresh = await _fetch_day(target)
        if fresh["events"]:
            _CACHE[key] = (time.monotonic(), fresh)
            return fresh

        # A transient upstream empty response must not erase a recently good schedule.
        if cached and now - cached[0] < STALE_TTL_SECONDS and cached[1].get("events"):
            return {**cached[1], "cache": "stale-if-empty", "upstream_empty": True}
        return fresh
