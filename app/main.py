from datetime import date

from fastapi import FastAPI, HTTPException

from app import __version__
from app.domain import Portfolio, PortfolioRequest
from app.portfolio import build_portfolio
from app.providers.api_sports import APISportsError, APISportsProvider

app = FastAPI(title="MultiSport Edge AI", version=__version__)


@app.get("/")
def root() -> dict:
    return {
        "service": "MultiSport Edge AI",
        "version": __version__,
        "status": "live",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "service": "multisport-edge-ai",
    }


@app.get("/v1/providers/api-sports/status")
async def api_sports_status() -> dict:
    try:
        return await APISportsProvider().status()
    except (APISportsError, Exception) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/football/fixtures")
async def football_fixtures(on: date | None = None) -> dict:
    target_date = on or date.today()
    try:
        fixtures = await APISportsProvider().football_fixtures(target_date)
    except (APISportsError, Exception) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"date": target_date.isoformat(), "count": len(fixtures), "fixtures": fixtures}


@app.get("/v1/football/fixtures/{fixture_id}/odds")
async def football_odds(fixture_id: int) -> dict:
    try:
        odds = await APISportsProvider().football_odds(fixture_id)
    except (APISportsError, Exception) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"fixture_id": fixture_id, "odds": odds}


@app.get("/v1/football/fixtures/{fixture_id}/predictions")
async def football_predictions(fixture_id: int) -> dict:
    try:
        predictions = await APISportsProvider().football_predictions(fixture_id)
    except (APISportsError, Exception) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"fixture_id": fixture_id, "predictions": predictions}


@app.post("/v1/portfolios/build", response_model=Portfolio)
def create_portfolio(request: PortfolioRequest) -> Portfolio:
    return build_portfolio(request)
