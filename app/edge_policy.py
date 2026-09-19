"""Edge Multi V2 qualification policy.

This module is intentionally conservative. It does not manufacture probabilities.
A candidate can qualify only when a server-side market model produced the score and
at least two independent evidence groups are present in addition to bookmaker odds.
"""
from __future__ import annotations

from math import isfinite, prod
from urllib.parse import urlparse

MIN_SCORE = 90.0
MIN_LEGS = 10
MAX_LEGS = 15
TARGET_ODDS = 1.60
TARGET_FLOOR = 1.55
TARGET_CEILING = 1.60

TRUSTED_GROUPS = {
    "flashscore": ("flashscore.com", "flashscore.co.za"),
    "sofascore": ("sofascore.com",),
    "betway": ("betway.co.za",),
    "sportingbet": ("sportingbet.co.za",),
}

MARKET_REGISTRY = {
    "football": {"match result", "double chance", "draw no bet", "goals", "team goals", "btts", "corners", "cards"},
    "soccer": {"match result", "double chance", "draw no bet", "goals", "team goals", "btts", "corners", "cards"},
    "basketball": {"moneyline", "spread", "total points", "team totals", "quarter", "half"},
    "tennis": {"match winner", "set winner", "total games", "game handicap", "total sets"},
    "ice hockey": {"moneyline", "double chance", "puck line", "total goals", "team goals"},
    "rugby": {"match winner", "handicap", "total points", "team totals", "winning margin"},
    "volleyball": {"match winner", "set handicap", "total sets", "total points", "set winner"},
    "handball": {"match winner", "double chance", "handicap", "total goals", "team goals"},
    "baseball": {"moneyline", "run line", "total runs", "team runs"},
    "cricket": {"match winner", "innings runs", "team totals", "wickets", "performance"},
    "mma": {"fight winner", "method of victory", "goes the distance", "round totals"},
    "boxing": {"fight winner", "method of victory", "goes the distance", "round totals"},
    "darts": {"match winner", "handicap", "total legs", "total sets", "180s"},
    "table tennis": {"match winner", "set handicap", "total sets", "total points"},
    "american football": {"moneyline", "spread", "game total", "team totals", "half"},
    "aussie rules": {"match winner", "handicap", "total points", "winning margin"},
    "esports": {"match winner", "map winner", "map handicap", "total maps", "total rounds"},
}


def evidence_group(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return None
    except ValueError:
        return None
    for group, needles in TRUSTED_GROUPS.items():
        if any(host == needle or host.endswith("." + needle) for needle in needles):
            return group
    return None


def independent_groups(urls: list[str] | tuple[str, ...]) -> set[str]:
    return {g for u in urls if (g := evidence_group(str(u)))}


def market_family(sport: str, market: str) -> str | None:
    allowed = MARKET_REGISTRY.get(sport.strip().lower(), set())
    text = market.strip().lower()
    # Longest-first prevents generic labels from swallowing a more specific family.
    for family in sorted(allowed, key=len, reverse=True):
        if family in text:
            return family
    if text in {"1x2", "match result 1x2"} and sport.strip().lower() in {"football", "soccer"}:
        return "match result"
    return None


def qualification_state(raw: dict) -> tuple[str, str | None]:
    try:
        odds = float(raw.get("odds"))
    except (TypeError, ValueError, OverflowError):
        odds = float("nan")
    bookmaker = str(raw.get("bookmaker", "")).strip().lower()
    if (
        not isfinite(odds) or not 1 < odds <= 1000
        or bookmaker not in {"betway", "sportingbet"}
        or evidence_group(str(raw.get("source_url", ""))) != bookmaker
    ):
        return "ODDS_PENDING", "Verified bookmaker odds are required."
    family = market_family(str(raw.get("sport", "")), str(raw.get("market", "")))
    if family is None:
        return "MODEL_PENDING", "No approved sport/market model is registered."
    sources = raw.get("evidence_sources")
    if not isinstance(sources, (list, tuple)):
        sources = []
    groups = independent_groups(tuple(str(x) for x in sources if x))
    independent = groups - {"betway", "sportingbet"}
    if len(independent) < 2:
        return "EVIDENCE_PENDING", "Two independent trusted evidence groups are required."
    if raw.get("model_validated") is not True or not raw.get("model_id") or not raw.get("model_version"):
        return "MODEL_PENDING", "A server-side validated sport/market model output is required."
    try:
        score = float(raw.get("analytical_confidence"))
    except (TypeError, ValueError, OverflowError):
        score = float("nan")
    if not isfinite(score) or not MIN_SCORE <= score <= 100:
        return "BELOW_THRESHOLD", f"Analytical score must be at least {MIN_SCORE:.0f}."
    return "QUALIFIED", None


def optimize_safest(candidates: list[dict]) -> dict:
    """Choose 10-15 independent-event legs nearest to 1.60 without exceeding it.

    Safety ordering is score descending, then decimal odds ascending. We never add a
    lower-quality leg merely to force the target; failure remains explicit.
    """
    eligible = []
    for row in candidates:
        state, reason = qualification_state(row)
        if state == "QUALIFIED":
            eligible.append({**row, "qualification_state": state, "qualification_reason": reason})
    eligible.sort(key=lambda x: (-float(x["analytical_confidence"]), float(x["odds"])))
    chosen: list[dict] = []
    events: set[tuple[str, str]] = set()
    for row in eligible:
        key = (str(row.get("sport", "")).lower(), str(row.get("event", "")).lower())
        if key in events:
            continue
        trial = prod([float(x["odds"]) for x in chosen] + [float(row["odds"])])
        if trial > TARGET_CEILING:
            continue
        chosen.append(row)
        events.add(key)
        if len(chosen) >= MIN_LEGS and prod(float(x["odds"]) for x in chosen) >= TARGET_FLOOR:
            break
        if len(chosen) == MAX_LEGS:
            break
    combined = prod(float(x["odds"]) for x in chosen) if chosen else 1.0
    locked = MIN_LEGS <= len(chosen) <= MAX_LEGS and TARGET_FLOOR <= combined <= TARGET_CEILING
    return {
        "status": "LOCKED" if locked else "WAITING",
        "legs": chosen if locked else [],
        "locked_count": len(chosen) if locked else 0,
        "combined_odds": round(combined, 4) if locked else None,
        "target_odds": TARGET_ODDS,
        "target_band": [TARGET_FLOOR, TARGET_CEILING],
        "qualified_candidate_count": len(eligible),
        "reason": None if locked else "Not enough independently evidenced >=90 selections to build a safe 10-15 leg Edge near 1.60.",
    }


def daily_funnel(events: list[dict], observations: list[dict], locked: dict) -> dict:
    total = len(events)
    completed = sum(1 for e in events if e.get("home_score") is not None and e.get("away_score") is not None)
    remaining = max(0, total - completed)
    evidenced = sum(1 for r in observations if qualification_state(r)[0] not in {"ODDS_PENDING", "EVIDENCE_PENDING"})
    qualified = sum(1 for r in observations if qualification_state(r)[0] == "QUALIFIED")
    return {
        "total_games_today": total,
        "remaining_games": remaining,
        "completed_games": completed,
        "bookmaker_observations": len(observations),
        "independently_evidenced": evidenced,
        "qualified_90_plus": qualified,
        "edge_locked": locked.get("status") == "LOCKED",
        "edge_locked_count": locked.get("locked_count", 0),
        "edge_combined_odds": locked.get("combined_odds"),
    }
