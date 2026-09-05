"""Sourced web-intelligence ingestion and qualification.

Web observations are accepted only when source, timestamp, event, market, selection and
real bookmaker odds are present. Confidence must come from an evidence scorer; bookmaker
odds alone never qualify a selection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import prod
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
SUPPORTED_BOOKMAKERS = {"betway", "sportingbet"}
MIN_CONFIDENCE = 90.0
TARGET_MIN, TARGET_MAX = 1.45, 1.60

@dataclass(frozen=True)
class SourcedCandidate:
    sport: str
    event: str
    competition: str
    starts_at: str
    bookmaker: str
    market: str
    selection: str
    odds: float
    source_url: str
    observed_at: str
    analytical_confidence: float | None = None
    evidence_sources: tuple[str, ...] = ()

    @property
    def implied_probability(self) -> float:
        return 1.0 / self.odds

    @property
    def qualified(self) -> bool:
        return (
            self.bookmaker.lower() in SUPPORTED_BOOKMAKERS
            and self.odds > 1.0
            and self.analytical_confidence is not None
            and self.analytical_confidence >= MIN_CONFIDENCE
            and bool(self.source_url)
            and bool(self.observed_at)
            and len(self.evidence_sources) >= 1
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["implied_probability"] = round(self.implied_probability, 6)
        d["qualified"] = self.qualified
        return d


def normalize_observation(raw: dict) -> SourcedCandidate:
    required = ("sport", "event", "competition", "starts_at", "bookmaker", "market", "selection", "odds", "source_url", "observed_at")
    missing = [k for k in required if raw.get(k) in (None, "")]
    if missing:
        raise ValueError("Missing sourced fields: " + ", ".join(missing))
    odds = float(raw["odds"])
    if odds <= 1.0 or odds > 1000:
        raise ValueError("Invalid decimal odds")
    return SourcedCandidate(
        sport=str(raw["sport"]).strip().lower(), event=str(raw["event"]).strip(),
        competition=str(raw["competition"]).strip(), starts_at=str(raw["starts_at"]).strip(),
        bookmaker=str(raw["bookmaker"]).strip().lower(), market=str(raw["market"]).strip(),
        selection=str(raw["selection"]).strip(), odds=odds, source_url=str(raw["source_url"]).strip(),
        observed_at=str(raw["observed_at"]).strip(),
        analytical_confidence=float(raw["analytical_confidence"]) if raw.get("analytical_confidence") is not None else None,
        evidence_sources=tuple(str(x) for x in raw.get("evidence_sources", []) if x),
    )


def qualify_records(records: list[dict]) -> dict:
    accepted, rejected = [], []
    for raw in records:
        try:
            c = normalize_observation(raw)
            (accepted if c.qualified else rejected).append(c.to_dict())
        except (TypeError, ValueError) as exc:
            rejected.append({"event": raw.get("event", "unknown"), "qualified": False, "reason": str(exc)})
    return {"qualified": accepted, "rejected": rejected, "minimum_confidence": MIN_CONFIDENCE}


def build_web_portfolio(records: list[dict], min_legs: int = 10, max_legs: int = 15) -> dict:
    result = qualify_records(records)
    candidates = sorted(result["qualified"], key=lambda x: (-x["analytical_confidence"], x["odds"]))
    chosen, events = [], set()
    for c in candidates:
        event_key = (c["sport"], c["event"].lower())
        if event_key in events:
            continue
        trial = prod([x["odds"] for x in chosen] + [c["odds"]])
        if trial > TARGET_MAX and len(chosen) >= min_legs:
            continue
        chosen.append(c); events.add(event_key)
        if len(chosen) >= min_legs and TARGET_MIN <= prod(x["odds"] for x in chosen) <= TARGET_MAX:
            break
        if len(chosen) >= max_legs:
            break
    combined = prod(x["odds"] for x in chosen) if chosen else 1.0
    ok = min_legs <= len(chosen) <= max_legs and TARGET_MIN <= combined <= TARGET_MAX
    return {
        "status": "QUALIFIED_PORTFOLIO" if ok else "NO_QUALIFIED_PORTFOLIO",
        "source_mode": "web-intelligence", "legs": chosen if ok else [],
        "candidate_count": len(candidates), "selected_count": len(chosen) if ok else 0,
        "combined_odds": round(combined, 4) if ok else None,
        "target_odds": [TARGET_MIN, TARGET_MAX], "portfolio_legs": [min_legs, max_legs],
        "reason": None if ok else "Insufficient independent >=90-confidence sourced selections inside the target odds band.",
        "generated_at": datetime.now(SAST).isoformat(),
    }
