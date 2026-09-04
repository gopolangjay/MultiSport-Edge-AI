from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BookmakerMatch:
    target: str
    provider_id: int
    provider_name: str


def discover_target_bookmakers(bookmakers: list[dict[str, Any]]) -> list[BookmakerMatch]:
    """Discover targets from provider metadata; never assume undocumented IDs."""
    aliases = {
        "betway": {"betway"},
        "sportingbet": {"sportingbet", "sporting bet"},
    }
    matches: list[BookmakerMatch] = []
    for bookmaker in bookmakers:
        name = str(bookmaker.get("name", "")).strip()
        normalized = " ".join(name.casefold().replace("-", " ").split())
        for target, names in aliases.items():
            if normalized in names:
                try:
                    provider_id = int(bookmaker["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                matches.append(BookmakerMatch(target, provider_id, name))
    return matches
