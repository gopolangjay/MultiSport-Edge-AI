from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.domain import Portfolio, PortfolioRequest
from app.optimizer import optimize_portfolio
from app.providers.api_sports import APISportsError, APISportsProvider

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="MultiSport Edge AI", version=__version__)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "service": "multisport-edge-ai"}


@app.get("/v1/providers/api-sports/status")
async def api_sports_status() -> dict:
    try:
        return await APISportsProvider().status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="API-Sports provider unavailable") from exc


@app.get("/v1/football/fixtures")
async def football_fixtures(on: date | None = None) -> dict:
    target_date = on or date.today()
    try:
        fixtures = await APISportsProvider().football_fixtures(target_date)
    except (APISportsError, Exception) as exc:
        raise HTTPException(status_code=502, detail="Fixture provider unavailable") from exc
    return {"date": target_date.isoformat(), "count": len(fixtures), "fixtures": fixtures}


@app.get("/v1/football/fixtures/{fixture_id}/odds")
async def football_odds(fixture_id: int) -> dict:
    try:
        odds = await APISportsProvider().football_odds(fixture_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Odds provider unavailable") from exc
    return {"fixture_id": fixture_id, "odds": odds}


@app.get("/v1/football/fixtures/{fixture_id}/predictions")
async def football_predictions(fixture_id: int) -> dict:
    try:
        predictions = await APISportsProvider().football_predictions(fixture_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Prediction evidence unavailable") from exc
    return {"fixture_id": fixture_id, "predictions": predictions}


@app.post("/v1/portfolios/build", response_model=Portfolio)
def create_portfolio(request: PortfolioRequest) -> Portfolio:
    return optimize_portfolio(request)
