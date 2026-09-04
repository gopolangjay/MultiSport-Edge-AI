from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.providers.api_sports import APISportsProvider


@dataclass(frozen=True)
class FootballEvidenceBundle:
    fixture_id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    season: int
    home_history: list[dict[str, Any]]
    away_history: list[dict[str, Any]]
    home_statistics: list[dict[str, Any]]
    away_statistics: list[dict[str, Any]]
    injuries: list[dict[str, Any]]
    standings: list[dict[str, Any]]
    head_to_head: list[dict[str, Any]]
    odds: list[dict[str, Any]]
    provider_predictions: list[dict[str, Any]]


async def collect_football_evidence(
    provider: APISportsProvider,
    *,
    fixture_id: int,
    home_team_id: int,
    away_team_id: int,
    league_id: int,
    season: int,
) -> FootballEvidenceBundle:
    # Calls are intentionally explicit so a quota-aware scheduler/cache can decide
    # which evidence needs refreshing instead of hiding provider usage in a model.
    home_history = await provider.historical_fixtures(home_team_id)
    away_history = await provider.historical_fixtures(away_team_id)
    home_statistics = await provider.team_statistics(league_id, season, home_team_id)
    away_statistics = await provider.team_statistics(league_id, season, away_team_id)
    injuries = await provider.injuries(fixture_id)
    standings = await provider.standings(league_id, season)
    h2h = await provider.head_to_head(home_team_id, away_team_id)
    odds = await provider.football_odds(fixture_id)
    predictions = await provider.football_predictions(fixture_id)
    return FootballEvidenceBundle(
        fixture_id=fixture_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        league_id=league_id,
        season=season,
        home_history=home_history,
        away_history=away_history,
        home_statistics=home_statistics,
        away_statistics=away_statistics,
        injuries=injuries,
        standings=standings,
        head_to_head=h2h,
        odds=odds,
        provider_predictions=predictions,
    )
