"""Reliable public sports schedule/results provider.

Uses TheSportsDB's documented V1 API (free key 123) for fixture/result discovery.
This layer is deliberately separate from bookmaker odds and model qualification.
"""
from __future__ import annotations

import asyncio
from datetime import date

import httpx

BASE = "https://www.thesportsdb.com/api/v1/json/123/eventsday.php"
SPORTS = ("Soccer", "Tennis", "Basketball", "Rugby", "Cricket", "Ice_Hockey", "Baseball", "Volleyball", "Handball")


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


async def events_for_day(target: date) -> dict:
    timeout = httpx.Timeout(15.0, connect=8.0)
    headers = {"User-Agent": "MultiSportEdgeAI/2.0"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        chunks = await asyncio.gather(*(_sport_day(client, target, sport) for sport in SPORTS))
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
        "note": "Fixture/result discovery only. Bookmaker odds and >=90 model qualification remain separate.",
    }
