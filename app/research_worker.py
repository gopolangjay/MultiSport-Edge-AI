"""Validation/scoring for externally researched sportsbook observations."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
ALLOWED_BOOKMAKERS = {"betway", "sportingbet"}
BOOKMAKER_HOSTS = {
    "betway": {"betway.co.za", "www.betway.co.za"},
    "sportingbet": {"sportingbet.co.za", "www.sportingbet.co.za"},
}
EVIDENCE_HOST_GROUPS = {
    "flashscore": {"flashscore.co.za", "www.flashscore.co.za"},
    "sofascore": {"sofascore.com", "www.sofascore.com"},
    "betway": BOOKMAKER_HOSTS["betway"],
    "sportingbet": BOOKMAKER_HOSTS["sportingbet"],
}
MAX_OBSERVATION_AGE = timedelta(minutes=30)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _group(host: str) -> str | None:
    for name, hosts in EVIDENCE_HOST_GROUPS.items():
        if host in hosts:
            return name
    return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def score_observation(raw: dict) -> tuple[float | None, list[str]]:
    signals = raw.get("signals") or {}
    evidence = [str(x) for x in raw.get("evidence_sources", []) if x]
    groups = {_group(_host(x)) for x in evidence}
    groups.discard(None)
    reasons: list[str] = []
    if len(groups) < 2:
        return None, ["requires at least two independent trusted evidence sources"]
    keys = ("historical_rate", "recent_form", "matchup_support", "availability_support", "market_stability", "model_agreement", "sample_quality")
    vals = []
    for key in keys:
        if key in signals:
            try:
                vals.append(_clamp(float(signals[key]), 0.0, 1.0))
            except (TypeError, ValueError):
                pass
    if len(vals) < 5:
        return None, ["requires at least five normalized evidence signals"]
    base = sum(vals) / len(vals)
    source_bonus = min(0.02, 0.01 * max(0, len(groups) - 2))
    return round(_clamp((base + source_bonus) * 100.0, 0.0, 97.0), 2), reasons


def prepare_record(raw: dict) -> tuple[dict | None, str | None]:
    required = ("sport", "event", "competition", "starts_at", "bookmaker", "market", "selection", "odds", "source_url", "observed_at")
    missing = [k for k in required if raw.get(k) in (None, "")]
    if missing:
        return None, "missing: " + ", ".join(missing)
    bookmaker = str(raw["bookmaker"]).strip().lower()
    if bookmaker not in ALLOWED_BOOKMAKERS:
        return None, "unsupported bookmaker"
    if _host(str(raw["source_url"])) not in BOOKMAKER_HOSTS[bookmaker]:
        return None, "source_url must be the selected bookmaker domain"
    try:
        odds = float(raw["odds"])
    except (TypeError, ValueError):
        return None, "invalid odds"
    if not 1.0 < odds <= 1000:
        return None, "invalid odds"
    try:
        observed = datetime.fromisoformat(str(raw["observed_at"]).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=SAST)
        age = datetime.now(SAST).astimezone(observed.tzinfo) - observed
        if age < timedelta(minutes=-5) or age > MAX_OBSERVATION_AGE:
            return None, "observation is outside the 30-minute freshness window"
    except Exception:
        return None, "invalid observed_at"
    confidence, reasons = score_observation(raw)
    item = {k: raw[k] for k in required}
    item["bookmaker"] = bookmaker
    item["odds"] = odds
    item["observed_at"] = observed.isoformat()
    item["evidence_sources"] = [str(x) for x in raw.get("evidence_sources", []) if x]
    item["analytical_confidence"] = confidence
    item["research_signals"] = raw.get("signals") or {}
    item["research_notes"] = raw.get("research_notes") or reasons
    return item, None


def prepare_batch(observations: list[dict]) -> dict:
    records, rejected = [], []
    for raw in observations:
        record, error = prepare_record(raw)
        if record is None:
            rejected.append({"event": raw.get("event", "unknown"), "reason": error})
        else:
            records.append(record)
    return {"ok": True, "records": records, "accepted": len(records), "rejected": rejected, "generated_at": datetime.now(SAST).isoformat(), "confidence_semantics": "analytical threshold, not guaranteed win probability"}
