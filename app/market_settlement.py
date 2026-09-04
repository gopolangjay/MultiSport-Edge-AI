from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FootballResult:
    home: int
    away: int
    status: str


def settle_football(market: str, selection: str, result: FootballResult) -> str:
    if result.status.lower() not in {"ft", "aet", "pen", "finished"}:
        return "UNRESOLVED"
    market, selection = market.lower(), selection.lower()
    total = result.home + result.away
    if market in {"match winner", "1x2"}:
        actual = "home" if result.home > result.away else "away" if result.away > result.home else "draw"
        actual = {"home": "1", "draw": "x", "away": "2"}.get(actual, actual)
        return "WON" if selection in {actual, {"1":"home","x":"draw","2":"away"}[actual]} else "LOST"
    if "both teams" in market or market == "btts":
        yes = result.home > 0 and result.away > 0
        return "WON" if (selection == "yes") == yes else "LOST"
    if "over/under" in market or "total goals" in market:
        try:
            line = float(selection.split()[-1])
        except (ValueError, IndexError):
            return "UNRESOLVED"
        if total == line:
            return "VOID"
        if selection.startswith("over"):
            return "WON" if total > line else "LOST"
        if selection.startswith("under"):
            return "WON" if total < line else "LOST"
    return "UNRESOLVED"
