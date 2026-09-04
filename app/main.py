from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.domain import Portfolio, PortfolioRequest
from app.optimizer import optimize_portfolio
from app.providers.api_sports import APISportsProvider

BASE_DIR = Path(__file__).resolve().parent
SAST = ZoneInfo("Africa/Johannesburg")
app = FastAPI(title="MultiSport Edge AI", version=__version__)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8"), headers={"Cache-Control":"no-store"})

@app.get("/health")
def health() -> dict:
    return {"status":"ok","version":__version__,"service":"multisport-edge-ai","time_sast":datetime.now(SAST).isoformat()}

def safe_error(exc: Exception) -> str:
    text=str(exc)
    if "API_SPORTS_KEY" in text and "configured" not in text:
        return "API-Sports authentication configuration error"
    return text[:300] or exc.__class__.__name__

@app.get("/v1/providers/api-sports/status")
async def api_sports_status() -> dict:
    try:
        payload=await APISportsProvider().status()
        return {"ok":True,"provider":"API-Sports","payload":payload}
    except Exception as exc:
        return {"ok":False,"provider":"API-Sports","error":safe_error(exc)}

@app.get("/v1/football/fixtures")
async def football_fixtures(on: str | None = None) -> dict:
    try:
        target_date=datetime.strptime(on,"%Y-%m-%d").date() if on else datetime.now(SAST).date()
    except ValueError as exc:
        raise HTTPException(status_code=400,detail="Use YYYY-MM-DD") from exc
    try:
        fixtures=await APISportsProvider().football_fixtures(target_date)
        return {"ok":True,"date":target_date.isoformat(),"count":len(fixtures),"fixtures":fixtures}
    except Exception as exc:
        return {"ok":False,"date":target_date.isoformat(),"count":0,"fixtures":[],"error":safe_error(exc)}

@app.get("/v1/football/fixtures/{fixture_id}/odds")
async def football_odds(fixture_id: int) -> dict:
    try:
        odds=await APISportsProvider().football_odds(fixture_id)
        return {"ok":True,"fixture_id":fixture_id,"odds":odds}
    except Exception as exc:
        return {"ok":False,"fixture_id":fixture_id,"odds":[],"error":safe_error(exc)}

@app.get("/v1/football/fixtures/{fixture_id}/predictions")
async def football_predictions(fixture_id: int) -> dict:
    try:
        predictions=await APISportsProvider().football_predictions(fixture_id)
        return {"ok":True,"fixture_id":fixture_id,"predictions":predictions}
    except Exception as exc:
        return {"ok":False,"fixture_id":fixture_id,"predictions":[],"error":safe_error(exc)}

@app.post("/v1/portfolios/build", response_model=Portfolio)
def create_portfolio(request: PortfolioRequest) -> Portfolio:
    return optimize_portfolio(request)
