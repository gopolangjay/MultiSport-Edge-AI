from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.config import get_settings


class APISportsError(RuntimeError):
    pass


class APISportsProvider:
    """API-Sports football adapter. Raw provider data remains separate from model output."""

    football_base_url = "https://v3.football.api-sports.io"

    def __init__(self, api_key: str | None = None, timeout: float = 20.0) -> None:
        self.api_key = api_key or get_settings().api_sports_key
        self.timeout = timeout
        if not self.api_key:
            raise APISportsError("API_SPORTS_KEY is not configured")

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"x-apisports-key": self.api_key}
        async with httpx.AsyncClient(base_url=self.football_base_url, timeout=self.timeout) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        if payload.get("errors"):
            raise APISportsError(f"API-Sports returned errors: {payload['errors']}")
        return payload

    async def _response(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return (await self._get(endpoint, params)).get("response", [])

    async def status(self) -> dict[str, Any]:
        return await self._get("/status")

    async def football_fixtures(self, fixture_date: date) -> list[dict[str, Any]]:
        return await self._response("/fixtures", {"date": fixture_date.isoformat()})

    async def historical_fixtures(self, team_id: int, last: int = 20) -> list[dict[str, Any]]:
        return await self._response("/fixtures", {"team": team_id, "last": max(1, min(last, 100))})

    async def team_statistics(self, league_id: int, season: int, team_id: int) -> list[dict[str, Any]]:
        return await self._response("/teams/statistics", {"league": league_id, "season": season, "team": team_id})

    async def player_statistics(self, league_id: int, season: int, team_id: int | None = None, page: int = 1) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"league": league_id, "season": season, "page": page}
        if team_id is not None:
            params["team"] = team_id
        return await self._response("/players", params)

    async def injuries(self, fixture_id: int) -> list[dict[str, Any]]:
        return await self._response("/injuries", {"fixture": fixture_id})

    async def standings(self, league_id: int, season: int) -> list[dict[str, Any]]:
        return await self._response("/standings", {"league": league_id, "season": season})

    async def head_to_head(self, home_team_id: int, away_team_id: int, last: int = 10) -> list[dict[str, Any]]:
        return await self._response("/fixtures/headtohead", {"h2h": f"{home_team_id}-{away_team_id}", "last": max(1, min(last, 50))})

    async def football_odds(self, fixture_id: int) -> list[dict[str, Any]]:
        return await self._response("/odds", {"fixture": fixture_id})

    async def bookmakers(self) -> list[dict[str, Any]]:
        return await self._response("/odds/bookmakers")

    async def football_predictions(self, fixture_id: int) -> list[dict[str, Any]]:
        return await self._response("/predictions", {"fixture": fixture_id})
