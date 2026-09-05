"""Autonomous web-research collector using OpenAI Responses API web search.

Searches only public pages, requests structured sourced observations, and passes them
through the existing conservative research-worker validation/scoring pipeline.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.research_worker import prepare_batch
from app.web_scan import ingest, snapshot

SAST = ZoneInfo("Africa/Johannesburg")
MODEL = os.getenv("RESEARCH_MODEL", "gpt-5.6-luna")

SPORTS = [
    "football", "tennis", "basketball", "rugby", "cricket", "ice hockey",
    "baseball", "volleyball", "handball", "table tennis",
]

PROMPT = """You are the market-research collector for MultiSport Edge AI.
Search the public web for events taking place today in South African time across these sports:
{sports}.

Primary bookmaker targets: Betway South Africa and Sportingbet South Africa. Use only prices
that are explicitly visible in public web sources. Cross-check event/evidence using public
Flashscore and/or Sofascore pages where available. Never invent an event, market, selection,
odds, statistic, source URL, or signal.

Return ONLY valid JSON, no markdown, in this shape:
{{"observations":[{{"sport":"...","event":"...","competition":"...","starts_at":"ISO-8601 with timezone if known","bookmaker":"betway|sportingbet","market":"...","selection":"...","odds":1.01,"source_url":"https://...","observed_at":"ISO-8601","evidence_sources":["https://...","https://..."],"signals":{{"historical_rate":0.0,"recent_form":0.0,"matchup_support":0.0,"availability_support":0.0,"market_stability":0.0,"model_agreement":0.0,"sample_quality":0.0}},"research_notes":"short factual note"}}]}}

Signal values must be in [0,1] and only be included when supported by evidence. Do not turn
bookmaker implied probability into analytical confidence. Prefer conservative low-risk market
families and independent events. If a required value cannot be verified, omit that observation.
The downstream system, not you, decides whether a selection clears the >=90 analytical gate.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("observations", []), list):
        raise ValueError("research response must contain observations array")
    return data


def run_research() -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        return {"ok": False, "error": "OPENAI_API_KEY is not configured"}
    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        tools=[{
            "type": "web_search",
            "search_context_size": "high",
            "user_location": {"type": "approximate", "country": "ZA", "timezone": "Africa/Johannesburg"},
        }],
        input=PROMPT.format(sports=", ".join(SPORTS)),
        store=False,
    )
    payload = _extract_json(response.output_text)
    prepared = prepare_batch(payload.get("observations", []))
    ingestion = ingest(prepared["records"])
    slate = snapshot()
    return {
        "ok": True,
        "model": MODEL,
        "researched_at": datetime.now(SAST).isoformat(),
        "discovered": len(payload.get("observations", [])),
        "prepared": prepared["accepted"],
        "rejected": prepared["rejected"],
        "ingestion": ingestion,
        "qualified": slate["qualified_records"],
        "portfolio": slate["portfolio"],
    }
