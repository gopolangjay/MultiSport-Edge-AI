from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedQuote:
    provider: str
    fixture_id: int
    bookmaker_id: int | None
    bookmaker: str
    market_id: int | None
    market: str
    selection: str
    line: str | None
    decimal_odds: float


def _split_selection(value: str) -> tuple[str, str | None]:
    value = value.strip()
    parts = value.rsplit(" ", 1)
    if len(parts) == 2:
        try:
            float(parts[1])
            return parts[0], parts[1]
        except ValueError:
            pass
    return value, None


def normalize_football_odds(payload: list[dict[str, Any]]) -> list[NormalizedQuote]:
    quotes: list[NormalizedQuote] = []
    for item in payload:
        fixture_id = int(item.get("fixture", {}).get("id", 0))
        for bookmaker in item.get("bookmakers", []):
            bookmaker_name = str(bookmaker.get("name", "unknown")).strip().lower()
            for bet in bookmaker.get("bets", []):
                market = str(bet.get("name", "unknown")).strip().lower()
                for value in bet.get("values", []):
                    raw_selection = str(value.get("value", "unknown"))
                    selection, line = _split_selection(raw_selection)
                    try:
                        odds = float(value.get("odd"))
                    except (TypeError, ValueError):
                        continue
                    if odds <= 1.0:
                        continue
                    quotes.append(NormalizedQuote(
                        provider="api-sports",
                        fixture_id=fixture_id,
                        bookmaker_id=bookmaker.get("id"),
                        bookmaker=bookmaker_name,
                        market_id=bet.get("id"),
                        market=market,
                        selection=selection.strip().lower(),
                        line=line,
                        decimal_odds=odds,
                    ))
    return quotes
