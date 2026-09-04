from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./multisport_edge.db"
    openai_api_key: str | None = None
    min_analytical_confidence: float = 90.0
    target_odds_min: float = 1.45
    target_odds_max: float = 1.60
    min_portfolio_legs: int = 10
    max_portfolio_legs: int = 15
    max_legs_per_event: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
