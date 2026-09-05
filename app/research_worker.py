"""Research-worker feed for MultiSport Edge AI.

This module accepts sourced observations produced by an external research worker,
validates provenance, derives a conservative analytical-confidence score only when
sufficient independent evidence is supplied, and emits records compatible with
web_scan.ingest(). It deliberately does not scrape private/undocumented endpoints.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
ALLOWED_BOOKMAKERS = {"betway", "sportingbet"}
TRUSTED_EVIDENCE_HOSTS = {
    "flashscore.co.za", "www.flashscore.co.za", "sofascore.com", "www.sofascore.com",
    "sportingbet.co.za", "www.sportingbet.co.za", "betway.co.za", "www.betway.co.za",
}


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def score_observation(raw: dict) -> tuple[float | None, list[str]]:
    """Conservative evidence score, not a guaranteed win probability.

    A record cannot reach 90 from bookmaker price alone. It needs multiple independent
    evidence signals and high data quality. The worker may provide normalized signal
    values in [0,1]: historical_rate, recent_form, matchup_support, availability_support,
    market_stability, model_agreement, sample_quality.
    """
    signals = raw.get("signals") or {}
    evidence = [str(x) for x in raw.get("evidence_sources", []) if x]
    independent_hosts = {_host(x) for x in evidence if _host(x)}
    trusted_hosts = independent_hosts & TRUSTED_EVIDENCE_HOSTS
    reasons: list[str] = []
    if len(trusted_hosts) < 2:
        reasons.append("requires at least two trusted evidence hosts")
        return None, reasons
    keys = ("historical_rate", "recent_form", "matchup_support", "availability_support", "market_stability", "model_agreement", "sample_quality")
    vals = []
    for key in keys:
        if key in signals:
            try:
                vals.append(_clamp(float(signals[key]), 0.0, 1.0))
            except (TypeError, ValueError):
                pass
    if len(vals) < 5:
        reasons.append("requires at least five normalized evidence signals")
        return None, reasons
    base = sum(vals) / len(vals)
    # Data quality and source agreement cap confidence; no score >97 at this stage.
    source_bonus = min(0.02, 0.01 * max(0, len(trusted_hosts) - 2))
    score = _clamp((base + source_bonus) * 100.0, 0.0, 97.0)
    return round(score, 2), reasons


def prepare_record(raw: dict) -> tuple[dict | None, str | None]:
    required = ("sport", "event", "competition", "starts_at", "bookmaker", "market", "selection", "odds", "source_url")
    missing = [k for k in required if raw.get(k) in (None, "")]
    if missing:
        return None, "missing: " + ", ".join(missing)
    bookmaker = str(raw["bookmaker"]).strip().lower()
    if bookmaker not in ALLOWED_BOOKMAKERS:
        return None, "unsupported bookmaker"
    try:
        odds = float(raw["odds"])
    except (TypeError, ValueError):
        return None, "invalid odds"
    if not 1.0 < odds <= 1000:
        return None, "invalid odds"
    confidence, reasons = score_observation(raw)
    item = {k: raw[k] for k in required}
    item["bookmaker"] = bookmaker
    item["odds"] = odds
    item["observed_at"] = str(raw.get("observed_at") or datetime.now(SAST).isoformat())
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
    return {
        "ok": True,
        "records": records,
        "accepted": len(records),
        "rejected": rejected,
        "generated_at": datetime.now(SAST).isoformat(),
        "confidence_semantics": "analytical threshold, not guaranteed win probability",
    }
