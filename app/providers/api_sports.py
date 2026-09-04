from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.config import get_settings


class APISportsError(RuntimeError):
    pass


class APISportsProvider:
    """Permitted API-Sports adapter. Keeps raw provider data separate from model output."""

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
        errors = payload.get("errors")
        if errors:
            raise APISportsError(f"API-Sports returned errors: {errors}")
        return payload

    async def status(self) -> dict[str, Any]:
        return await self._get("/status")

    async def football_fixtures(self, fixture_date: date) -> list[dict[str, Any]]:
        payload = await self._get("/fixtures", {"date": fixture_date.isoformat()})
        return payload.get("response", [])

    async def football_odds(self, fixture_id: int) -> list[dict[str, Any]]:
        payload = await self._get("/odds", {"fixture": fixture_id})
        return payload.get("response", [])

    async def football_predictions(self, fixture_id: int) -> list[dict[str, Any]]:
        payload = await self._get("/predictions", {"fixture": fixture_id})
        return payload.get("response", [])
