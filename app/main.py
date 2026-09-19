import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app import __version__, private_store
from app.daily_reports import router as reports_router
from app.domain import Portfolio, PortfolioRequest
from app.market_collector import collect_public_markets
from app.optimizer import optimize_portfolio
from app.private_auth import PrivateAccessMiddleware
from app.private_auth import router as auth_router
from app.providers.api_sports import APISportsProvider
from app.report_bridge import bridge_app, mcp
from app.report_bridge import router as bridge_router
from app.research_worker import prepare_batch
from app.sports_data import events_for_day
from app.web_intelligence import fallback_status
from app.web_pipeline import build_web_portfolio, qualify_records
from app.web_scan import ingest as ingest_web_records
from app.web_scan import snapshot as web_scan_snapshot

BASE_DIR = Path(__file__).resolve().parent
SAST = ZoneInfo("Africa/Johannesburg")
@asynccontextmanager
async def lifespan(_app):
    # Log categories only, never exception messages (they may contain DSNs/secrets).
    if not os.getenv("DATABASE_URL", "").strip():
        logging.error("PRIVATE_STORAGE_NOT_CONFIGURED: DATABASE_URL is missing")
    else:
        try:
            await run_in_threadpool(private_store.engine)
            logging.info("PRIVATE_STORAGE_READY: private database schema verified")
        except Exception as exc:
            logging.error("PRIVATE_STORAGE_UNAVAILABLE: %s", type(exc).__name__)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="MultiSport Edge AI", version=__version__, lifespan=lifespan)
app.add_middleware(PrivateAccessMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(auth_router)
app.include_router(bridge_router)
app.include_router(reports_router)


class WebBatch(BaseModel):
    records: list[dict] = Field(default_factory=list, max_length=500)


class ResearchBatch(BaseModel):
    observations: list[dict] = Field(default_factory=list, max_length=500)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse(
        (BASE_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "service": "multisport-edge-ai",
        "private_access": True,
    }


def safe_error(exc: Exception) -> str:
    text = str(exc)
    if "API_SPORTS_KEY" in text and "configured" not in text:
        return "API-Sports authentication configuration error"
    return text[:300] or exc.__class__.__name__


@app.get("/v1/system/status")
async def system_status() -> dict:
    now = datetime.now(SAST)
    scan = web_scan_snapshot()
    fixtures = await events_for_day(now.date())
    return {
        "ok": True,
        "time_sast": now.isoformat(),
        "workflow": [
            "events",
            "bookmaker_odds",
            "evidence",
            "qualification",
            "portfolio",
            "settlement",
        ],
        "events_provider": {
            "name": fixtures["provider"],
            "ok": fixtures["ok"],
            "events": fixtures["count"],
        },
        "bookmaker_collector": {
            "name": "Sportingbet/Betway public pages",
            "observations": scan["observed_records"],
        },
        "model_gate": {"threshold": 90, "qualified": scan["qualified_records"]},
        "portfolio": scan["portfolio"],
        "degraded": scan["observed_records"] == 0,
        "degraded_reason": (
            "Bookmaker pages are JavaScript-rendered; no verified odds observations "
            "are currently stored."
            if scan["observed_records"] == 0
            else None
        ),
    }


@app.get("/v1/events/today")
async def events_today() -> dict:
    return await events_for_day(datetime.now(SAST).date())


@app.get("/v1/events/{on}")
async def events_on(on: str) -> dict:
    try:
        target = date.fromisoformat(on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Use YYYY-MM-DD") from exc
    return await events_for_day(target)


@app.get("/v1/providers/api-sports/status")
async def api_sports_status() -> dict:
    try:
        payload = await APISportsProvider().status()
        return {"ok": True, "provider": "API-Sports", "payload": payload}
    except Exception as exc:  # provider failures are intentionally degraded to fallback status
        return {
            "ok": False,
            "provider": "API-Sports",
            "error": safe_error(exc),
            "fallback": "TheSportsDB+public-market-collector",
        }


@app.get("/v1/providers/web-intelligence/status")
def web_intelligence_status() -> dict:
    status = fallback_status()
    status["research_worker"] = "public-market-collector+verified-research"
    status["requires_openai_api_key"] = False
    status["mode"] = (
        "Events -> verified bookmaker odds -> evidence -> >=90 qualification -> "
        "portfolio -> settlement"
    )
    return status


@app.post("/v1/research-worker/feed")
def research_worker_feed(batch: ResearchBatch) -> dict:
    prepared = prepare_batch(batch.observations)
    ingestion = ingest_web_records(prepared["records"])
    return {
        "ok": True,
        "source": "verified-research-feed",
        "prepared": prepared,
        "ingestion": ingestion,
        "scan": web_scan_snapshot(),
    }


async def _collector_response() -> dict:
    collection = await collect_public_markets()
    return {
        "ok": True,
        "collection": collection,
        "scan": web_scan_snapshot(),
        "events": await events_for_day(datetime.now(SAST).date()),
    }


@app.post("/v1/market-collector/run")
async def market_collector_run() -> dict:
    return await _collector_response()


@app.post("/v1/web-intelligence/ingest")
def web_intelligence_ingest(batch: WebBatch) -> dict:
    return ingest_web_records(batch.records)


@app.get("/v1/web-intelligence/scan")
def web_intelligence_scan() -> dict:
    return web_scan_snapshot()


@app.post("/v1/web-intelligence/qualify")
def web_intelligence_qualify(batch: WebBatch) -> dict:
    return qualify_records(batch.records)


@app.post("/v1/web-intelligence/portfolio")
def web_intelligence_portfolio(batch: WebBatch) -> dict:
    return build_web_portfolio(batch.records)


@app.get("/v1/football/fixtures")
async def football_fixtures(on: str | None = None) -> dict:
    try:
        target_date = date.fromisoformat(on) if on else datetime.now(SAST).date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Use YYYY-MM-DD") from exc
    data = await events_for_day(target_date)
    fixtures = [
        x for x in data["events"] if x["sport"].lower() in {"soccer", "football"}
    ]
    return {
        "ok": data["ok"],
        "date": target_date.isoformat(),
        "count": len(fixtures),
        "fixtures": fixtures,
        "source": "TheSportsDB",
    }


@app.get("/v1/football/fixtures/{fixture_id}/odds")
async def football_odds(fixture_id: int) -> dict:
    return {
        "ok": False,
        "fixture_id": fixture_id,
        "odds": [],
        "error": "No verified bookmaker odds provider is connected for this fixture. "
        "Odds are never fabricated.",
    }


@app.get("/v1/football/fixtures/{fixture_id}/predictions")
async def football_predictions(fixture_id: int) -> dict:
    return {
        "ok": False,
        "fixture_id": fixture_id,
        "predictions": [],
        "error": "Prediction requires verified odds plus independent evidence.",
    }


@app.post("/v1/portfolios/build", response_model=Portfolio)
def create_portfolio(request: PortfolioRequest) -> Portfolio:
    return optimize_portfolio(request)


# Last mount: exact SDK OAuth and /mcp routes, with its own bearer-token middleware.
app.mount("/", bridge_app)
