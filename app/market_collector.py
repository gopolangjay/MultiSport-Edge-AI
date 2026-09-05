"""Autonomous collector for public sportsbook market pages.

This collector uses only public HTML, records provenance, and deliberately does
not invent analytical evidence. Collected bookmaker observations therefore
enter the pipeline as sourced market data; qualification remains a separate
step and requires independent evidence.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.web_scan import ingest

SAST = ZoneInfo("Africa/Johannesburg")
SOURCES = {
    "sportingbet": "https://www.sportingbet.co.za/en/sports/hub",
    "betway": "https://www.betway.co.za/sport",
}
USER_AGENT = "MultiSportEdgeAI/1.0 (+public-market-research)"


def _text(markup: str) -> str:
    markup = re.sub(
        r"<script[\s\S]*?</script>|<style[\s\S]*?</style>",
        " ",
        markup,
        flags=re.IGNORECASE,
    )
    markup = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(markup)).strip()


def _extract_sportingbet(markup: str, observed_at: str) -> list[dict]:
    """Extract only clearly labelled event/result-price rows."""
    text = _text(markup)
    price = r"(\d{1,3}(?:\.\d{1,3})?)"
    pattern = re.compile(
        rf"([A-Z][A-Za-z0-9 .&'’/-]{{2,45}})\s+"
        rf"([A-Z][A-Za-z0-9 .&'’/-]{{2,45}})\s+"
        rf"(?:Today|Tomorrow|\d{{2}}/\d{{2}}/\d{{4}})[^\d]{{0,35}}"
        rf"{price}\s+{price}\s+{price}"
    )
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for match in pattern.finditer(text):
        home, away = match.group(1).strip(), match.group(2).strip()
        prices = [float(match.group(i)) for i in (3, 4, 5)]
        event = f"{home} vs {away}"
        for selection, odds in zip((home, "Draw", away), prices, strict=True):
            key = (event, selection)
            if key in seen or not 1.0 < odds <= 100:
                continue
            seen.add(key)
            rows.append(
                {
                    "sport": "football",
                    "event": event,
                    "competition": "public sportsbook slate",
                    "starts_at": observed_at,
                    "bookmaker": "sportingbet",
                    "market": "Match Result 1X2",
                    "selection": selection,
                    "odds": odds,
                    "source_url": SOURCES["sportingbet"],
                    "observed_at": observed_at,
                    "evidence_sources": [SOURCES["sportingbet"]],
                    "analytical_confidence": None,
                    "research_signals": {},
                    "research_notes": [
                        "Automatically collected public bookmaker market; independent "
                        "evidence still required for qualification."
                    ],
                }
            )
    return rows[:300]


async def collect_public_markets() -> dict:
    observed_at = datetime.now(SAST).isoformat()
    results: list[dict] = []
    source_status: dict[str, dict] = {}
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for bookmaker, url in SOURCES.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                extracted = (
                    _extract_sportingbet(response.text, observed_at)
                    if bookmaker == "sportingbet"
                    else []
                )
                results.extend(extracted)
                source_status[bookmaker] = {
                    "ok": True,
                    "http_status": response.status_code,
                    "records": len(extracted),
                    "url": url,
                }
            except Exception as exc:  # each source is isolated so one failure cannot stop the scan
                source_status[bookmaker] = {
                    "ok": False,
                    "records": 0,
                    "url": url,
                    "error": str(exc)[:180],
                }
    ingestion = (
        ingest(results)
        if results
        else {"ok": True, "accepted": 0, "note": "No unambiguous public market rows extracted."}
    )
    return {
        "ok": True,
        "observed_at": observed_at,
        "sources": source_status,
        "collected": len(results),
        "ingestion": ingestion,
        "qualification_note": (
            "Market collection and >=90 analytical qualification are separate; "
            "independent evidence is required."
        ),
    }
