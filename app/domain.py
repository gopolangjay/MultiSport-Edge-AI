from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Sport(StrEnum):
    FOOTBALL = "football"
    TENNIS = "tennis"
    BASKETBALL = "basketball"
    RUGBY = "rugby"
    CRICKET = "cricket"
    ICE_HOCKEY = "ice_hockey"
    BASEBALL = "baseball"
    VOLLEYBALL = "volleyball"
    HANDBALL = "handball"
    TABLE_TENNIS = "table_tennis"


class Bookmaker(StrEnum):
    BETWAY = "betway"
    SPORTINGBET = "sportingbet"


class Candidate(BaseModel):
    id: str
    sport: Sport
    event_id: str
    event_name: str
    starts_at: datetime
    market: str
    selection: str
    bookmaker: Bookmaker
    decimal_odds: float = Field(gt=1.0)
    calibrated_probability: float = Field(ge=0.0, le=1.0)
    analytical_confidence: float = Field(ge=0.0, le=100.0)
    data_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    correlation_cluster: str | None = None


class PortfolioRequest(BaseModel):
    candidates: list[Candidate]
    min_confidence: float = Field(default=90.0, ge=0, le=100)
    target_odds_min: float = Field(default=1.45, gt=1.0)
    target_odds_max: float = Field(default=1.60, gt=1.0)
    min_legs: int = Field(default=10, ge=2, le=15)
    max_legs: int = Field(default=15, ge=2, le=15)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.target_odds_max < self.target_odds_min:
            raise ValueError("target_odds_max must be >= target_odds_min")
        if self.max_legs < self.min_legs:
            raise ValueError("max_legs must be >= min_legs")
        return self


class Portfolio(BaseModel):
    status: str
    legs: list[Candidate] = []
    combined_odds: float | None = None
    average_confidence: float | None = None
    reason: str | None = None
