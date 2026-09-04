from fastapi import FastAPI

from app import __version__
from app.domain import Portfolio, PortfolioRequest
from app.portfolio import build_portfolio

app = FastAPI(title="MultiSport Edge AI", version=__version__)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "service": "multisport-edge-ai",
    }


@app.post("/v1/portfolios/build", response_model=Portfolio)
def create_portfolio(request: PortfolioRequest) -> Portfolio:
    return build_portfolio(request)
