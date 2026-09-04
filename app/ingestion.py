from datetime import datetime, timezone
from hashlib import sha256

from pydantic import BaseModel, Field

from app.domain import Bookmaker, Sport


class RawMarketQuote(BaseModel):
    provider: str
    provider_event_id: str
    sport: Sport
    competition: str
    home_or_participant_a: str
    away_or_participant_b: str
    starts_at: datetime
    market: str
    selection: str
    line: float | None = None
    decimal_odds: float = Field(gt=1.0)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NormalizedMarketQuote(RawMarketQuote):
    event_key: str
    market_key: str
    bookmaker: Bookmaker
    implied_probability: float


def _clean(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def event_key(quote: RawMarketQuote) -> str:
    # Conservative cross-provider key. A future entity-resolution layer will maintain aliases.
    bucket = quote.starts_at.astimezone(timezone.utc).strftime("%Y%m%d%H")
    raw = "|".join(
        [
            quote.sport.value,
            _clean(quote.competition),
            _clean(quote.home_or_participant_a),
            _clean(quote.away_or_participant_b),
            bucket,
        ]
    )
    return sha256(raw.encode()).hexdigest()[:24]


def normalize_quote(quote: RawMarketQuote) -> NormalizedMarketQuote:
    bookmaker = Bookmaker(quote.provider.casefold())
    ekey = event_key(quote)
    line = "" if quote.line is None else f":{quote.line:g}"
    mkey = f"{ekey}:{_clean(quote.market)}:{_clean(quote.selection)}{line}"
    return NormalizedMarketQuote(
        **quote.model_dump(),
        event_key=ekey,
        market_key=mkey,
        bookmaker=bookmaker,
        implied_probability=round(1.0 / quote.decimal_odds, 6),
    )


def best_price(quotes: list[NormalizedMarketQuote]) -> NormalizedMarketQuote:
    if not quotes:
        raise ValueError("quotes cannot be empty")
    keys = {q.market_key for q in quotes}
    if len(keys) != 1:
        raise ValueError("best_price requires equivalent normalized propositions")
    return max(quotes, key=lambda q: q.decimal_odds)
